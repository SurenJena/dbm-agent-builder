#!/usr/bin/env python3
"""
ddl_converter.py — Oracle DDL → PostgreSQL DDL Converter
Reads schema_metadata.json and dependency_order.json, then generates:
  output/ddl/01_tables.sql        — CREATE TABLE statements
  output/ddl/02_sequences.sql     — CREATE SEQUENCE statements
  output/ddl/03_pk_uk.sql         — PRIMARY KEY / UNIQUE constraints
  output/ddl/04_fk.sql            — FOREIGN KEY constraints
  output/ddl/05_check.sql         — CHECK constraints
  output/ddl/06_indexes.sql       — CREATE INDEX statements
  output/ddl/07_views.sql         — CREATE OR REPLACE VIEW statements
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / "config" / ".env")

LOG_DIR    = Path(os.getenv("LOG_DIR", "./logs"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output")) / "ddl"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "ddl_converter.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# PostgreSQL BIGINT upper bound — Oracle MAXVALUE can exceed this
PG_BIGINT_MAX = 9_223_372_036_854_775_807


# ---------------------------------------------------------------------------
# Data-type mapping
# ---------------------------------------------------------------------------
def map_oracle_type(
    data_type: str,
    data_length,
    data_precision,
    data_scale,
    char_length,
) -> str:
    dt = (data_type or "").upper().strip()

    if dt == "NUMBER":
        prec  = int(data_precision) if data_precision not in (None, "") else None
        scale = int(data_scale)     if data_scale      not in (None, "") else None
        if prec is not None and scale in (None, 0):
            if prec <= 9:
                return "INTEGER"
            if prec <= 18:
                return "BIGINT"
            return f"NUMERIC({prec})"
        if prec is not None and scale is not None:
            return f"NUMERIC({prec},{scale})"
        return "NUMERIC"

    if dt in ("VARCHAR2", "NVARCHAR2"):
        length = int(char_length or data_length or 255)
        return f"VARCHAR({length})"

    if dt in ("CHAR", "NCHAR"):
        length = int(char_length or data_length or 1)
        return f"CHAR({length})"

    if dt in ("CLOB", "NCLOB", "LONG"):
        return "TEXT"

    if dt == "BLOB":
        return "BYTEA"

    if dt in ("RAW", "LONG RAW"):
        return "BYTEA"

    if dt == "DATE":
        return "TIMESTAMP"

    if dt.startswith("TIMESTAMP"):
        if "WITH TIME ZONE" in dt:
            return "TIMESTAMP WITH TIME ZONE"
        if "WITH LOCAL TIME ZONE" in dt:
            return "TIMESTAMP WITH TIME ZONE"
        return "TIMESTAMP"

    if dt in ("FLOAT", "BINARY_DOUBLE"):
        return "DOUBLE PRECISION"

    if dt == "BINARY_FLOAT":
        return "REAL"

    if dt == "XMLTYPE":
        return "XML"

    if dt.startswith("INTERVAL YEAR"):
        return "INTERVAL"

    if dt.startswith("INTERVAL DAY"):
        return "INTERVAL"

    # fallback
    log.warning("Unknown Oracle type '%s' — mapping to TEXT", dt)
    return "TEXT"


# ---------------------------------------------------------------------------
# CHECK constraint search_condition rewriter
# Converts Oracle lowercase column names to double-quoted UPPERCASE tokens
# ---------------------------------------------------------------------------
_KEYWORDS = {
    "AND", "OR", "NOT", "IN", "IS", "NULL", "LIKE", "BETWEEN",
    "TRUE", "FALSE", "UNKNOWN", "EXISTS", "ALL", "ANY",
}

def rewrite_check_condition(condition: str) -> str:
    """
    Tokenise the Oracle search_condition and wrap bare identifiers in
    double-quoted UPPERCASE names so PostgreSQL can resolve them.

    Oracle stores: end_date > start_date
    Needed:        "END_DATE" > "START_DATE"
    """
    tokens = re.findall(r"'[^']*'|\"[^\"]*\"|[A-Za-z_][A-Za-z0-9_$#]*|[^A-Za-z_'\"\s]+|\s+", condition)
    result = []
    for tok in tokens:
        if tok.startswith("'") or tok.startswith('"'):
            result.append(tok)
        elif re.match(r"^[A-Za-z_][A-Za-z0-9_$#]*$", tok):
            upper = tok.upper()
            if upper in _KEYWORDS or re.match(r"^\d+$", upper):
                result.append(upper)
            else:
                result.append(f'"{upper}"')   # MUST uppercase before quoting
        else:
            result.append(tok)
    return "".join(result)


# ---------------------------------------------------------------------------
# idempotent ADD CONSTRAINT wrapper
# ---------------------------------------------------------------------------
def pg_add_constraint(schema: str, table: str, cname: str, body: str) -> str:
    """Wraps ALTER TABLE … ADD CONSTRAINT in a pg_constraint NOT EXISTS guard."""
    return (
        f"DO $$ BEGIN\n"
        f"  IF NOT EXISTS (\n"
        f"    SELECT 1 FROM pg_constraint c\n"
        f"    JOIN pg_namespace n ON n.oid = c.connamespace\n"
        f"    WHERE n.nspname = '{schema}' AND c.conname = '{cname}'\n"
        f"  ) THEN\n"
        f"    ALTER TABLE \"{schema}\".\"{table}\" ADD CONSTRAINT \"{cname}\" {body};\n"
        f"  END IF;\n"
        f"END $$;\n"
    )


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def gen_tables(metadata: dict, dep_order: list, schema: str) -> str:
    col_map: dict[str, list] = {}
    for col in metadata["columns"]:
        col_map.setdefault(col["table_name"], []).append(col)

    lines = [
        "-- =============================================================",
        "-- 01_tables.sql  —  CREATE TABLE (without constraints)",
        f"-- Schema: {schema}",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- =============================================================\n",
    ]

    for table in dep_order:
        cols = sorted(col_map.get(table, []), key=lambda c: int(c.get("column_id") or 0))
        if not cols:
            log.warning("Table %s has no columns — skipping", table)
            continue

        lines.append(f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" (')
        col_defs = []
        for col in cols:
            pg_type  = map_oracle_type(
                col["data_type"],
                col.get("data_length"),
                col.get("data_precision"),
                col.get("data_scale"),
                col.get("char_length"),
            )
            nullable = "" if col.get("nullable") == "Y" else " NOT NULL"
            # skip DEFAULT — complex Oracle expressions rarely translate cleanly
            col_defs.append(f'  "{col["column_name"]}" {pg_type}{nullable}')

        lines.append(",\n".join(col_defs))
        lines.append(");\n")

    return "\n".join(lines)


def gen_sequences(metadata: dict, schema: str) -> str:
    lines = [
        "-- =============================================================",
        "-- 02_sequences.sql  —  CREATE SEQUENCE",
        f"-- Schema: {schema}",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- =============================================================\n",
    ]

    for seq in metadata["sequences"]:
        name         = seq["sequence_name"]
        start        = int(seq.get("last_number") or 1)
        increment    = int(seq.get("increment_by") or 1)
        min_val      = int(seq.get("min_value") or 1)
        raw_max      = seq.get("max_value")
        max_val      = min(int(raw_max), PG_BIGINT_MAX) if raw_max else PG_BIGINT_MAX
        cache        = int(seq.get("cache_size") or 20)
        cycle        = "CYCLE" if seq.get("cycle_flag") == "Y" else "NO CYCLE"

        lines.append(
            f'CREATE SEQUENCE IF NOT EXISTS "{schema}"."{name}"\n'
            f"  START WITH {start}\n"
            f"  INCREMENT BY {increment}\n"
            f"  MINVALUE {min_val}\n"
            f"  MAXVALUE {max_val}\n"
            f"  CACHE {cache}\n"
            f"  {cycle};\n"
        )

    return "\n".join(lines)


def gen_pk_uk(metadata: dict, schema: str) -> str:
    # Build column lookup: constraint_name → [col, ...]
    con_cols: dict[str, list] = {}
    for cc in metadata["constraint_columns"]:
        con_cols.setdefault(cc["constraint_name"], []).append(cc)
    for k in con_cols:
        con_cols[k].sort(key=lambda x: int(x.get("position") or 0))

    lines = [
        "-- =============================================================",
        "-- 03_pk_uk.sql  —  PRIMARY KEY / UNIQUE constraints",
        f"-- Schema: {schema}",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- =============================================================\n",
    ]

    for c in metadata["constraints"]:
        if c["constraint_type"] not in ("P", "U"):
            continue
        if c.get("status") == "DISABLED":
            continue
        cname  = c["constraint_name"]
        table  = c["table_name"]
        ctype  = "PRIMARY KEY" if c["constraint_type"] == "P" else "UNIQUE"
        cols   = con_cols.get(cname, [])
        if not cols:
            log.warning("Constraint %s has no columns — skipping", cname)
            continue
        col_list = ", ".join(f'"{cc["column_name"]}"' for cc in cols)
        body = f"{ctype} ({col_list})"
        lines.append(pg_add_constraint(schema, table, cname, body))

    return "\n".join(lines)


def gen_fk(metadata: dict, schema: str) -> str:
    con_cols: dict[str, list] = {}
    for cc in metadata["constraint_columns"]:
        con_cols.setdefault(cc["constraint_name"], []).append(cc)
    for k in con_cols:
        con_cols[k].sort(key=lambda x: int(x.get("position") or 0))

    # Build PK/UK constraint → table + columns index
    pk_info: dict[str, dict] = {}
    for c in metadata["constraints"]:
        if c["constraint_type"] in ("P", "U"):
            pk_info[c["constraint_name"]] = {
                "table":   c["table_name"],
                "columns": [cc["column_name"] for cc in con_cols.get(c["constraint_name"], [])],
            }

    lines = [
        "-- =============================================================",
        "-- 04_fk.sql  —  FOREIGN KEY constraints (applied after data load)",
        f"-- Schema: {schema}",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- =============================================================\n",
    ]

    for c in metadata["constraints"]:
        if c["constraint_type"] != "R":
            continue
        if c.get("status") == "DISABLED":
            continue
        cname   = c["constraint_name"]
        table   = c["table_name"]
        r_con   = c.get("r_constraint_name", "")
        ref     = pk_info.get(r_con)
        if not ref:
            log.warning("FK %s: cannot resolve referenced constraint %s — skipping", cname, r_con)
            continue

        child_cols = con_cols.get(cname, [])
        if not child_cols:
            log.warning("FK %s has no columns — skipping", cname)
            continue

        child_col_list = ", ".join(f'"{cc["column_name"]}"' for cc in child_cols)
        ref_col_list   = ", ".join(f'"{col}"'              for col in ref["columns"])
        ref_table      = ref["table"]
        delete_rule    = c.get("delete_rule") or "NO ACTION"
        delete_clause  = f" ON DELETE {delete_rule}" if delete_rule != "NO ACTION" else ""

        body = (
            f'FOREIGN KEY ({child_col_list}) '
            f'REFERENCES "{schema}"."{ref_table}" ({ref_col_list}){delete_clause}'
        )
        lines.append(pg_add_constraint(schema, table, cname, body))

    return "\n".join(lines)


def gen_check(metadata: dict, schema: str) -> str:
    lines = [
        "-- =============================================================",
        "-- 05_check.sql  —  CHECK constraints",
        f"-- Schema: {schema}",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- =============================================================\n",
    ]

    for c in metadata["constraints"]:
        if c["constraint_type"] != "C":
            continue
        if c.get("status") == "DISABLED":
            continue
        condition = c.get("search_condition") or ""
        # Skip Oracle system NOT NULL check constraints
        if re.match(r'^\s*"?\w+"?\s+IS\s+NOT\s+NULL\s*$', condition, re.IGNORECASE):
            continue
        cname     = c["constraint_name"]
        table     = c["table_name"]
        pg_cond   = rewrite_check_condition(condition)
        body      = f"CHECK ({pg_cond})"
        lines.append(pg_add_constraint(schema, table, cname, body))

    return "\n".join(lines)


def gen_indexes(metadata: dict, schema: str) -> str:
    idx_cols: dict[str, list] = {}
    for ic in metadata["index_columns"]:
        idx_cols.setdefault(ic["index_name"], []).append(ic)
    for k in idx_cols:
        idx_cols[k].sort(key=lambda x: int(x.get("column_position") or 0))

    lines = [
        "-- =============================================================",
        "-- 06_indexes.sql  —  CREATE INDEX",
        f"-- Schema: {schema}",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- =============================================================\n",
    ]

    for idx in metadata["indexes"]:
        iname  = idx["index_name"]
        table  = idx["table_name"]
        unique = "UNIQUE " if idx.get("uniqueness") == "UNIQUE" else ""
        cols   = idx_cols.get(iname, [])
        if not cols:
            log.warning("Index %s has no columns — skipping", iname)
            continue
        col_list = ", ".join(
            f'"{ic["column_name"]}" {"DESC" if ic.get("descend") == "DESC" else "ASC"}'
            for ic in cols
        )
        lines.append(
            f'CREATE {unique}INDEX IF NOT EXISTS "{iname}" '
            f'ON "{schema}"."{table}" ({col_list});\n'
        )

    return "\n".join(lines)


def gen_views(metadata: dict, schema: str) -> str:
    lines = [
        "-- =============================================================",
        "-- 07_views.sql  —  CREATE OR REPLACE VIEW",
        f"-- Schema: {schema}",
        f"-- Generated: {datetime.now().isoformat()}",
        "-- NOTE: Oracle-specific syntax may require manual adjustment",
        "-- =============================================================\n",
    ]

    for v in metadata["views"]:
        vname = v["view_name"]
        text  = (v.get("text") or "").strip()
        # Basic Oracle→PG conversions
        text = re.sub(r"\bSYSDATE\b",    "CURRENT_TIMESTAMP",       text, flags=re.IGNORECASE)
        text = re.sub(r"\bFROM\s+DUAL\b","",                        text, flags=re.IGNORECASE)
        text = re.sub(r"\bNVL\s*\(",     "COALESCE(",                text, flags=re.IGNORECASE)
        text = re.sub(r"\bTO_DATE\s*\(", "TO_TIMESTAMP(",            text, flags=re.IGNORECASE)
        text = re.sub(r"\bTO_CHAR\s*\(", "TO_CHAR(",                 text, flags=re.IGNORECASE)
        text = re.sub(r"\|\|",           "||",                       text)   # already PG syntax
        lines.append(
            f'CREATE OR REPLACE VIEW "{schema}"."{vname}" AS\n{text};\n'
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    schema = os.getenv("ORACLE_SCHEMA", "HR").upper()
    pg_schema = os.getenv("PG_SCHEMA", "hr").lower()

    log.info("=" * 60)
    log.info("DDL Converter")
    log.info("Oracle schema : %s  →  PostgreSQL schema: %s", schema, pg_schema)
    log.info("Started       : %s", datetime.now().isoformat())
    log.info("=" * 60)

    meta_path = OUTPUT_DIR / "schema_metadata.json"
    dep_path  = OUTPUT_DIR / "dependency_order.json"

    if not meta_path.exists():
        log.error("Missing %s — run extract_schema.py first", meta_path)
        sys.exit(1)
    if not dep_path.exists():
        log.error("Missing %s — run analyze_dependencies.py first", dep_path)
        sys.exit(1)

    with open(meta_path, encoding="utf-8") as fh:
        metadata = json.load(fh)
    with open(dep_path, encoding="utf-8") as fh:
        dep_data = json.load(fh)

    dep_order = dep_data["migration_order"]

    outputs = {
        "01_tables.sql":    gen_tables(metadata, dep_order, pg_schema),
        "02_sequences.sql": gen_sequences(metadata, pg_schema),
        "03_pk_uk.sql":     gen_pk_uk(metadata, pg_schema),
        "04_fk.sql":        gen_fk(metadata, pg_schema),
        "05_check.sql":     gen_check(metadata, pg_schema),
        "06_indexes.sql":   gen_indexes(metadata, pg_schema),
        "07_views.sql":     gen_views(metadata, pg_schema),
    }

    for filename, content in outputs.items():
        path = OUTPUT_DIR / filename
        path.write_text(content, encoding="utf-8")
        log.info("Written: %s", path)

    log.info("-" * 60)
    log.info("DDL conversion complete.")


if __name__ == "__main__":
    main()
