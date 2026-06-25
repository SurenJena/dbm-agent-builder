#!/usr/bin/env python3
"""
count_validator.py — Row Count Validation
Compares row counts for every table between Oracle source and PostgreSQL target.
Generates a JSON report and exits non-zero if any mismatch is found.
"""

import json
import logging
import os
import sys
from datetime import datetime
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
        logging.FileHandler(LOG_DIR / "count_validator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


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


def get_oracle_count(cur, schema: str, table: str) -> int:
    cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
    return cur.fetchone()[0]


def get_pg_count(cur, schema: str, table: str) -> int:
    cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
    return cur.fetchone()[0]


def load_table_list() -> list:
    dep_path = OUTPUT_DIR / "ddl" / "dependency_order.json"
    if not dep_path.exists():
        log.error("Missing %s — run discovery first", dep_path)
        sys.exit(1)
    with open(dep_path, encoding="utf-8") as fh:
        return json.load(fh)["migration_order"]


def main():
    schema_ora = os.getenv("ORACLE_SCHEMA", "HR").upper()
    schema_pg  = os.getenv("PG_SCHEMA", "hr").lower()

    log.info("=" * 60)
    log.info("Row Count Validator")
    log.info("Oracle: %s  |  PostgreSQL: %s", schema_ora, schema_pg)
    log.info("Started: %s", datetime.now().isoformat())
    log.info("=" * 60)

    tables   = load_table_list()
    ora_conn = oracle_connect()
    pg_conn  = pg_connect()
    ora_cur  = ora_conn.cursor()
    pg_cur   = pg_conn.cursor()

    results   = []
    mismatches = 0

    try:
        for table in tables:
            try:
                ora_count = get_oracle_count(ora_cur, schema_ora, table)
                pg_count  = get_pg_count(pg_cur, schema_pg, table)
                match     = ora_count == pg_count
                if not match:
                    mismatches += 1
                    log.warning("  MISMATCH %-30s  Oracle=%d  PG=%d", table, ora_count, pg_count)
                else:
                    log.info("  OK       %-30s  %d rows", table, ora_count)
                results.append({
                    "table":      table,
                    "oracle_count": ora_count,
                    "pg_count":   pg_count,
                    "match":      match,
                })
            except Exception as exc:
                log.error("  ERROR %-30s  %s", table, exc)
                results.append({"table": table, "error": str(exc), "match": False})
                mismatches += 1
    finally:
        ora_cur.close()
        ora_conn.close()
        pg_cur.close()
        pg_conn.close()

    report = {
        "validated_at":   datetime.now().isoformat(),
        "oracle_schema":  schema_ora,
        "pg_schema":      schema_pg,
        "total_tables":   len(results),
        "mismatches":     mismatches,
        "results":        results,
    }
    report_path = OUTPUT_DIR / "reports" / "count_validation.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    log.info("-" * 60)
    log.info("Tables checked : %d", len(results))
    log.info("Mismatches     : %d", mismatches)
    log.info("Report         : %s", report_path)

    if mismatches:
        log.error("Count validation FAILED — %d mismatches", mismatches)
        sys.exit(1)
    else:
        log.info("Count validation PASSED ✓")


if __name__ == "__main__":
    main()
