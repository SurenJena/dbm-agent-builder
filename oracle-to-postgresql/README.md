# Oracle to PostgreSQL Migration Framework

Production-ready migration framework for migrating Oracle schemas to PostgreSQL.

---

## 1. Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.9+    |
| psql client | 12+     |
| Oracle client (optional) | oracledb thin mode (no OCI needed) |

```bash
pip install -r requirements.txt
```

---

## 2. Configuration

```bash
# Copy the template and fill in your credentials
cp config/.env.template config/.env
```

Edit `config/.env` — all sensitive values live here and are never committed:

| Variable | Description | Default |
|----------|-------------|---------|
| `ORACLE_HOST` | Oracle host | `localhost` |
| `ORACLE_PORT` | Oracle listener port | `1521` |
| `ORACLE_SERVICE` | Oracle service name | `ORCL` |
| `ORACLE_SCHEMA` | Schema to migrate | `HR` |
| `ORACLE_USER` | Oracle user | `hr` |
| `ORACLE_PASSWORD` | Oracle password | — |
| `PG_HOST` | PostgreSQL host | `localhost` |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_DATABASE` | Target database | `hr_db` |
| `PG_SCHEMA` | Target schema | `hr` |
| `PG_USER` | PostgreSQL user | `postgres` |
| `PG_PASSWORD` | PostgreSQL password | — |
| `BATCH_SIZE` | Rows per copy batch | `10000` |

---

## 3. Project Structure

```
oracle-to-postgresql/
├── config/
│   ├── .env.template          # Credential template (committed)
│   ├── source_db.yaml         # Oracle config reference
│   ├── target_db.yaml         # PostgreSQL config reference
│   └── migration_config.yaml  # Migration settings & type map
├── discovery/
│   ├── extract_schema.py      # Extract full Oracle schema metadata
│   └── analyze_dependencies.py# Build FK-aware table migration order
├── conversion/
│   └── ddl_converter.py       # Convert Oracle DDL → PostgreSQL DDL
├── migration/
│   └── data_migrator.py       # Batch data migration (copy_expert)
├── validation/
│   ├── count_validator.py     # Row-count comparison
│   └── checksum_validator.py  # MD5 checksum sampling
├── scripts/
│   ├── run_migration.sh       # Main orchestrator (12-phase pipeline)
│   └── test_connections.py    # Connectivity + permission test
├── output/                    # Generated at runtime
│   ├── ddl/                   # Generated SQL files
│   ├── logs/                  # Phase-level Python logs
│   └── reports/               # Validation JSON + parity report
├── logs/                      # Shell orchestrator logs
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 4. Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp config/.env.template config/.env
# Edit config/.env

# 3. Run full migration
chmod +x scripts/run_migration.sh
./scripts/run_migration.sh

# 4. Schema-only (no data, no validation)
./scripts/run_migration.sh --schema-only

# 5. Skip validation (run all phases except checksum/count)
./scripts/run_migration.sh --skip-validation

# 6. Data-only (schema already in PG, re-migrate data)
./scripts/run_migration.sh --data-only
```

---

## 5. Phase Sequence

| Phase | Description | Skip Flag |
|-------|-------------|-----------|
| 0 | Prerequisites + `__pycache__` purge | never |
| 1 | Connection tests | never |
| 2 | Schema discovery | `--data-only` |
| 3 | DDL conversion | `--data-only` |
| 4 | Apply schema (tables → sequences → PK/UK) | `--data-only` |
| 5 | Data migration | `--schema-only` |
| 6 | Post-data DDL (FK → CHECK → indexes) | never |
| 7 | View creation | never |
| 8 | Row-count validation | `--schema-only` / `--skip-validation` |
| 9 | Checksum validation | `--schema-only` / `--skip-validation` |
| 10 | Schema parity validation | never |
| 11 | ANALYZE / statistics | never |

Every phase is **idempotent** — a full re-run is always safe.

---

## 6. Data Type Mapping

| Oracle Type | PostgreSQL Type |
|-------------|----------------|
| `NUMBER` (no precision) | `NUMERIC` |
| `NUMBER(p,0)` p ≤ 9 | `INTEGER` |
| `NUMBER(p,0)` p ≤ 18 | `BIGINT` |
| `NUMBER(p,s)` | `NUMERIC(p,s)` |
| `VARCHAR2(n)` / `NVARCHAR2(n)` | `VARCHAR(n)` |
| `CHAR(n)` / `NCHAR(n)` | `CHAR(n)` |
| `CLOB` / `NCLOB` / `LONG` | `TEXT` |
| `BLOB` / `RAW` / `LONG RAW` | `BYTEA` |
| `DATE` | `TIMESTAMP` |
| `TIMESTAMP` | `TIMESTAMP` |
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP WITH TIME ZONE` |
| `FLOAT` / `BINARY_DOUBLE` | `DOUBLE PRECISION` |
| `BINARY_FLOAT` | `REAL` |
| `XMLTYPE` | `XML` |

---

## 7. Validation Reports

After a full run, three reports are generated in `output/reports/`:

| Report | Description |
|--------|-------------|
| `count_validation.json` | Per-table row counts (Oracle vs PostgreSQL) |
| `checksum_validation.json` | MD5 row-hash comparison for sampled rows |
| `schema_parity.txt` | Object count comparison (tables, views, sequences, indexes, constraints) |

---

## 8. Rollback

There is no automated rollback — PostgreSQL is the target and Oracle remains
untouched throughout the migration.  To roll back:

1. Stop all application connections to the PostgreSQL target.
2. Drop the target schema: `DROP SCHEMA hr CASCADE;`
3. Point applications back to the Oracle source.
4. Investigate the root cause using `logs/` and `output/reports/`.
5. Re-run the migration after correcting the issue.

---

## 9. Troubleshooting

| Symptom | Resolution |
|---------|-----------|
| `ORA-01045` | Grant `CREATE SESSION` to Oracle user |
| `psycopg2.OperationalError` | Check `PG_HOST`, `PG_PORT`, `PG_DATABASE` in `.env` |
| Count mismatch | Check `output/reports/count_validation.json` for specific tables |
| Checksum mismatch | Inspect `output/reports/checksum_validation.json`; check data-type mappings |
| Schema parity errors | Review `output/reports/schema_parity.txt`; re-run Phase 6 DDL files manually |
| `__pycache__` stale code | Phase 0 purges automatically; or run `find . -name __pycache__ -exec rm -rf {} +` |
| Sequence out of range | Verify `last_number` extraction; check `MAXVALUE` capped to `9223372036854775807` |
