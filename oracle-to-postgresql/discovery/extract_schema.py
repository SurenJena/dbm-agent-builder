#!/usr/bin/env python3
"""
extract_schema.py — Oracle Schema Metadata Extractor
Extracts complete schema metadata: tables, columns, constraints, indexes,
sequences, views, and triggers from Oracle source database.

Output: output/ddl/ directory with structured JSON metadata files.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

import oracledb
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "config" / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output")) / "ddl"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "extract_schema.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------
def get_oracle_connection():
    host     = os.getenv("ORACLE_HOST", "localhost")
    port     = int(os.getenv("ORACLE_PORT", "1521"))
    service  = os.getenv("ORACLE_SERVICE", "ORCL")
    user     = os.getenv("ORACLE_USER", "hr")
    password = os.getenv("ORACLE_PASSWORD", "hr")
    dsn = f"{host}:{port}/{service}"
    log.info("Connecting to Oracle: %s@%s", user, dsn)
    return oracledb.connect(user=user, password=password, dsn=dsn)


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------
def extract_tables(cur, schema: str) -> list:
    log.info("Extracting tables for schema: %s", schema)
    cur.execute(
        """
        SELECT table_name, num_rows, last_analyzed, partitioned, status
        FROM   all_tables
        WHERE  owner = :1
        ORDER  BY table_name
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log.info("  Found %d tables", len(rows))
    return rows


def extract_columns(cur, schema: str) -> list:
    log.info("Extracting columns...")
    cur.execute(
        """
        SELECT table_name, column_name, column_id, data_type,
               data_length, data_precision, data_scale, nullable,
               data_default, char_length
        FROM   all_tab_columns
        WHERE  owner = :1
        ORDER  BY table_name, column_id
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log.info("  Found %d columns", len(rows))
    return rows


def extract_constraints(cur, schema: str) -> list:
    log.info("Extracting constraints...")
    cur.execute(
        """
        SELECT c.table_name, c.constraint_name, c.constraint_type,
               c.status, c.validated, c.search_condition,
               c.r_owner, c.r_constraint_name, c.delete_rule
        FROM   all_constraints c
        WHERE  c.owner = :1
          AND  c.constraint_type IN ('P','U','R','C')
        ORDER  BY c.table_name, c.constraint_type, c.constraint_name
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log.info("  Found %d constraints", len(rows))
    return rows


def extract_constraint_columns(cur, schema: str) -> list:
    log.info("Extracting constraint columns...")
    cur.execute(
        """
        SELECT constraint_name, table_name, column_name, position
        FROM   all_cons_columns
        WHERE  owner = :1
        ORDER  BY constraint_name, position
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log.info("  Found %d constraint-column mappings", len(rows))
    return rows


def extract_indexes(cur, schema: str) -> list:
    log.info("Extracting indexes...")
    cur.execute(
        """
        SELECT i.index_name, i.table_name, i.index_type, i.uniqueness,
               i.status, i.partitioned
        FROM   all_indexes i
        WHERE  i.owner = :1
          AND  NOT EXISTS (
                 SELECT 1 FROM all_constraints c
                 WHERE  c.owner = :2
                   AND  c.constraint_name = i.index_name
                   AND  c.constraint_type IN ('P','U')
               )
        ORDER  BY i.table_name, i.index_name
        """,
        [schema.upper(), schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log.info("  Found %d non-constraint indexes", len(rows))
    return rows


def extract_index_columns(cur, schema: str) -> list:
    log.info("Extracting index columns...")
    cur.execute(
        """
        SELECT ic.index_name, ic.table_name, ic.column_name,
               ic.column_position, ic.descend
        FROM   all_ind_columns ic
        WHERE  ic.index_owner = :1
        ORDER  BY ic.index_name, ic.column_position
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log.info("  Found %d index-column mappings", len(rows))
    return rows


def extract_sequences(cur, schema: str) -> list:
    log.info("Extracting sequences...")
    cur.execute(
        """
        SELECT sequence_name, min_value, max_value, increment_by,
               cycle_flag, order_flag, cache_size, last_number
        FROM   all_sequences
        WHERE  sequence_owner = :1
        ORDER  BY sequence_name
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log.info("  Found %d sequences", len(rows))
    return rows


def extract_views(cur, schema: str) -> list:
    log.info("Extracting views...")
    cur.execute(
        """
        SELECT view_name, text
        FROM   all_views
        WHERE  owner = :1
        ORDER  BY view_name
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        # CLOB → str
        if hasattr(r.get("text"), "read"):
            r["text"] = r["text"].read()
        rows.append(r)
    log.info("  Found %d views", len(rows))
    return rows


def extract_triggers(cur, schema: str) -> list:
    log.info("Extracting triggers...")
    cur.execute(
        """
        SELECT trigger_name, table_name, trigger_type, triggering_event,
               status, trigger_body
        FROM   all_triggers
        WHERE  owner = :1
        ORDER  BY table_name, trigger_name
        """,
        [schema.upper()],
    )
    cols = [d[0].lower() for d in cur.description]
    rows = []
    for row in cur.fetchall():
        r = dict(zip(cols, row))
        if hasattr(r.get("trigger_body"), "read"):
            r["trigger_body"] = r["trigger_body"].read()
        rows.append(r)
    log.info("  Found %d triggers", len(rows))
    return rows


# ---------------------------------------------------------------------------
# JSON serialiser (handles Decimal / datetime from Oracle)
# ---------------------------------------------------------------------------
def _json_default(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def save_json(data: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=_json_default)
    log.info("  Saved %s", path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    schema = os.getenv("ORACLE_SCHEMA", "HR").upper()
    log.info("=" * 60)
    log.info("Oracle Schema Extractor")
    log.info("Schema : %s", schema)
    log.info("Started: %s", datetime.now().isoformat())
    log.info("=" * 60)

    conn = get_oracle_connection()
    cur  = conn.cursor()

    try:
        tables              = extract_tables(cur, schema)
        columns             = extract_columns(cur, schema)
        constraints         = extract_constraints(cur, schema)
        constraint_columns  = extract_constraint_columns(cur, schema)
        indexes             = extract_indexes(cur, schema)
        index_columns       = extract_index_columns(cur, schema)
        sequences           = extract_sequences(cur, schema)
        views               = extract_views(cur, schema)
        triggers            = extract_triggers(cur, schema)

        metadata = {
            "schema":             schema,
            "extracted_at":       datetime.now().isoformat(),
            "tables":             tables,
            "columns":            columns,
            "constraints":        constraints,
            "constraint_columns": constraint_columns,
            "indexes":            indexes,
            "index_columns":      index_columns,
            "sequences":          sequences,
            "views":              views,
            "triggers":           triggers,
        }

        out_path = OUTPUT_DIR / "schema_metadata.json"
        save_json(metadata, out_path)

        log.info("-" * 60)
        log.info("Extraction complete.")
        log.info("  Tables    : %d", len(tables))
        log.info("  Columns   : %d", len(columns))
        log.info("  Constraints: %d", len(constraints))
        log.info("  Indexes   : %d", len(indexes))
        log.info("  Sequences : %d", len(sequences))
        log.info("  Views     : %d", len(views))
        log.info("  Triggers  : %d", len(triggers))
        log.info("Output      : %s", out_path)

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
