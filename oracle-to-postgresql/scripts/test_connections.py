#!/usr/bin/env python3
"""
test_connections.py — Oracle and PostgreSQL Connectivity Test
Validates source and target connections, permissions, and versions
before running any migration phase.  Exits non-zero on any failure.
"""

import os
import sys
import logging
from pathlib import Path

import oracledb
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "config" / ".env")

LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "test_connections.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Oracle tests
# ---------------------------------------------------------------------------
def test_oracle() -> bool:
    host     = os.getenv("ORACLE_HOST", "localhost")
    port     = os.getenv("ORACLE_PORT", "1521")
    service  = os.getenv("ORACLE_SERVICE", "ORCL")
    schema   = os.getenv("ORACLE_SCHEMA", "HR").upper()
    user     = os.getenv("ORACLE_USER", "hr")
    password = os.getenv("ORACLE_PASSWORD", "hr")
    dsn      = f"{host}:{port}/{service}"

    log.info("Testing Oracle connection: %s@%s (schema=%s)", user, dsn, schema)
    try:
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        cur  = conn.cursor()

        # Version
        cur.execute("SELECT * FROM v$version WHERE ROWNUM = 1")
        version = cur.fetchone()[0]
        log.info("  Oracle version : %s", version)

        # Table count
        cur.execute(
            "SELECT COUNT(*) FROM all_tables WHERE owner = :1",
            [schema],
        )
        table_count = cur.fetchone()[0]
        log.info("  Tables in %s : %d", schema, table_count)

        if table_count == 0:
            log.warning("  WARNING: No tables found in schema %s", schema)

        # SELECT privilege check
        cur.execute(
            "SELECT COUNT(*) FROM all_tab_privs "
            "WHERE grantee = :1 AND privilege = 'SELECT'",
            [user.upper()],
        )
        priv_count = cur.fetchone()[0]
        log.info("  SELECT grants  : %d", priv_count)

        cur.close()
        conn.close()
        log.info("  ✓ Oracle connection OK")
        return True

    except Exception as exc:
        log.error("  ✗ Oracle connection FAILED: %s", exc)
        return False


# ---------------------------------------------------------------------------
# PostgreSQL tests
# ---------------------------------------------------------------------------
def test_postgresql() -> bool:
    host     = os.getenv("PG_HOST", "localhost")
    port     = os.getenv("PG_PORT", "5432")
    dbname   = os.getenv("PG_DATABASE", "hr_db")
    schema   = os.getenv("PG_SCHEMA", "hr").lower()
    user     = os.getenv("PG_USER", "postgres")
    password = os.getenv("PG_PASSWORD", "postgres")

    log.info("Testing PostgreSQL connection: %s@%s:%s/%s (schema=%s)", user, host, port, dbname, schema)
    try:
        conn = psycopg2.connect(
            host=host, port=int(port), dbname=dbname, user=user, password=password
        )
        cur = conn.cursor()

        # Version
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        log.info("  PostgreSQL version : %s", version)

        # Schema existence
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
            (schema,),
        )
        schema_exists = cur.fetchone()[0]
        if schema_exists:
            log.info("  Schema '%s' : exists", schema)
        else:
            log.info("  Schema '%s' : does NOT exist (will be created)", schema)

        # CREATE privileges
        cur.execute(
            "SELECT has_database_privilege(%s, %s, 'CREATE')",
            (user, dbname),
        )
        can_create = cur.fetchone()[0]
        log.info("  CREATE privilege on DB : %s", can_create)
        if not can_create:
            log.warning("  WARNING: user %s lacks CREATE on database %s", user, dbname)

        # Ensure schema exists
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        conn.commit()
        log.info("  Schema '%s' ensured.", schema)

        cur.close()
        conn.close()
        log.info("  ✓ PostgreSQL connection OK")
        return True

    except Exception as exc:
        log.error("  ✗ PostgreSQL connection FAILED: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("Connection Tests")
    log.info("=" * 60)

    ora_ok = test_oracle()
    pg_ok  = test_postgresql()

    log.info("-" * 60)
    log.info("Oracle     : %s", "PASS ✓" if ora_ok else "FAIL ✗")
    log.info("PostgreSQL : %s", "PASS ✓" if pg_ok  else "FAIL ✗")

    if not (ora_ok and pg_ok):
        log.error("One or more connection tests FAILED — aborting migration")
        sys.exit(1)

    log.info("All connection tests PASSED ✓")


if __name__ == "__main__":
    main()
