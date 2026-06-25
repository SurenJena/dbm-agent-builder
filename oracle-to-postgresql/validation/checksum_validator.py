#!/usr/bin/env python3
"""
checksum_validator.py — Data Integrity / Checksum Validation
Samples rows from each table and computes MD5 checksums for comparison.
Numeric values are normalised via decimal.Decimal to prevent false
mismatches caused by Oracle returning float vs PostgreSQL returning Decimal.

Normalisation rule (MANDATORY):
  format(Decimal(str(val)).normalize(), 'f')
    24000.0         → '24000'
    Decimal('24000.00') → '24000'
    0.25 / Decimal('0.25') → '0.25'
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

import oracledb
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "config" / ".env")

LOG_DIR    = Path(os.getenv("LOG_DIR", "./logs"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "reports").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "checksum_validator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

SAMPLE_SIZE = int(os.getenv("CHECKSUM_SAMPLE_SIZE", "1000"))


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
# Canonical value serialiser
# ---------------------------------------------------------------------------
def canonical(val) -> str:
    """Produce a canonical string representation for checksum comparison."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float, Decimal)):
        return format(Decimal(str(val)).normalize(), "f")
    if isinstance(val, datetime):
        return val.replace(microsecond=0).isoformat(sep=" ")
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.hex()
    return str(val).strip()


def row_hash(row) -> str:
    """Compute MD5 of a tab-delimited row using canonical values."""
    return hashlib.md5("|".join(canonical(v) for v in row).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Samplers
# ---------------------------------------------------------------------------
def get_pk_columns(metadata: dict, table: str, con_cols: dict) -> list:
    for c in metadata["constraints"]:
        if c["constraint_type"] == "P" and c["table_name"] == table:
            return [cc["column_name"] for cc in sorted(
                con_cols.get(c["constraint_name"], []),
                key=lambda x: int(x.get("position") or 0),
            )]
    return []


def sample_oracle(cur, schema: str, table: str, columns: list, pk_cols: list, n: int) -> dict:
    pk_order     = ", ".join(f'"{c}"' for c in pk_cols)
    order_clause = f"ORDER BY {pk_order}" if pk_cols else ""
    col_expr     = ", ".join(f'"{c}"' for c in columns)
    cur.execute(
        f'SELECT {col_expr} FROM "{schema}"."{table}" {order_clause} FETCH FIRST :1 ROWS ONLY',
        [n],
    )
    return {row_hash(row): row for row in cur.fetchall()}


def sample_pg(cur, schema: str, table: str, columns: list, pk_cols: list, n: int) -> dict:
    pk_order     = ", ".join(f'"{c}"' for c in pk_cols)
    order_clause = f"ORDER BY {pk_order}" if pk_cols else ""
    col_expr     = ", ".join(f'"{c}"' for c in columns)
    cur.execute(
        f'SELECT {col_expr} FROM "{schema}"."{table}" {order_clause} LIMIT %s',
        (n,),
    )
    return {row_hash(row): row for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    schema_ora = os.getenv("ORACLE_SCHEMA", "HR").upper()
    schema_pg  = os.getenv("PG_SCHEMA", "hr").lower()

    log.info("=" * 60)
    log.info("Checksum Validator  (sample size: %d rows per table)", SAMPLE_SIZE)
    log.info("Oracle: %s  |  PostgreSQL: %s", schema_ora, schema_pg)
    log.info("Started: %s", datetime.now().isoformat())
    log.info("=" * 60)

    ddl_dir   = OUTPUT_DIR / "ddl"
    meta_path = ddl_dir / "schema_metadata.json"
    dep_path  = ddl_dir / "dependency_order.json"
    for p in (meta_path, dep_path):
        if not p.exists():
            log.error("Missing %s — run discovery first", p)
            sys.exit(1)

    with open(meta_path, encoding="utf-8") as fh:
        metadata = json.load(fh)
    with open(dep_path, encoding="utf-8") as fh:
        tables = json.load(fh)["migration_order"]

    # Build lookups
    col_map: dict[str, list] = {}
    for col in metadata["columns"]:
        col_map.setdefault(col["table_name"], []).append(col)
    for k in col_map:
        col_map[k].sort(key=lambda c: int(c.get("column_id") or 0))

    con_cols: dict[str, list] = {}
    for cc in metadata["constraint_columns"]:
        con_cols.setdefault(cc["constraint_name"], []).append(cc)

    ora_conn = oracle_connect()
    pg_conn  = pg_connect()
    ora_cur  = ora_conn.cursor()
    pg_cur   = pg_conn.cursor()

    results    = []
    mismatches = 0

    try:
        for table in tables:
            columns  = [c["column_name"] for c in col_map.get(table, [])]
            pk_cols  = get_pk_columns(metadata, table, con_cols)
            if not columns:
                continue
            try:
                ora_hashes = sample_oracle(ora_cur, schema_ora, table, columns, pk_cols, SAMPLE_SIZE)
                pg_hashes  = sample_pg(pg_cur, schema_pg, table, columns, pk_cols, SAMPLE_SIZE)

                common      = set(ora_hashes) & set(pg_hashes)
                only_ora    = set(ora_hashes) - set(pg_hashes)
                only_pg     = set(pg_hashes)  - set(ora_hashes)
                match_pct   = (len(common) / max(len(ora_hashes), 1)) * 100

                if only_ora or only_pg:
                    mismatches += 1
                    log.warning(
                        "  MISMATCH %-30s  ora_only=%d  pg_only=%d  match=%.1f%%",
                        table, len(only_ora), len(only_pg), match_pct,
                    )
                else:
                    log.info(
                        "  OK       %-30s  %d rows  match=%.1f%%",
                        table, len(common), match_pct,
                    )

                results.append({
                    "table":     table,
                    "sampled":   len(ora_hashes),
                    "matched":   len(common),
                    "ora_only":  len(only_ora),
                    "pg_only":   len(only_pg),
                    "match_pct": round(match_pct, 2),
                    "status":    "OK" if not (only_ora or only_pg) else "MISMATCH",
                })
            except Exception as exc:
                log.error("  ERROR %-30s  %s", table, exc)
                results.append({"table": table, "error": str(exc), "status": "ERROR"})
                mismatches += 1
    finally:
        ora_cur.close()
        ora_conn.close()
        pg_cur.close()
        pg_conn.close()

    report = {
        "validated_at":  datetime.now().isoformat(),
        "oracle_schema": schema_ora,
        "pg_schema":     schema_pg,
        "sample_size":   SAMPLE_SIZE,
        "total_tables":  len(results),
        "mismatches":    mismatches,
        "results":       results,
    }
    report_path = OUTPUT_DIR / "reports" / "checksum_validation.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    log.info("-" * 60)
    log.info("Tables checked : %d", len(results))
    log.info("Mismatches     : %d", mismatches)
    log.info("Report         : %s", report_path)

    if mismatches:
        log.error("Checksum validation FAILED — %d mismatches", mismatches)
        sys.exit(1)
    else:
        log.info("Checksum validation PASSED ✓")


if __name__ == "__main__":
    main()
