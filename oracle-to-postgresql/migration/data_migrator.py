#!/usr/bin/env python3
"""
data_migrator.py — Oracle → PostgreSQL Batch Data Migrator
Migrates data table-by-table in topological FK order using psycopg2
copy_expert() for maximum throughput.  Always truncates the target
table before loading (idempotent re-runs).

MANDATORY rules applied:
  - Uses psycopg2 copy_expert()  (NEVER copy_from)
  - Always TRUNCATEs before COPY  (no env-var gate)
  - Numeric normalisation via decimal.Decimal for consistent repr
  - Positional Oracle bind variables only (:1, :2 …)
"""

import io
import json
import logging
import os
import sys
from datetime import datetime, date
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

import oracledb
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "config" / ".env")

LOG_DIR    = Path(os.getenv("LOG_DIR", "./logs"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output")) / "ddl"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "data_migrator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

BATCH_SIZE  = int(os.getenv("BATCH_SIZE", "10000"))
PG_NULL     = r"\N"   # PostgreSQL text-format NULL sentinel


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------
def oracle_connect():
    dsn = f"{os.getenv('ORACLE_HOST','localhost')}:{os.getenv('ORACLE_PORT','1521')}/{os.getenv('ORACLE_SERVICE','ORCL')}"
    return oracledb.connect(
        user=os.getenv("ORACLE_USER", "hr"),
        password=os.getenv("ORACLE_PASSWORD", "hr"),
        dsn=dsn,
    )


def pg_connect():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        dbname=os.getenv("PG_DATABASE", "hr_db"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "postgres"),
    )


# ---------------------------------------------------------------------------
# Value serialiser for PostgreSQL TEXT COPY format
# ---------------------------------------------------------------------------
def _normalise_numeric(val) -> str:
    """Canonical numeric string: no trailing zeros, no scientific notation."""
    return format(Decimal(str(val)).normalize(), "f")


def pg_text_value(val) -> str:
    """Convert a Python value to a PostgreSQL text-format COPY token."""
    if val is None:
        return PG_NULL
    if isinstance(val, bool):
        return "t" if val else "f"
    if isinstance(val, (int, float, Decimal)):
        return _normalise_numeric(val)
    if isinstance(val, (datetime,)):
        return val.isoformat(sep=" ")
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, bytes):
        return "\\x" + val.hex()
    # Escape tab, newline, carriage return, backslash per COPY text protocol
    s = str(val)
    s = s.replace("\\", "\\\\")
    s = s.replace("\t", "\\t")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    return s


# ---------------------------------------------------------------------------
# Table migrator
# ---------------------------------------------------------------------------
def migrate_table(
    ora_cur,
    pg_conn,
    schema_ora: str,
    schema_pg: str,
    table: str,
    columns: list,
) -> int:
    pg_cur = pg_conn.cursor()

    # Always truncate before load — idempotent re-runs
    pg_cur.execute(f'TRUNCATE TABLE "{schema_pg}"."{table}" CASCADE')
    pg_conn.commit()
    log.info("  TRUNCATE %s.%s — OK", schema_pg, table)

    # COPY SQL (we write the SQL, so we control all quoting)
    col_expr     = ", ".join(f'"{c}"' for c in columns)
    select_cols  = ", ".join(f'"{c}"' for c in columns)
    copy_sql = (
        f'COPY "{schema_pg}"."{table}" ({col_expr}) '
        f"FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '{PG_NULL}')"
    )

    ora_cur.execute(
        f'SELECT {select_cols} FROM "{schema_ora}"."{table}"'
    )

    total   = 0
    buf     = io.StringIO()

    while True:
        rows = ora_cur.fetchmany(BATCH_SIZE)
        if not rows:
            break
        for row in rows:
            buf.write("\t".join(pg_text_value(v) for v in row) + "\n")
            total += 1

        buf.seek(0)
        pg_cur.copy_expert(copy_sql, buf)
        pg_conn.commit()
        buf.seek(0)
        buf.truncate(0)
        log.info("  → %s: %d rows loaded so far", table, total)

    pg_cur.close()
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    schema_ora = os.getenv("ORACLE_SCHEMA", "HR").upper()
    schema_pg  = os.getenv("PG_SCHEMA", "hr").lower()

    log.info("=" * 60)
    log.info("Data Migrator")
    log.info("Oracle: %s  →  PostgreSQL: %s", schema_ora, schema_pg)
    log.info("Batch size: %d", BATCH_SIZE)
    log.info("Started:    %s", datetime.now().isoformat())
    log.info("=" * 60)

    # Load dependency order
    dep_path = OUTPUT_DIR / "dependency_order.json"
    if not dep_path.exists():
        log.error("Missing %s — run discovery first", dep_path)
        sys.exit(1)
    with open(dep_path, encoding="utf-8") as fh:
        dep_data = json.load(fh)
    migration_order = dep_data["migration_order"]

    # Load column metadata
    meta_path = OUTPUT_DIR / "schema_metadata.json"
    if not meta_path.exists():
        log.error("Missing %s — run discovery first", meta_path)
        sys.exit(1)
    with open(meta_path, encoding="utf-8") as fh:
        metadata = json.load(fh)

    col_map: dict[str, list] = {}
    for col in metadata["columns"]:
        col_map.setdefault(col["table_name"], []).append(col)
    for k in col_map:
        col_map[k].sort(key=lambda c: int(c.get("column_id") or 0))

    ora_conn = oracle_connect()
    pg_conn  = pg_connect()
    ora_cur  = ora_conn.cursor()
    ora_cur.arraysize = BATCH_SIZE

    summary: list[dict] = []
    errors:  list[str]  = []

    try:
        for table in migration_order:
            columns = [c["column_name"] for c in col_map.get(table, [])]
            if not columns:
                log.warning("No columns for table %s — skipping", table)
                continue
            log.info("Migrating table: %s (%d columns)", table, len(columns))
            try:
                count = migrate_table(ora_cur, pg_conn, schema_ora, schema_pg, table, columns)
                summary.append({"table": table, "rows": count, "status": "OK"})
                log.info("  ✓ %s: %d rows", table, count)
            except Exception as exc:
                pg_conn.rollback()
                log.error("  ✗ %s: %s", table, exc)
                errors.append(f"{table}: {exc}")
                summary.append({"table": table, "rows": 0, "status": f"ERROR: {exc}"})

    finally:
        ora_cur.close()
        ora_conn.close()
        pg_conn.close()

    # Summary report
    log.info("=" * 60)
    log.info("Migration Summary")
    total_rows = sum(r["rows"] for r in summary)
    log.info("  Tables migrated: %d", len(summary))
    log.info("  Total rows     : %d", total_rows)
    log.info("  Errors         : %d", len(errors))
    for err in errors:
        log.error("  ERROR: %s", err)

    report_dir = Path(os.getenv("OUTPUT_DIR", "./output")) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "migration_summary.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "total_rows": total_rows, "errors": errors}, fh, indent=2)
    log.info("Report: %s", report_path)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
