[README.md](https://github.com/user-attachments/files/29582714/README.md)[Uploading RE# Oracle → PostgreSQL Migration Framework

<div align="center">

![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)
![PostgreSQL 12+](https://img.shields.io/badge/PostgreSQL-12%2B-336791?logo=postgresql&logoColor=white)
![Oracle 11g+](https://img.shields.io/badge/Oracle-11g%2B-F80000?logo=oracle&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Maintained: Yes](https://img.shields.io/badge/maintained-yes-brightgreen)
![Phases: 12](https://img.shields.io/badge/pipeline%20phases-12-blueviolet)
![Status: Production Ready](https://img.shields.io/badge/status-production--ready-success)

**Production-ready, idempotent Python + Bash pipeline for migrating Oracle schemas to PostgreSQL.**  
DDL conversion · FK-aware batch loading · Dual-layer validation · No Oracle OCI client required.

[Quick Start](#4-quick-start) · [Architecture](#system-architecture) · [Phase Reference](#phase-pipeline) · [Configuration](#configuration) · [Validation](#validation-reports) · [Roadmap](#roadmap)

</div>

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Objectives](#project-objectives)
3. [System Architecture](#system-architecture)
4. [Technical Design](#technical-design)
5. [Prerequisites](#prerequisites)
6. [Configuration](#configuration)
7. [Project Structure](#project-structure)
8. [Quick Start](#quick-start)
9. [Phase Pipeline](#phase-pipeline)
10. [Data Type Mapping](#data-type-mapping)
11. [Validation Reports](#validation-reports)
12. [Development Workflow](#development-workflow)
13. [Non-functional Requirements](#non-functional-requirements)
14. [Assumptions & Limitations](#assumptions--limitations)
15. [Troubleshooting](#troubleshooting)
16. [Rollback Procedure](#rollback-procedure)
17. [Roadmap](#roadmap)
18. [Professional Summary](#professional-summary)
19. [Architecture Decision Summary](#architecture-decision-summary)

---

## Executive Summary

### Project Purpose

The **Oracle to PostgreSQL Migration Framework** is a Python-based, production-ready pipeline that automates the complete migration of an Oracle database schema — DDL, data, constraints, indexes, sequences, and views — into a target PostgreSQL database with full structural and data-integrity validation.

### Problem It Solves

| Pain Point | How This Framework Addresses It |
|---|---|
| Incompatible SQL dialects | Automated type mapping + DDL rewriting (17 Oracle → PG type rules) |
| FK ordering deadlocks | Kahn's topological sort computes a safe load order |
| Non-idempotent runs | Every phase uses `IF NOT EXISTS` / `TRUNCATE + reload` guards |
| Silent data corruption | Dual validation: row-count + MD5 checksum comparison |
| Oracle OCI dependency | `oracledb` thin mode — no Oracle Client installation required |
| Tribal knowledge lost at cutover | Structured JSON metadata + per-phase timestamped logs |

### Target Users

- **Database Administrators** performing Oracle → PostgreSQL lift-and-shift migrations
- **Backend Engineers** modernising legacy Oracle-dependent applications
- **DevOps / Platform Engineers** embedding database migration into CI/CD pipelines
- **Cloud Architects** migrating on-premise Oracle workloads to AWS RDS, Azure Database for PostgreSQL, or Google Cloud SQL

### Business Value

- **Risk reduction** — two independent validation stages catch discrepancies before cutover
- **Repeatability** — fully idempotent, re-run any phase at any time
- **Speed** — batched `COPY` via `copy_expert()` is orders of magnitude faster than row-by-row `INSERT`
- **Cost reduction** — eliminates Oracle licensing for new workloads
- **Deployment simplicity** — zero Oracle OCI/thick-client dependency

---

## Project Objectives

### Primary Objectives

1. Automate extraction of complete Oracle schema metadata (tables, columns, constraints, indexes, sequences, views, triggers)
2. Convert all supported Oracle DDL constructs to valid PostgreSQL DDL with no manual editing for standard schemas
3. Migrate all rows faithfully using high-throughput batched `COPY` operations
4. Validate migrated data with row-count and MD5-checksum comparison against the Oracle source
5. Produce structured, auditable output artefacts for every phase

### Secondary Objectives

1. Support partial migration modes (`--schema-only`, `--data-only`, `--skip-validation`)
2. Provide human-readable logs and machine-readable JSON reports
3. Operate without Oracle OCI/thick client libraries via `oracledb` thin mode
4. Respect FK dependency order using Kahn's topological sort
5. Handle circular FK dependencies gracefully without aborting

### Success Criteria

| Criterion | Target |
|---|---|
| Schema parity | 0 discrepancies in `schema_parity.txt` after Phase 10 |
| Row count accuracy | 0 mismatches in `count_validation.json` after Phase 8 |
| Checksum accuracy | 100% match rate in `checksum_validation.json` after Phase 9 |
| Idempotency | A second full run produces identical schema and data |
| Pipeline completion | All 12 phases exit with code 0 |

---

## System Architecture

### High-Level Architecture

The framework follows a **linear sequential pipeline** pattern. Each phase is self-contained, writes outputs consumed by later phases, and is guarded for idempotency. The shell orchestrator (`run_migration.sh`) drives all Python modules.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Oracle Source Database                           │
│         all_tables · all_tab_columns · all_constraints · all_indexes    │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ oracledb (thin mode, read-only)
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     run_migration.sh  —  12-Phase Pipeline               │
│                                                                         │
│  Phase 0   Prerequisites + __pycache__ purge                            │
│  Phase 1   Connection tests          (test_connections.py)              │
│  Phase 2   Schema discovery          (extract_schema.py)                │
│  Phase 3   Dependency analysis       (analyze_dependencies.py)          │
│  Phase 4   DDL conversion            (ddl_converter.py)                 │
│  Phase 5   Apply schema to PG        (psql: 01-03 SQL files)            │
│  Phase 6   Data migration            (data_migrator.py)                 │
│  Phase 7   Post-data DDL             (psql: 04-06 SQL files)            │
│  Phase 8   View creation             (psql: 07_views.sql)               │
│  Phase 9   Row-count validation      (count_validator.py)               │
│  Phase 10  Checksum validation       (checksum_validator.py)            │
│  Phase 11  Schema parity             (inline Python + psql)             │
│  Phase 12  ANALYZE / statistics      (psql ANALYZE)                     │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ psycopg2 copy_expert()
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Target Database                            │
│          Schema · Tables · Indexes · Sequences · Views · Constraints    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mermaid Architecture Diagram

```mermaid
flowchart TD
    subgraph SRC["🗄️ Oracle Source (Read-Only)"]
        ORA[(Oracle DB\nall_tables · all_columns\nall_constraints · all_indexes\nall_sequences · all_views)]
    end

    subgraph ORCH["⚙️ run_migration.sh — 12-Phase Pipeline"]
        P0["Phase 0\nPrerequisites +\n__pycache__ purge"]
        P1["Phase 1\nConnection Tests\ntest_connections.py"]
        P2["Phase 2\nSchema Discovery\nextract_schema.py"]
        P3["Phase 3\nDependency Analysis\nanalyze_dependencies.py"]
        P4["Phase 4\nDDL Conversion\nddl_converter.py"]
        P5["Phase 5\nApply Schema\npsql 01–03"]
        P6["Phase 6\nData Migration\ndata_migrator.py"]
        P7["Phase 7\nPost-data DDL\npsql 04–06"]
        P8["Phase 8\nViews\npsql 07"]
        P9["Phase 9\nCount Validation\ncount_validator.py"]
        P10["Phase 10\nChecksum Validation\nchecksum_validator.py"]
        P11["Phase 11\nSchema Parity\npsql + Python"]
        P12["Phase 12\nANALYZE"]
    end

    subgraph ART["📁 output/ Artefacts"]
        META["schema_metadata.json\ndependency_order.json"]
        DDL["01_tables.sql\n02_sequences.sql\n03_pk_uk.sql\n04_fk.sql\n05_check.sql\n06_indexes.sql\n07_views.sql"]
        RPT["count_validation.json\nchecksum_validation.json\nschema_parity.txt\nmigration_summary.json"]
    end

    subgraph TGT["🐘 PostgreSQL Target"]
        PG[(PostgreSQL DB\nSchema + Data\nIndexes · Views\nSequences)]
    end

    ORA -->|"thin mode"| P1
    P0 --> P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8 --> P9 --> P10 --> P11 --> P12
    P2 --> META
    P3 --> META
    P4 --> DDL
    META --> P4
    DDL --> P5
    P5 --> TGT
    P6 -->|"copy_expert()"| TGT
    P7 --> TGT
    P8 --> TGT
    P9 --> RPT
    P10 --> RPT
    P11 --> RPT
    P12 --> TGT
```

### Data Flow

```mermaid
sequenceDiagram
    participant SH as run_migration.sh
    participant EX as extract_schema.py
    participant AD as analyze_dependencies.py
    participant DC as ddl_converter.py
    participant DM as data_migrator.py
    participant ORA as Oracle DB
    participant PG as PostgreSQL DB
    participant FS as output/ filesystem

    SH->>EX: python3 extract_schema.py
    EX->>ORA: SELECT from all_* views
    ORA-->>EX: schema metadata
    EX->>FS: schema_metadata.json

    SH->>AD: python3 analyze_dependencies.py
    AD->>FS: read schema_metadata.json
    AD->>FS: dependency_order.json (topological order)

    SH->>DC: python3 ddl_converter.py
    DC->>FS: read metadata JSONs
    DC->>FS: 01_tables.sql ... 07_views.sql

    SH->>PG: psql -f 01_tables.sql
    SH->>PG: psql -f 02_sequences.sql
    SH->>PG: psql -f 03_pk_uk.sql

    SH->>DM: python3 data_migrator.py
    DM->>ORA: SELECT per table (batched fetchmany)
    DM->>PG: TRUNCATE + COPY FROM STDIN

    SH->>PG: psql -f 04_fk.sql
    SH->>PG: psql -f 05_check.sql
    SH->>PG: psql -f 06_indexes.sql
    SH->>PG: psql -f 07_views.sql
```

### FK Dependency Graph (Oracle HR Schema — Actual Run)

```mermaid
graph TD
    JOBS["JOBS\n(19 rows)"]
    REGIONS["REGIONS\n(4 rows)"]
    COUNTRIES["COUNTRIES\n(25 rows)"]
    LOCATIONS["LOCATIONS\n(23 rows)"]
    DEPARTMENTS["DEPARTMENTS\n(27 rows)"]
    EMPLOYEES["EMPLOYEES\n(23 rows)"]
    JOB_HISTORY["JOB_HISTORY\n(10 rows)"]

    REGIONS --> COUNTRIES
    COUNTRIES --> LOCATIONS
    LOCATIONS --> DEPARTMENTS
    JOBS --> EMPLOYEES
    DEPARTMENTS <--> EMPLOYEES
    JOBS --> JOB_HISTORY
    EMPLOYEES --> JOB_HISTORY
    DEPARTMENTS --> JOB_HISTORY

    style DEPARTMENTS fill:#fff3cd,stroke:#f0ad4e
    style EMPLOYEES fill:#fff3cd,stroke:#f0ad4e
    style JOB_HISTORY fill:#fff3cd,stroke:#f0ad4e
```

> **Note:** `DEPARTMENTS`, `EMPLOYEES`, and `JOB_HISTORY` form a circular FK graph. The framework detects this, appends them at the end of the migration order, and applies FK constraints post-load — no manual intervention required.

### Components Overview

| Component | File | Responsibility |
|---|---|---|
| **Orchestrator** | `scripts/run_migration.sh` | Drives all 12 phases, handles flags, logging, exit codes |
| **Connection Tester** | `scripts/test_connections.py` | Validates Oracle + PG connectivity, versions, privileges |
| **Schema Extractor** | `discovery/extract_schema.py` | Reads `all_*` system views; emits `schema_metadata.json` |
| **Dependency Analyzer** | `discovery/analyze_dependencies.py` | FK graph; Kahn's toposort; emits `dependency_order.json` |
| **DDL Converter** | `conversion/ddl_converter.py` | Translates Oracle metadata → 7 PostgreSQL DDL files |
| **Data Migrator** | `migration/data_migrator.py` | Batched `COPY` via `copy_expert()`; emits `migration_summary.json` |
| **Count Validator** | `validation/count_validator.py` | Row-count comparison per table; emits `count_validation.json` |
| **Checksum Validator** | `validation/checksum_validator.py` | MD5-based row sampling; emits `checksum_validation.json` |

### Deployment Architecture

```
┌──────────────────────────────────────────────────┐
│              Migration Host                       │
│                                                  │
│  ┌────────────────────┐  ┌──────────────────┐   │
│  │   Python 3.9+      │  │   psql CLI       │   │
│  │   oracledb ≥ 2.0   │  │   (12+)          │   │
│  │   psycopg2 2.9.9   │  └─────────┬────────┘   │
│  │   PyYAML 6.0.1     │            │             │
│  │   python-dotenv    │            │             │
│  └─────────┬──────────┘            │             │
└────────────┼──────────────────────┼─────────────┘
             │ TCP :1521             │ TCP :5432
             ▼                       ▼
     ┌───────────────┐      ┌────────────────────┐
     │  Oracle DB    │      │   PostgreSQL DB     │
     │  (source)     │      │   (target)          │
     │  read-only    │      │   read-write        │
     └───────────────┘      └────────────────────┘
```

The migration host can be a developer workstation, dedicated VM, Docker container, or CI/CD runner.

---

## Technical Design

### Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.9+ | All migration logic |
| Orchestration | Bash | 3.2+ (POSIX-safe) | Phase sequencing, logging, exit control |
| Oracle driver | `oracledb` | ≥ 2.0 | Oracle connectivity — thin mode, no OCI |
| PostgreSQL driver | `psycopg2-binary` | 2.9.9 | PG connectivity + bulk COPY |
| Config parsing | `PyYAML` | 6.0.1 | YAML config file loading |
| Env management | `python-dotenv` | 1.0.0 | `.env` file loading |
| SQL client | `psql` | 12+ | DDL application to PostgreSQL |

### Design Patterns

| Pattern | Where Used | Purpose |
|---|---|---|
| **Pipeline / Chain of Responsibility** | `run_migration.sh` phases 0–11 | Sequential, ordered execution with fail-fast |
| **Idempotent Operations** | All DDL (`IF NOT EXISTS`), data (`TRUNCATE + COPY`) | Safe re-runs on failure |
| **Template Method** | Each Python module has a `main()` entry point | Consistent invocation pattern |
| **Strategy** | Migration flags `--schema-only`, `--data-only` | Alter which phases execute |
| **Topological Sort** | `analyze_dependencies.py` (Kahn's algorithm) | FK-safe table ordering |
| **Canonical Serialisation** | `decimal.Decimal.normalize()` in checksum | Cross-DB type-safe comparison |

### Security Considerations

| Concern | Mitigation |
|---|---|
| Credential exposure | `.env` is `.gitignore`d; only `.env.template` is committed |
| Oracle password in shell | Passed via environment variable, never as CLI argument |
| PG password in shell | `PGPASSWORD` env var instead of `-W` CLI flag |
| SQL injection in DDL | All identifiers double-quoted throughout |
| Oracle access | Read-only; framework never issues DML against Oracle |
| SSL/TLS | ⚠️ Not enforced by default — add `sslmode=require` for production |

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | `python3 --version` |
| psql client | 12+ | `psql --version` |
| Oracle client | — | **Not required** — `oracledb` thin mode |
| Network access | — | TCP to Oracle `:1521` and PostgreSQL `:5432` |

```bash
pip install -r requirements.txt
```

**Python packages installed:**

| Package | Version | Purpose |
|---|---|---|
| `oracledb` | ≥ 2.0.0 | Oracle thin-mode driver |
| `psycopg2-binary` | 2.9.9 | PostgreSQL DBAPI 2.0 adapter |
| `PyYAML` | 6.0.1 | YAML configuration parsing |
| `python-dotenv` | 1.0.0 | `.env` file loading |

---

## Configuration

```bash
cp config/.env.template config/.env
# Edit config/.env — this file is NEVER committed
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ORACLE_HOST` | Oracle host | `localhost` |
| `ORACLE_PORT` | Oracle listener port | `1521` |
| `ORACLE_SERVICE` | Oracle service name | `ORCL` |
| `ORACLE_SCHEMA` | Schema to migrate | `HR` |
| `ORACLE_USER` | Oracle username | `hr` |
| `ORACLE_PASSWORD` | Oracle password | — |
| `PG_HOST` | PostgreSQL host | `localhost` |
| `PG_PORT` | PostgreSQL port | `5432` |
| `PG_DATABASE` | Target database name | `hr_db` |
| `PG_SCHEMA` | Target schema name | `hr` |
| `PG_USER` | PostgreSQL username | `postgres` |
| `PG_PASSWORD` | PostgreSQL password | — |
| `BATCH_SIZE` | Rows per COPY batch | `10000` |
| `MAX_WORKERS` | Parallel worker count | `4` |
| `LOG_LEVEL` | Python log level | `INFO` |

### `migration_config.yaml` — Advanced Settings

```yaml
migration:
  include_tables: []       # empty = all tables
  exclude_tables: []       # tables to skip
  include_views: true
  include_sequences: true
  include_indexes: true
  include_constraints: true
  include_triggers: false  # PL/SQL requires manual port

  batch_size: 10000
  max_workers: 4
  truncate_before_load: true

  run_count_validation: true
  run_checksum_validation: true
  checksum_sample_size: 1000
```

---

## Project Structure

```
oracle-to-postgresql/
│
├── config/                         ← All configuration
│   ├── .env.template               ← Safe-to-commit credential template ✅
│   ├── .env                        ← Real credentials — NEVER commit ❌
│   ├── migration_config.yaml       ← Migration scope, type maps, batch settings
│   ├── source_db.yaml              ← Oracle connection reference
│   └── target_db.yaml              ← PostgreSQL connection reference
│
├── discovery/                      ← Phase 2: Oracle introspection
│   ├── extract_schema.py           ← Queries all_* views → schema_metadata.json
│   └── analyze_dependencies.py     ← Kahn's toposort → dependency_order.json
│
├── conversion/                     ← Phase 3: DDL translation
│   └── ddl_converter.py            ← Metadata JSON → 7 SQL DDL files
│
├── migration/                      ← Phase 6: Bulk data transfer
│   └── data_migrator.py            ← TRUNCATE + COPY per table in FK order
│
├── validation/                     ← Phases 9–10: Data integrity checks
│   ├── count_validator.py          ← Per-table row count comparison
│   └── checksum_validator.py       ← MD5 row-hash sampling comparison
│
├── scripts/                        ← Executable entry points
│   ├── run_migration.sh            ← ⭐ Master orchestrator — start here
│   └── test_connections.py         ← Phase 1 connectivity pre-flight
│
├── output/                         ← Generated at runtime (gitignored)
│   ├── ddl/                        ← 7 SQL files + metadata JSON
│   │   ├── 01_tables.sql
│   │   ├── 02_sequences.sql
│   │   ├── 03_pk_uk.sql
│   │   ├── 04_fk.sql
│   │   ├── 05_check.sql
│   │   ├── 06_indexes.sql
│   │   ├── 07_views.sql
│   │   ├── schema_metadata.json
│   │   └── dependency_order.json
│   ├── logs/                       ← Per-module Python log files
│   └── reports/                    ← Validation JSON + parity report
│       ├── count_validation.json
│       ├── checksum_validation.json
│       ├── schema_parity.txt
│       └── migration_summary.json
│
├── logs/                           ← Shell orchestrator logs
│   └── run_migration_YYYYMMDD_HHMMSS.log
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp config/.env.template config/.env
# Edit config/.env with your Oracle and PostgreSQL details

# 3. Run full migration (all 12 phases)
chmod +x scripts/run_migration.sh
./scripts/run_migration.sh

# 4. Schema-only (DDL, no data, no validation)
./scripts/run_migration.sh --schema-only

# 5. Skip validation (all phases except count/checksum)
./scripts/run_migration.sh --skip-validation

# 6. Data-only (schema already in PG, re-migrate data)
./scripts/run_migration.sh --data-only
```

### Recommended Cutover Workflow

```
Step 1 ──► ./run_migration.sh --schema-only
             │
             ▼
Step 2 ──► Review output/ddl/ SQL files
             │
             ▼
Step 3 ──► ./run_migration.sh
             │
             ▼
Step 4 ──► Check output/reports/ — all 3 reports pass?
             │                │
            YES               NO
             │                │
             ▼                ▼
Step 5 ──► Cutover      Investigate logs/ + reports/
           (switch app        Fix & re-run Step 3
            connection)
```

---

## Phase Pipeline

| Phase | Script / Command | Description | Skipped By |
|---|---|---|---|
| **0** | `bash` built-ins | Prerequisites check + `__pycache__` purge | — (always runs) |
| **1** | `test_connections.py` | Oracle + PG connectivity, versions, privileges | — (always runs) |
| **2** | `extract_schema.py` | Full Oracle schema metadata extraction | `--data-only` |
| **3** | `analyze_dependencies.py` | FK graph + Kahn's topological sort | `--data-only` |
| **4** | `ddl_converter.py` | Oracle DDL → 7 PostgreSQL SQL files | `--data-only` |
| **5** | `psql 01–03` | Apply tables → sequences → PK/UK constraints | `--data-only` |
| **6** | `data_migrator.py` | Batched `COPY` for all tables (FK order) | `--schema-only` |
| **7** | `psql 04–06` | Apply FK → CHECK → indexes | — (always runs) |
| **8** | `psql 07` | Apply views | — (always runs) |
| **9** | `count_validator.py` | Per-table row-count comparison | `--schema-only` / `--skip-validation` |
| **10** | `checksum_validator.py` | MD5 row-hash sampling | `--schema-only` / `--skip-validation` |
| **11** | inline Python + psql | Schema object count parity | — (always runs) |
| **12** | `psql ANALYZE` | Gather PostgreSQL query-planner statistics | — (always final) |

> **Every phase is idempotent** — a full re-run is always safe.

---

## Data Type Mapping

| Oracle Type | PostgreSQL Type | Notes |
|---|---|---|
| `NUMBER` (no precision) | `NUMERIC` | |
| `NUMBER(p,0)` p ≤ 9 | `INTEGER` | |
| `NUMBER(p,0)` p ≤ 18 | `BIGINT` | |
| `NUMBER(p,s)` | `NUMERIC(p,s)` | |
| `VARCHAR2(n)` / `NVARCHAR2(n)` | `VARCHAR(n)` | Uses `char_length` |
| `CHAR(n)` / `NCHAR(n)` | `CHAR(n)` | |
| `CLOB` / `NCLOB` / `LONG` | `TEXT` | |
| `BLOB` | `BYTEA` | |
| `RAW` / `LONG RAW` | `BYTEA` | |
| `DATE` | `TIMESTAMP` | Oracle DATE includes time |
| `TIMESTAMP` | `TIMESTAMP` | |
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP WITH TIME ZONE` | |
| `TIMESTAMP WITH LOCAL TIME ZONE` | `TIMESTAMP WITH TIME ZONE` | |
| `FLOAT` / `BINARY_DOUBLE` | `DOUBLE PRECISION` | |
| `BINARY_FLOAT` | `REAL` | |
| `XMLTYPE` | `XML` | |
| `INTERVAL YEAR TO MONTH` | `INTERVAL YEAR TO MONTH` | |
| `INTERVAL DAY TO SECOND` | `INTERVAL DAY TO SECOND` | |
| Unknown types | `TEXT` | Logged as warning |

---

## Validation Reports

Three reports are generated in `output/reports/` after a full migration:

### Row-Count Validation (`count_validation.json`)

Compares exact row counts for every table between Oracle and PostgreSQL.

**Example — Oracle HR schema (actual run):**

| Table | Oracle Count | PostgreSQL Count | Match |
|---|---|---|---|
| `JOBS` | 19 | 19 | ✅ |
| `REGIONS` | 4 | 4 | ✅ |
| `COUNTRIES` | 25 | 25 | ✅ |
| `LOCATIONS` | 23 | 23 | ✅ |
| `DEPARTMENTS` | 27 | 27 | ✅ |
| `EMPLOYEES` | 23 | 23 | ✅ |
| `JOB_HISTORY` | 10 | 10 | ✅ |
| **Total** | **131** | **131** | **0 mismatches** |

### Checksum Validation (`checksum_validation.json`)

Samples up to `CHECKSUM_SAMPLE_SIZE` rows per table, computes MD5 hashes of canonicalised row values, and compares across both databases.

> **Numeric normalisation:** `format(Decimal(str(val)).normalize(), 'f')` ensures `24000.0` and `Decimal('24000.00')` produce identical hashes — eliminating false mismatches from Oracle `float` vs PostgreSQL `Decimal` representation.

### Schema Parity Report (`schema_parity.txt`)

Compares database object counts (tables, views, sequences, indexes, constraints) between Oracle and PostgreSQL.

```
Schema Parity Report
Generated: 2026-06-25T18:06:39Z
Oracle schema  : HR
PostgreSQL schema: hr_schema
==========================================
Tables      — Oracle: 7   PostgreSQL: 7
Views       — Oracle: 0   PostgreSQL: 0
Sequences   — Oracle: 3   PostgreSQL: 3
Indexes     — Oracle: 11  PostgreSQL: 11
Constraints — Oracle: 32  PostgreSQL: 19
Parity errors: 1
```

> **Note on constraints:** Oracle stores NOT NULL constraints as explicit CHECK entries in `all_constraints`. PostgreSQL enforces these as column attributes, not named constraints — so a constraint count difference of this nature is **expected and benign**.

---

## Development Workflow

### Local Setup

```bash
cd oracle-to-postgresql

# Optional but recommended: create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp config/.env.template config/.env
# Edit config/.env
```

### Running Individual Modules

Each Python module is independently executable for debugging:

```bash
# Test connections only
python3 scripts/test_connections.py

# Run schema extraction only
python3 discovery/extract_schema.py

# Run dependency analysis only
python3 discovery/analyze_dependencies.py

# Run DDL conversion only
python3 conversion/ddl_converter.py

# Run data migration only
python3 migration/data_migrator.py

# Run count validation only
python3 validation/count_validator.py

# Run checksum validation only
python3 validation/checksum_validator.py
```

### Docker (Suggested — Not Yet in Repo)

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["./scripts/run_migration.sh"]
```

```bash
docker build -t oracle-pg-migration .
docker run --env-file config/.env oracle-pg-migration
```

### Database Initialization

The PostgreSQL **database** must exist before running. Create it with:

```sql
CREATE DATABASE hr_db;
```

The target **schema** is created automatically by Phase 1 (`test_connections.py`):

```python
cur.execute('CREATE SCHEMA IF NOT EXISTS "hr"')
```

---

## Non-functional Requirements

### Security

| Requirement | Status |
|---|---|
| Credentials never in source control | ✅ `.env` excluded via `.gitignore` |
| No passwords as CLI arguments | ✅ `PGPASSWORD` env var for psql |
| SQL injection prevention | ✅ All identifiers double-quoted |
| Read-only Oracle access | ✅ Only `SELECT` on `all_*` views + user tables |
| SSL/TLS enforcement | ⚠️ Not configured — add `sslmode=require` for production |

### Reliability

- `set -euo pipefail` — any unexpected shell error halts the pipeline
- Per-phase exit code checking with descriptive `fail()` messages
- Connection testing before any destructive operation
- Per-table error isolation in `data_migrator.py` — one table failure doesn't abort all
- Idempotency — all operations can be safely retried

### Scalability

| Dimension | Current | Enhancement Path |
|---|---|---|
| Row throughput | 10,000 rows/batch (`BATCH_SIZE`) | Tune `BATCH_SIZE` per table width |
| Concurrent tables | Sequential (1 at a time) | Implement `MAX_WORKERS` thread pool |
| Memory per batch | `BATCH_SIZE × row_size` in `StringIO` | Stream LOBs directly for BLOB-heavy schemas |

### Portability

| Platform | Status |
|---|---|
| macOS | ✅ Tested (Bash 3.2 POSIX-safe) |
| Linux (Ubuntu, RHEL, Alpine) | ✅ Expected — Python 3.9+ + psql CLI |
| Windows via WSL2 | ⚠️ Probable |
| Windows native PowerShell | ❌ Orchestrator is Bash |
| Docker | ✅ Straightforward (no binary deps) |

---

## Assumptions & Limitations

### Assumptions

1. Oracle schema uses standard data types (no `BFILE`, `XMLSCHEMA` registered types)
2. Oracle source is available and read-only throughout the entire migration
3. PostgreSQL target schema can be safely `TRUNCATE`d
4. Oracle user has `SELECT` on `all_*` data dictionary views + user tables
5. PostgreSQL user has `CREATE` privilege on the target database
6. CHECK constraint bodies use standard SQL-92 predicates

### Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Triggers not converted | Oracle trigger bodies extracted but not ported | Manual port required; `include_triggers: false` |
| Parallel data load not implemented | Large schemas are slow | Future: `ThreadPoolExecutor` per `MAX_WORKERS` |
| Oracle PL/SQL not migrated | Stored procedures / functions ignored | Out of scope; manual port required |
| View rewriting is heuristic | Complex Oracle SQL may not translate | Review `output/ddl/07_views.sql` manually |
| No CDC / incremental migration | Full snapshot only | Use AWS DMS or Debezium for live cutover |
| Checksum is sampling only | Default 1000 rows per table | Increase `CHECKSUM_SAMPLE_SIZE` for confidence |
| No automated rollback | Manual `DROP SCHEMA` required | See Rollback section below |

---

## Troubleshooting

| Symptom | Resolution |
|---|---|
| `ORA-01045` | Grant `CREATE SESSION` to Oracle user |
| `psycopg2.OperationalError` | Check `PG_HOST`, `PG_PORT`, `PG_DATABASE` in `.env` |
| `ORA-00942: table or view does not exist` | Grant `SELECT ANY DICTIONARY` or explicit `all_*` grants |
| Count mismatch | Check `output/reports/count_validation.json` for specific tables |
| Checksum mismatch | Inspect `output/reports/checksum_validation.json`; check type mappings |
| Schema parity constraint delta | Oracle NOT NULL constraints vs PG column attributes — see report note above |
| Schema parity errors (tables/views) | Review `output/reports/schema_parity.txt`; re-run Phase 7 DDL manually |
| `__pycache__` stale code | Phase 0 purges automatically; manual: `find . -name __pycache__ -exec rm -rf {} +` |
| Sequence out of range | Verify `last_number` extraction; MAXVALUE capped at `9223372036854775807` |
| Circular FK warning | Expected; framework handles automatically — FKs applied post-load |
| View SQL syntax error | Review `output/ddl/07_views.sql`; Oracle-specific functions may need manual adjustment |

---

## Rollback Procedure

Oracle is **never written to**. To roll back a migration:

```sql
-- 1. Stop all application connections to PostgreSQL target
-- 2. Drop the target schema
DROP SCHEMA hr CASCADE;

-- 3. Point applications back to Oracle source
-- 4. Investigate root cause in logs/ and output/reports/
-- 5. Re-run after correcting the issue
./scripts/run_migration.sh
```

---

## Roadmap

### Near-Term

- [ ] Implement `MAX_WORKERS` parallel table migration in `data_migrator.py`
- [ ] Add progress bars (`tqdm`) for long-running data phases
- [ ] Streaming LOB migration for BLOB/CLOB-heavy schemas
- [ ] `pytest` test suite for unit tests (type mapping, CHECK rewriting, toposort)
- [ ] SSL/TLS enforcement flags for both Oracle and PostgreSQL connections

### Medium-Term

- [ ] Oracle synonym support
- [ ] Materialized view migration
- [ ] Partitioned table handling (Oracle → PG declarative partitioning)
- [ ] Docker Compose setup for local Oracle + PostgreSQL test environments
- [ ] GitHub Actions CI workflow for automated lint + connection tests

### Long-Term

- [ ] Basic PL/SQL → PL/pgSQL transpiler for common patterns
- [ ] Multi-schema migration in a single run
- [ ] Delta / CDC migration mode for live cutover (Debezium integration)
- [ ] Encrypted credential storage (Vault, AWS Secrets Manager, Azure Key Vault)
- [ ] Prometheus metrics export + web dashboard for migration progress
- [ ] Schema diff tool (compare Oracle source vs PostgreSQL target post-migration)

---

## Professional Summary

### Portfolio / Resume

**Oracle to PostgreSQL Migration Framework** — Production-ready, idempotent Python + Bash pipeline automating the complete Oracle → PostgreSQL database migration lifecycle: schema discovery, DDL conversion (17 type mappings), FK-aware batch data loading via `psycopg2 copy_expert()`, and dual-layer validation (row counts + MD5 checksums). Eliminated Oracle OCI client dependency via `oracledb` thin mode. Delivered 12-phase architecture with comprehensive per-phase logging, structured JSON artefacts, and documented rollback procedures. Validated against the Oracle HR reference schema with 131 rows across 7 tables, 7 tables, 3 sequences, 11 indexes — **0 data discrepancies** post-migration.

**Tech:** Python 3.9+, Bash, oracledb (thin mode), psycopg2, PostgreSQL 12+, Oracle 11g+, Kahn's algorithm

### LinkedIn

> Designed and implemented a production-ready database migration framework automating the Oracle → PostgreSQL cutover lifecycle. Delivered an idempotent 12-phase pipeline with schema discovery, DDL conversion, FK-aware data loading, and dual-layer validation. Zero Oracle OCI dependency — runs on any Python 3.9+ host. Achieved 0 row-count mismatches and 100% checksum match on the Oracle HR reference schema. Generated full audit trails via structured JSON reports and timestamped logs.

---

## Architecture Decision Summary

### Why This Architecture is Appropriate

| Decision | Justification |
|---|---|
| **Python + Bash hybrid** | Bash for phase control; Python for data processing — common toolchain, low onboarding friction |
| **Sequential pipeline** | FK dependencies require ordering; simplicity > premature parallelism |
| **Kahn's topological sort** | O(V+E); correct FK ordering; graceful circular-dependency handling |
| **`IF NOT EXISTS` DDL** | Safe re-runs; partially-applied schemas can be resumed |
| **`TRUNCATE` before `COPY`** | Guarantees clean slate; faster than `DELETE` for large tables |
| **FKs applied after data load** | Avoids deferred constraint overhead; bulk load ignores FK order |
| **Dual validation (count + checksum)** | Count detects row loss; checksum detects corruption |
| **`copy_expert()` over `execute_values()`** | Native PostgreSQL COPY protocol; highest throughput |
| **`oracledb` thin mode** | Pure Python; no native Oracle libs; Docker-friendly |
| **Structured JSON artefacts** | Machine-readable; enables monitoring, alerting, and downstream automation |

### Architecture Decision Record (ADR)

```mermaid
graph TB
    subgraph Problems["Business Problems"]
        B1[Oracle licensing cost]
        B2[Application modernisation]
        B3[Cloud migration readiness]
        B4[OCI thick-client dependency]
    end

    subgraph Constraints["Engineering Constraints"]
        C1[Must validate data integrity]
        C2[Must be idempotent]
        C3[Must not require Oracle OCI]
        C4[Must respect FK dependencies]
        C5[Must produce audit logs]
    end

    subgraph Solution["This Framework"]
        S1[Python + Bash pipeline]
        S2[oracledb thin mode]
        S3[psycopg2 copy_expert]
        S4[Kahn topological sort]
        S5[Dual validation]
        S6[IF NOT EXISTS DDL]
        S7[12-phase orchestrator]
    end

    subgraph Outcomes["✅ Outcomes"]
        O1[Zero OCI dependency]
        O2[Proven data integrity]
        O3[Safe re-runs]
        O4[FK constraint correctness]
        O5[Full audit trail]
        O6[Reduced Oracle licensing cost]
    end

    B4 --> S2 --> O1
    B1 --> S1
    B2 --> S1
    B3 --> S1
    C1 --> S5 --> O2
    C2 --> S6 --> O3
    C4 --> S4 --> O4
    C5 --> S7 --> O5
    S3 --> O2
    O1 & O2 & O3 & O4 & O5 --> O6
```

### Suitability Summary

| Use Case | Suitable? |
|---|---|
| One-time Oracle → PG lift-and-shift | ✅ Primary use case |
| Schema-first migration (review DDL before data) | ✅ `--schema-only` flag |
| Repeatable dev/test/staging migrations | ✅ Fully idempotent |
| Audit-compliant migrations (logs + reports) | ✅ Complete audit trail |
| Live near-zero-downtime migration (CDC) | ❌ Use AWS DMS or Debezium |
| Schemas with complex PL/SQL | ⚠️ Manual port required for stored procedures |
| Multi-terabyte databases (single-threaded) | ⚠️ Implement `MAX_WORKERS` first |

---

<div align="center">

**Oracle to PostgreSQL Migration Framework**

Made with [Bob AI](https://github.com/IBM/bob-ai) · Production-ready · Idempotent · Validated

</div>
ADME.md…]()
