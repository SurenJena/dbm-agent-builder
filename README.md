[Architecture.md](https://github.com/user-attachments/files/29581865/Architecture.md)
Oracle → PostgreSQL Migration Framework — Supplementary Documentation
Scope: This document complements the existing README.md without repeating it. All sections here are additive. Cross-references to README sections are noted where relevant.

1. Executive Summary
Project Purpose
The Oracle to PostgreSQL Migration Framework is a Python-based, production-ready pipeline that automates the complete migration of an Oracle database schema — DDL, data, constraints, indexes, sequences, and views — into a target PostgreSQL database with full structural and data-integrity validation.

Problem It Solves
Migrating from Oracle to PostgreSQL is routinely one of the most expensive and risky database modernisation efforts an engineering team faces. The primary challenges are:

Pain Point	How This Framework Addresses It
Incompatible SQL dialects	Automated type mapping + DDL rewriting (17 Oracle → PG type rules)
FK ordering deadlocks	Kahn's topological sort computes a safe load order
Non-idempotent runs	Every phase uses IF NOT EXISTS / TRUNCATE + reload guards
Silent data corruption	Dual-layer validation: row-count + MD5 checksum comparison
Oracle OCI dependency	Uses oracledb thin mode — no Oracle Client installation required
Tribal knowledge lost in cutover	Structured JSON metadata + per-phase timestamped logs
Target Users
Database Administrators performing Oracle → PostgreSQL lift-and-shift migrations
Backend Engineers modernising legacy Oracle-dependent applications
DevOps / Platform Engineers embedding database migration into CI/CD pipelines
Cloud Architects migrating on-premise Oracle workloads to AWS RDS PostgreSQL, Azure Database for PostgreSQL, or Google Cloud SQL
Business Value
Risk reduction: two independent validation stages catch data discrepancies before cutover
Repeatability: fully idempotent — re-run any phase at any time without side effects
Speed: batched COPY via copy_expert() is orders of magnitude faster than row-by-row INSERT
Cost reduction: eliminates Oracle licensing for new workloads
Zero Oracle OCI dependency: runs anywhere Python 3.9+ runs
2. Project Objectives
Primary Objectives
Automate extraction of complete Oracle schema metadata (tables, columns, constraints, indexes, sequences, views, triggers)
Convert all supported Oracle DDL constructs to valid PostgreSQL DDL with no manual editing for standard schemas
Migrate all rows faithfully using high-throughput batched COPY operations
Validate migrated data with both row-count and MD5-checksum comparison against the Oracle source
Produce structured, auditable output artefacts for every phase
Secondary Objectives
Support partial migration modes (--schema-only, --data-only, --skip-validation) to support incremental cutover workflows
Provide human-readable logs and machine-readable JSON reports suitable for downstream automation
Operate without Oracle OCI/thick client libraries via oracledb thin mode
Respect FK dependency order using graph-based topological sort to prevent constraint violations
Handle circular FK dependencies gracefully without aborting the migration
Success Criteria
Criterion	Measurable Target
Schema parity	0 discrepancies in schema_parity.txt after Phase 10
Row count accuracy	0 mismatches in count_validation.json after Phase 8
Checksum accuracy	100% match rate in checksum_validation.json after Phase 9
Idempotency	A second full run produces identical schema and data
Migration completion	All 12 phases exit with code 0
Expected Outcomes
A fully migrated PostgreSQL schema with all tables, constraints, indexes, sequences, and views
Three validation reports (count_validation.json, checksum_validation.json, schema_parity.txt) certifying data integrity
Per-phase Python logs and a timestamped shell orchestrator log for full audit trail
Generated SQL files in output/ddl/ for manual inspection or replay
3. System Architecture
High-Level Architecture
The framework follows a linear sequential pipeline pattern. Each phase is self-contained, writes outputs consumed by later phases, and is guarded for idempotency. The orchestration is driven by a single Bash script (run_migration.sh) that invokes Python modules.

PostgreSQL Target

output/ Artefacts

run_migration.sh — 12-Phase Pipeline

Oracle Source

oracledb thin

psycopg2 copy_expert

Oracle DB
all_tables
all_columns
all_constraints
...

Phase 0
Prerequisites +
__pycache__ purge

Phase 1
Connection Tests
test_connections.py

Phase 2
Schema Discovery
extract_schema.py

Phase 3
Dependency Analysis
analyze_dependencies.py

Phase 4 — DDL Conversion
ddl_converter.py

Phase 5 — Apply Schema
psql: 01-03 SQL files

Phase 6 — Data Migration
data_migrator.py

Phase 7 — Post-data DDL
psql: 04-06 SQL files

Phase 8
View Creation
psql: 07_views.sql

Phase 9
Count Validation
count_validator.py

Phase 10
Checksum Validation
checksum_validator.py

Phase 11
Schema Parity
inline Python + psql

Phase 12
ANALYZE
psql ANALYZE

schema_metadata.json
dependency_order.json

01_tables.sql
02_sequences.sql
03_pk_uk.sql
04_fk.sql
05_check.sql
06_indexes.sql
07_views.sql

count_validation.json
checksum_validation.json
schema_parity.txt
migration_summary.json

PostgreSQL DB
schema + data
+ indexes + views



Components
Component	File	Responsibility
Orchestrator	scripts/run_migration.sh	Drives all 12 phases, handles flags, logging, exit codes
Connection Tester	scripts/test_connections.py	Validates Oracle + PG connectivity, versions, privileges
Schema Extractor	discovery/extract_schema.py	Reads all_* system views; emits schema_metadata.json
Dependency Analyzer	discovery/analyze_dependencies.py	Builds FK graph; Kahn's toposort; emits dependency_order.json
DDL Converter	conversion/ddl_converter.py	Translates Oracle metadata → 7 PostgreSQL DDL files
Data Migrator	migration/data_migrator.py	Batched COPY via copy_expert(); emits migration_summary.json
Count Validator	validation/count_validator.py	Row-count comparison per table; emits count_validation.json
Checksum Validator	validation/checksum_validator.py	MD5-based row sampling; emits checksum_validation.json
Data Flow
output/ (filesystem)
PostgreSQL DB
Oracle DB
data_migrator.py
ddl_converter.py
analyze_dependencies.py
extract_schema.py
run_migration.sh
output/ (filesystem)
PostgreSQL DB
Oracle DB
data_migrator.py
ddl_converter.py
analyze_dependencies.py
extract_schema.py
run_migration.sh
python3 extract_schema.py
SELECT from all_tables, all_tab_columns, all_constraints...
schema metadata
schema_metadata.json
python3 analyze_dependencies.py
reads schema_metadata.json
dependency_order.json (topological order)
python3 ddl_converter.py
reads schema_metadata.json + dependency_order.json
01_tables.sql ... 07_views.sql
psql -f 01_tables.sql (CREATE TABLE IF NOT EXISTS)
psql -f 02_sequences.sql
psql -f 03_pk_uk.sql
python3 data_migrator.py
SELECT per table (batched fetchmany)
TRUNCATE + COPY FROM STDIN (copy_expert)
psql -f 04_fk.sql (ADD CONSTRAINT FK)
psql -f 05_check.sql
psql -f 06_indexes.sql
psql -f 07_views.sql


Database Interactions
Database	Driver	Access Pattern
Oracle	oracledb ≥ 2.0 (thin mode)	Read-only (SELECT from all_* system views + user tables)
PostgreSQL	psycopg2-binary 2.9.9	Read/write: DDL application + bulk COPY + validation queries
Important: Oracle is never written to. The framework is entirely non-destructive on the source.

External Integrations
Oracle Database (any version compatible with oracledb thin protocol) — source only
PostgreSQL 12+ — target; must be reachable via TCP
psql CLI — used for DDL application and inline schema parity queries
Deployment Architecture
Network

Migration Host

TCP (thin mode)

TCP

TCP

run_migration.sh

Python 3.9+
oracledb
psycopg2
PyYAML
python-dotenv

psql CLI

Oracle
:1521

PostgreSQL
:5432



The migration host can be:

A developer workstation
A dedicated migration VM/container
A CI/CD runner (GitHub Actions, GitLab CI, Jenkins)
Design Decisions
Decision	Rationale
Shell orchestrator wrapping Python modules	Each module is independently testable; Bash provides simple, portable phase control without a heavy workflow engine
oracledb thin mode	Removes Oracle Instant Client OCI dependency — runs on any host with Python
copy_expert() over copy_from()	Full control over COPY SQL; prevents injection; allows explicit NULL sentinel and format
Topological sort before data load	Prevents FK constraint violations during data insertion
FKs applied after data load	Data can be loaded in any order if FKs are absent; avoids DEFERRED constraint complexity
TRUNCATE before every load	Guarantees idempotent re-runs without duplicate rows
IF NOT EXISTS on all DDL	Schema application is safe to re-run — partially-applied schemas can be resumed
decimal.Decimal.normalize() in checksum	Eliminates false mismatches caused by Oracle float vs PostgreSQL Decimal representation
4. Technical Design
Technology Stack
Layer	Technology	Version	Purpose
Language	Python	3.9+	All migration logic
Orchestration	Bash	3.2+ (POSIX-safe)	Phase sequencing, logging, exit control
Oracle driver	oracledb	≥ 2.0	Oracle connectivity (thin mode)
PostgreSQL driver	psycopg2-binary	2.9.9	PG connectivity + bulk COPY
Config parsing	PyYAML	6.0.1	YAML config file loading
Env management	python-dotenv	1.0.0	.env file loading
SQL client	psql	12+	DDL application
Frameworks & Libraries
No web frameworks or heavyweight ORMs are used. The design is intentionally minimal:

oracledb       → Oracle thin-mode client
psycopg2       → PostgreSQL DBAPI 2.0 adapter
python-dotenv  → twelve-factor config
PyYAML         → migration_config.yaml parsing
stdlib: json, logging, pathlib, decimal, hashlib, collections, io

Design Patterns
Pattern	Where Used	Purpose
Pipeline / Chain of Responsibility	run_migration.sh phases 0–11	Sequential, ordered execution with fail-fast semantics
Idempotent Operations	All DDL (IF NOT EXISTS), data (TRUNCATE + COPY)	Safe re-runs on failure
Template Method	Each Python module has a main() entry point	Consistent invocation pattern
Strategy (partial)	Migration flags --schema-only, --data-only	Alter which phases execute
Topological Sort	analyze_dependencies.py (Kahn's algorithm)	FK-safe table ordering
Canonical Serialisation	decimal.Decimal.normalize() in checksum	Cross-DB type-safe comparison
Security Considerations
Concern	Mitigation
Credential exposure	.env file is .gitignored; only .env.template is committed
Oracle password in shell	Passed via environment variable, never as CLI argument
PG password in shell	Uses PGPASSWORD env var instead of -W CLI flag
SQL injection in DDL	Object names are double-quoted throughout; no user-supplied string interpolation in runtime queries
Oracle access	Read-only; framework never issues DML against Oracle
Network transport	Relies on TLS/SSL configuration of the target databases — Needs Confirmation if encryption in transit is a requirement
⚠️ Needs Confirmation: The framework does not currently enforce SSL/TLS on either database connection. For production cutover, sslmode=require should be added to the PostgreSQL DSN and equivalent TLS options to the Oracle connection.

Scalability Considerations
Dimension	Current Capability	Limitation
Row throughput	BATCH_SIZE=10000 rows per COPY call	Single-threaded per table; MAX_WORKERS=4 is defined in config but not yet applied in the migrator
Table count	Unlimited (iterates full dependency_order.json)	Large schemas (1000+ tables) will be slow due to sequential execution
Column count	Unlimited	copy_expert() handles wide rows well
BLOB / CLOB	BYTEA / TEXT mapping handled	Very large LOBs may cause memory pressure in the StringIO buffer
⚠️ Needs Confirmation: The MAX_WORKERS=4 configuration variable exists in .env.template and migration_config.yaml but parallel execution is not yet implemented in data_migrator.py. This is a future enhancement opportunity.

Performance Considerations
copy_expert() bulk COPY is the highest-throughput Python→PostgreSQL data load method, avoiding per-row round trips
arraysize = BATCH_SIZE on the Oracle cursor pre-fetches rows server-side to reduce network round trips
StringIO buffering assembles each batch in memory before flushing, reducing copy_expert() call overhead
ANALYZE in Phase 11 is always the final step, ensuring the PostgreSQL query planner has accurate statistics before the application goes live
FKs applied after data load avoids constraint validation overhead during the bulk insert
5. Repository Overview
Repository Description (≤ 350 characters)
Production-ready Python framework for migrating Oracle schemas to PostgreSQL. Automates DDL conversion, FK-aware batch data loading, and dual-layer validation (row counts + MD5 checksums) in a 12-phase idempotent pipeline. No Oracle OCI client required.

Project Tagline
From Oracle to PostgreSQL — automated, validated, repeatable.

Key Highlights
🔄 12-phase idempotent pipeline — restart any phase safely
🔍 Zero-OCI requirement — uses oracledb thin mode
📊 Dual validation — row counts + MD5 checksum sampling
🔗 FK-aware ordering — Kahn's algorithm prevents constraint errors
📝 Full audit trail — timestamped logs + structured JSON reports
⚙️ Flexible modes — --schema-only, --data-only, --skip-validation
🛡️ Non-destructive — Oracle source is never modified
Project Maturity
Beta / Production-Candidate — The framework has a complete, well-structured implementation with comprehensive validation. It has been executed against the Oracle HR reference schema (evidenced by the committed output artefacts). It is suitable for production use on well-understood schemas; complex PL/SQL bodies, Oracle-specific stored procedures, and parallel execution are not yet supported.

Intended Audience
Database administrators, backend engineers, and platform engineers who need to migrate Oracle schemas to PostgreSQL without commercial migration tools.

6. Features Summary
Core Features
Complete Oracle schema metadata extraction (tables, columns, constraints, indexes, sequences, views, triggers)
Oracle → PostgreSQL data type mapping for all common Oracle types (17 mappings)
FK-aware topological sort for safe table migration order
Idempotent DDL generation using CREATE ... IF NOT EXISTS and DO $$ IF NOT EXISTS guards
Batch data migration using psycopg2.copy_expert() for maximum throughput
CHECK constraint rewriting: Oracle IS NOT NULL constraints are filtered; column names are uppercased and double-quoted
Oracle built-in function rewriting in views (SYSDATE → CURRENT_TIMESTAMP, NVL → COALESCE, FROM DUAL removal, etc.)
Sequence migration with MAXVALUE capped at PostgreSQL BIGINT maximum
Administrative Features
Pre-flight connection tests with privilege checks (Phase 1)
Per-phase structured logging to both console and per-module log files
Timestamped orchestrator log file (logs/run_migration_YYYYMMDD_HHMMSS.log)
Schema parity report comparing object counts between Oracle and PostgreSQL (Phase 10)
Final ANALYZE to refresh PostgreSQL statistics (Phase 11)
Manual rollback procedure documented in README Section 8
Developer Features
Environment-based configuration via .env file (no hardcoded credentials)
migration_config.yaml for fine-grained migration scope control (include/exclude tables, batch size, worker count, validation flags)
All Python modules are independently executable (python3 <module>.py)
Structured JSON artefacts (schema_metadata.json, dependency_order.json) for debugging and integration
__pycache__ purge in Phase 0 prevents stale bytecode issues
Circular FK dependency detection with graceful handling
Deployment Features
No Docker required — pure Python + psql CLI
macOS bash 3.2 compatibility (POSIX-safe tr instead of ${var^^})
set -euo pipefail for strict shell error propagation
Flags: --schema-only, --data-only, --skip-validation for flexible cutover workflows
All output directories auto-created at runtime
Database Features
Oracle source: read-only access via all_* data dictionary views
PostgreSQL target: schema auto-created if not present (Phase 1)
FK constraints dropped before data load, re-applied after (handles circular FK schemas)
Disabled Oracle constraints are skipped in DDL generation
Oracle NOT NULL CHECK constraints filtered (enforced via column NOT NULL instead)
TIMESTAMP WITH LOCAL TIME ZONE → TIMESTAMP WITH TIME ZONE conversion
7. Project Structure Explanation
oracle-to-postgresql/
│
├── config/                     ← All configuration lives here
│   ├── .env.template           ← Safe-to-commit credential template
│   ├── .env                    ← NEVER committed — real credentials
│   ├── migration_config.yaml   ← Migration scope, batch size, type maps
│   ├── source_db.yaml          ← Oracle connection reference (documentation)
│   └── target_db.yaml          ← PostgreSQL connection reference (documentation)
│
├── discovery/                  ← Phase 2: Oracle introspection
│   ├── extract_schema.py       ← Queries all_* views; writes schema_metadata.json
│   └── analyze_dependencies.py ← Kahn's toposort; writes dependency_order.json
│
├── conversion/                 ← Phase 3: DDL translation
│   └── ddl_converter.py        ← Reads metadata JSON; writes 7 SQL DDL files
│
├── migration/                  ← Phase 5 (data): bulk data transfer
│   └── data_migrator.py        ← TRUNCATE + COPY per table in FK order
│
├── validation/                 ← Phases 8–9: data integrity checks
│   ├── count_validator.py      ← Per-table row count comparison
│   └── checksum_validator.py   ← MD5 row-hash sampling comparison
│
├── scripts/                    ← Executable entry points
│   ├── run_migration.sh        ← Master orchestrator — start here
│   └── test_connections.py     ← Phase 1 connectivity pre-flight
│
├── output/                     ← GENERATED at runtime (gitignored except .gitkeep)
│   ├── ddl/                    ← 7 SQL files + metadata JSON
│   ├── logs/                   ← Per-module Python log files
│   └── reports/                ← Validation JSON + parity text report
│
├── logs/                       ← Shell orchestrator timestamped logs
├── requirements.txt            ← Python dependencies (4 packages)
├── .gitignore                  ← Excludes .env, __pycache__, output data
└── README.md                   ← Quick-start, configuration, phase reference


Directory	Content Type	Runtime-generated?
config/	Configuration files	Partially (.env is user-created)
discovery/	Python source	No
conversion/	Python source	No
migration/	Python source	No
validation/	Python source	No
scripts/	Shell + Python entry points	No
output/ddl/	Generated SQL + JSON artefacts	Yes
output/reports/	Validation JSON reports	Yes
output/logs/	Module-level log files	Yes
logs/	Orchestrator log files	Yes
8. Development Workflow
Build Process
There is no compiled build step. The framework is interpreted Python + Bash.

# One-time setup
cd oracle-to-postgresql
python3 -m venv .venv          # optional but recommended
source .venv/bin/activate
pip install -r requirements.txt

Running Locally
# 1. Copy and populate credentials
cp config/.env.template config/.env
# Edit config/.env with your Oracle and PostgreSQL connection details

# 2. Verify connections only (no migration)
python3 scripts/test_connections.py

# 3. Full migration
chmod +x scripts/run_migration.sh
./scripts/run_migration.sh

# 4. Schema only (inspect DDL before committing to data migration)
./scripts/run_migration.sh --schema-only

# 5. Re-run data migration only (schema already applied)
./scripts/run_migration.sh --data-only

# 6. Full migration without checksum/count validation (faster for large schemas)
./scripts/run_migration.sh --skip-validation

Docker Workflow
Needs Confirmation: No Dockerfile or docker-compose.yml exists in the repository. For containerised execution, a minimal image would look like:

# Suggested — not committed to repository
FROM python:3.11-slim
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["./scripts/run_migration.sh"]

Database Initialization
No initialisation scripts are required. Phase 1 (test_connections.py) automatically creates the target PostgreSQL schema if it does not exist:

# test_connections.py line 130
cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

The PostgreSQL database itself must exist prior to running the migration. Create it with:

CREATE DATABASE hr_db;

Testing Workflow
Needs Confirmation: No automated test suite (tests/ directory, pytest, unittest) exists in the repository. The validation phases (8–10) serve as integration tests. Recommended additions:

# Current "test" — run connection pre-flight
python3 scripts/test_connections.py

# Manual module test — run individual phases against a test schema
ORACLE_SCHEMA=HR_TEST python3 discovery/extract_schema.py
ORACLE_SCHEMA=HR_TEST python3 discovery/analyze_dependencies.py
ORACLE_SCHEMA=HR_TEST python3 conversion/ddl_converter.py

Deployment Workflow
Recommended cutover procedure:

Yes

No

1. Schema-only
./run_migration.sh
--schema-only

2. Inspect DDL
output/ddl/
Review SQL files

3. Full migration
./run_migration.sh

4. Review reports
output/reports/
All 3 reports pass?

5. Cutover
Switch app
connection string

6. Investigate
logs/ + reports/
Fix & re-run



9. Non-functional Requirements
Security
Requirement	Implementation	Gap
No credentials in source control	.env excluded via .gitignore	.env.template has default weak passwords — warn users
No plaintext passwords in process args	Oracle: DSN-based; PG: PGPASSWORD env var	PGPASSWORD is visible in /proc on Linux — consider .pgpass
Read-only Oracle access	Only SELECT against all_* views	Requires Oracle user to have SELECT ANY DICTIONARY or explicit grants
DDL injection prevention	All identifiers double-quoted	✅ Covered
Reliability
set -euo pipefail in the orchestrator — any unexpected error halts the pipeline
Per-phase exit code checking with fail() function
Connection testing before any destructive operation
Per-table error isolation in data_migrator.py — one table failure doesn't abort all tables
Idempotency — all operations can be safely retried
Maintainability
Single-responsibility modules — each Python file does exactly one thing
Consistent logging pattern across all modules (logging.basicConfig + file handler + stream handler)
All configuration in one place (config/)
Generated artefacts clearly separated from source code (output/)
Inline comments explaining non-obvious logic (e.g., decimal.Decimal.normalize() rationale)
Scalability
Dimension	Limit	Recommended Enhancement
Concurrent table migration	1 (sequential)	Implement MAX_WORKERS parallelism in data_migrator.py
Memory per batch	BATCH_SIZE × row_size	Tune BATCH_SIZE down for very wide tables
Very large LOBs	StringIO may hold large values	Stream LOBs directly for BLOB-heavy schemas
Availability
The framework does not expose any service endpoints. It is a batch job. Availability is defined as:

Oracle source remains available (read-only) for the duration of discovery + data load
PostgreSQL target remains available (read-write) for the duration of schema application + data load
No planned downtime on the Oracle source is required
No planned downtime on the PostgreSQL target is required unless cutover is immediate
Portability
Platform	Status	Notes
macOS	✅ Tested	Bash 3.2 POSIX-safe; no GNU-isms
Linux (Ubuntu, RHEL, Alpine)	✅ Expected	Python 3.9+ + psql CLI
Windows (WSL2)	⚠️ Probable	Bash available via WSL
Windows (native PowerShell)	❌ Not supported	Orchestrator is Bash; would require rewrite
Docker	✅ Straightforward	No Docker artefacts in repo, but trivial to containerise
10. Assumptions and Limitations
Assumptions
Oracle schema uses standard data types (no BFILE, no XMLSCHEMA registered types)
All tables have a unique or primary key for FK reference (circular FKs handled gracefully)
Oracle source is available and read-only throughout the entire migration
PostgreSQL target schema is empty or can be safely TRUNCATEd
Network latency between migration host and databases is reasonable (<100ms RTT)
CHECK constraint bodies use standard SQL-92 predicates (complex Oracle-specific expressions may fail)
View bodies use Oracle syntax that maps 1:1 to PostgreSQL (non-standard Oracle functions require manual editing)
Oracle user has SELECT on all_* data dictionary views + user tables
PostgreSQL user has CREATE privilege on the target database
Limitations
Limitation	Impact	Mitigation
Triggers not migrated	Oracle trigger bodies are extracted but not converted	include_triggers: false in config; manual port required
Parallel data load not implemented	Large schemas are slow	Future: implement concurrent.futures.ThreadPoolExecutor per MAX_WORKERS
Oracle PL/SQL packages not migrated	Stored procedures / functions are ignored	Out of scope; manual port required
View rewriting is heuristic	Complex Oracle SQL may not translate cleanly	Review output/ddl/07_views.sql before applying
No incremental/CDC migration	Full snapshot only	For live cutover, external CDC tools (e.g., AWS DMS, Debezium) required
No rollback automation	Manual DROP SCHEMA required	Documented in README Section 8
Checksum sampling only (not full-table)	Default 1000 rows per table	Increase CHECKSUM_SAMPLE_SIZE for higher confidence
11. Future Roadmap
Based on current implementation analysis, realistic future enhancements include:

Phase 1 — Performance & Parallelism
 Implement MAX_WORKERS parallel table migration in data_migrator.py
 Add progress bars (tqdm or similar) for long-running phases
 Streaming LOB migration for BLOB/CLOB-heavy schemas
 Incremental checksum validation (resume after failure)
Phase 2 — Advanced Oracle Features
 Oracle synonym support (currently ignored)
 Materialized view migration
 Partitioned table handling (Oracle → PostgreSQL declarative partitioning)
 Basic PL/SQL → PL/pgSQL transpiler for common patterns (loops, cursors)
Phase 3 — Observability & Ops
 Prometheus metrics export (table count, rows migrated, phase duration)
 Structured JSON logging (--log-format json flag)
 Slack/email notifications on completion or failure
 Web dashboard for real-time migration progress
Phase 4 — CI/CD & Automation
 GitHub Actions workflow for automated test migrations
 Docker Compose setup for local Oracle + PostgreSQL test environments
 Pre-commit hooks for .env leak prevention
 pytest test suite for unit tests of type mapping, CHECK rewriting, etc.
Phase 5 — Enterprise Features
 Schema diff tool (compare Oracle source vs PostgreSQL target post-migration)
 Delta/CDC migration mode for live cutover (integration with Debezium or similar)
 Multi-schema migration in a single run
 Encrypted credential storage (Vault, AWS Secrets Manager, Azure Key Vault)
 SSL/TLS enforcement flags for both Oracle and PostgreSQL connections
12. GitHub Best Practices Review
Current State
Practice	Status	Evidence
README	✅ Present	Comprehensive quick-start, config, phase reference
LICENSE	❌ Missing	No LICENSE file in repository
.gitignore	✅ Present	Excludes .env, __pycache__, output/ data
requirements.txt	✅ Present	Pinned versions for all dependencies
CONTRIBUTING.md	❌ Missing	—
CODE_OF_CONDUCT.md	❌ Missing	—
SECURITY.md	❌ Missing	—
CHANGELOG.md	❌ Missing	—
Badges	❌ None	No build status, coverage, or release badges
GitHub Actions	❌ None	No CI/CD workflows
Issue templates	❌ None	—
PR template	❌ None	—
Discussions enabled	❓ Unknown	Requires repo settings check
Wiki enabled	❓ Unknown	Requires repo settings check
Project board	❌ None	No visible project board
Releases / tags	❓ Unknown	Requires repo check
Recommended Additions
1. LICENSE
Suggested: MIT License or Apache 2.0 for open-source distribution. If internal/proprietary, add a restrictive copyright notice.

2. CONTRIBUTING.md
# Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Ensure all validation phases pass (`./scripts/run_migration.sh`)
4. Submit a pull request with a clear description

## Code Style
- Python: PEP 8 (enforced via `black` and `flake8`)
- Shell: ShellCheck clean
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`, etc.)

3. CODE_OF_CONDUCT.md
Adopt the Contributor Covenant.

4. SECURITY.md
# Security Policy

## Reporting a Vulnerability
Email security@example.com (replace with your contact). Do not open a public issue.

## Known Limitations
- `.env` credentials are stored in plaintext on disk
- `PGPASSWORD` is visible in process env on Linux (use `.pgpass` for production)

5. CHANGELOG.md
Use Keep a Changelog format:

# Changelog

## [Unreleased]
### Added
- Initial release with 12-phase migration pipeline

### Known Issues
- Parallel data loading not yet implemented
- Trigger bodies not converted (manual port required)

6. Badges (for README)
![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Maintenance](https://img.shields.io/badge/maintained-yes-brightgreen.svg)

7. GitHub Actions CI
.github/workflows/validate.yml:

name: Validation

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install flake8 black
      - run: black --check .
      - run: flake8 .

8. Issue Templates
.github/ISSUE_TEMPLATE/bug_report.md:

---
name: Bug report
about: Report a migration issue
---

**Phase that failed:** (e.g., Phase 5 — Data Migration)
**Oracle version:** 
**PostgreSQL version:** 
**Error message:**

9. Pull Request Template
.github/PULL_REQUEST_TEMPLATE.md:

## Description
<!-- What does this PR do? -->

## Validation
- [ ] All phases run successfully (`./scripts/run_migration.sh`)
- [ ] No new linting errors
- [ ] Updated README if configuration changed

10. Release Strategy
Tag releases using semantic versioning: v1.0.0, v1.1.0, etc.
Create GitHub Releases with CHANGELOG excerpt
Attach packaged artefacts (e.g., oracle-to-postgresql-v1.0.0.tar.gz)
13. Professional Project Summary
Portfolio / Resume
Oracle to PostgreSQL Migration Framework — A production-ready, idempotent Python + Bash pipeline automating the complete migration of Oracle database schemas to PostgreSQL, including DDL conversion (17 type mappings), FK-aware batch data loading (psycopg2 copy_expert), and dual-layer validation (row counts + MD5 checksums). Eliminated Oracle OCI client dependency via oracledb thin mode. Delivered 12-phase architecture with comprehensive logging, structured JSON artefacts, and rollback procedures. Executed against Oracle HR reference schema with 0 data discrepancies post-migration.

Tech: Python 3.9+, Bash, oracledb, psycopg2, PostgreSQL 12+, Oracle 11g+, Kahn's algorithm (topological sort)

LinkedIn
Designed and implemented a production-ready database migration framework automating the Oracle → PostgreSQL cutover lifecycle: schema discovery, DDL conversion, FK-aware data loading, and dual-layer validation. Achieved idempotent execution across all 12 phases using IF NOT EXISTS DDL guards and TRUNCATE + COPY data loads. Delivered zero-downtime capability on Oracle source (read-only migration) and comprehensive audit trails via structured JSON reports and per-phase logging. Removed Oracle OCI dependency via oracledb thin mode, enabling execution on any Python 3.9+ host.

GitHub Profile
🚀 Production Database Migration Framework

Automates Oracle → PostgreSQL schema & data migration with FK-aware ordering, dual validation, and zero Oracle OCI dependency.

✅ 12-phase idempotent pipeline

✅ Row count + MD5 checksum validation

✅ Structured JSON artefacts

View Repository →

14. Architecture Decision Summary
Why This Architecture is Appropriate
Decision	Business Justification	Technical Justification
Python + Bash hybrid	Common toolchain; low onboarding friction	Bash for control flow; Python for data processing
Sequential pipeline (not parallel)	Simplicity; FK dependencies require ordering	Topological sort ensures correctness; parallelism is a future optimisation
FK-aware topological sort	Prevents constraint violations	Kahn's algorithm is O(V+E); scalable for typical schemas
Idempotent DDL with IF NOT EXISTS	Re-runs are free; reduces cutover risk	PostgreSQL/Oracle both support this natively
TRUNCATE before COPY	Guarantees clean slate on re-run	Faster than DELETE for large tables
FKs applied after data load	Avoids deferred constraint overhead	Data load can ignore FK order if FKs are absent
Dual validation (count + checksum)	High-confidence data integrity	Count catches row loss; checksum catches corruption
copy_expert() over execute_values()	Highest throughput for bulk load	Avoids per-row round trips; native PostgreSQL protocol
No Oracle OCI client	Deployment simplicity; Docker-friendly	oracledb thin mode is pure Python; no native libs
Structured JSON artefacts	Machine-readable for downstream automation	Enables integration with monitoring, alerting, BI
Suitability for the Problem
This architecture is optimal for:

One-time lift-and-shift migrations of well-understood Oracle schemas
Schema-first migrations where DDL must be reviewed before data cutover
Repeatable migrations for dev/test/staging environments
Audit-compliant migrations requiring full logs and validation reports
This architecture is not optimal for:

Live, near-zero downtime migrations requiring CDC (use AWS DMS, Debezium)
Schemas with complex Oracle PL/SQL (requires manual port)
Multi-terabyte databases (single-threaded data load is slow)
Continuous replication (this is a snapshot-based tool)
For the intended use case — Oracle → PostgreSQL database modernisation where the schema is known, the cutover window is acceptable, and full validation is mandatory — this architecture is production-ready and fit for purpose.

Architecture Decision Record (ADR) — Mermaid Diagram
Unable to Render Diagram

Final Notes
This supplementary documentation should be stored as:

ARCHITECTURE.md (Sections 1–4, 14)
CONTRIBUTING.md (Section 12, items 2–9)
SECURITY.md (Section 12, item 4)
ROADMAP.md (Section 11)
