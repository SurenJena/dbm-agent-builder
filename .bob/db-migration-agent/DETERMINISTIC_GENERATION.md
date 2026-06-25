
# Deterministic Generation Rules for Oracle→PostgreSQL Migration

## Overview
This document defines the ABSOLUTE rules for generating identical migration codebases regardless of prompt variation. ALL Oracle→PostgreSQL migration requests MUST produce the EXACT SAME output structure, file names, and implementation logic.

## Canonical Project Structure

**MANDATORY - ALWAYS GENERATE EXACTLY THIS STRUCTURE:**

```
oracle-to-postgresql/
├── config/
│   ├── .env.template              # Environment variables template
│   ├── source_db.yaml             # Oracle connection config
│   ├── target_db.yaml             # PostgreSQL connection config
│   └── migration_config.yaml      # Migration settings
├── discovery/
│   ├── extract_schema.py          # Extract Oracle schema metadata
│   └── analyze_dependencies.py    # Analyze FK dependencies
├── conversion/
│   └── ddl_converter.py           # Convert Oracle DDL to PostgreSQL
├── migration/
│   └── data_migrator.py           # Batch data migration with progress tracking
├── validation/
│   ├── count_validator.py         # Row count validation
│   └── checksum_validator.py      # Data integrity validation
├── scripts/
│   ├── run_migration.sh           # Main orchestration script
│   └── test_connections.py        # Connection testing utility
├── output/
│   ├── ddl/                       # Generated DDL files (created at runtime)
│   ├── logs/                      # Execution logs (created at runtime)
│   └── reports/                   # Validation reports (created at runtime)
├── logs/                          # Runtime logs directory
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
└── README.md                      # Project documentation
```

## Excluded Folders (NEVER GENERATE)

- `docker/` - User provides their own Docker setup
- `backups/` - User manages their own backup strategy
- `tests/` - Only if explicitly requested
- `docs/` - Only if explicitly requested
- Any additional .md files beyond README.md

## Prompt Normalization Rules

### Canonical Form
ALL prompts are normalized to: **"Migrate Oracle schema to PostgreSQL"**

### Equivalent Prompt Variations (ALL produce IDENTICAL output)

**Action Verbs (all equivalent):**
- Migrate
- Transform
- Convert
- Port
- Move
- Transfer

**Prepositions (all equivalent):**
- to
- into
- onto

**Object Variations (all equivalent):**
- schema
- database
- database schema
- DB
- tables

**Qualifiers (all ignored):**
- compatible
- format
- structure
- HR (or any schema name)

**Examples of Equivalent Prompts:**
1. "Migrate Oracle schema to PostgreSQL"
2. "Migrate Oracle schema into PostgreSQL"
3. "Transform Oracle schema to PostgreSQL"
4. "Transform Oracle schema into PostgreSQL compatible schema"
5. "Convert Oracle database to PostgreSQL"
6. "Convert Oracle database schema to PostgreSQL format"
7. "Migrate Oracle to PostgreSQL"
8. "Oracle to PostgreSQL migration"
9. "Oracle PostgreSQL migration"
10. "Migrate Oracle HR schema to PostgreSQL"
11. "Port Oracle database to PostgreSQL"
12. "Transfer Oracle schema into PostgreSQL format"

**ALL of the above MUST generate the EXACT SAME codebase.**

## File Content Determinism

### 1. extract_schema.py
**MUST ALWAYS include:**
- Oracle connection using cx_Oracle
- Extract tables, columns, data types, constraints
- Extract sequences with last_number
- Extract indexes (excluding constraint-backing indexes)
- Extract views, triggers, procedures, functions
- Save metadata to JSON files
- Identical error handling and logging

### 2. ddl_converter.py
**MUST ALWAYS include:**
- Data type mapping: NUMBER→NUMERIC/INTEGER/BIGINT, VARCHAR2→VARCHAR, DATE→TIMESTAMP
- Sequence conversion with START WITH <last_number> and MAXVALUE capped to 9223372036854775807
- Constraint conversion (PK, FK, UK, CHECK)
- Index conversion
- View conversion
- Identical conversion algorithms

### 3. data_migrator.py
**MUST ALWAYS include:**
- Batch processing (default 10,000 rows)
- Progress tracking with percentage
- Transaction management
- Error handling with rollback
- Logging to output/logs/
- Identical migration logic

### 4. count_validator.py
**MUST ALWAYS include:**
- Row count comparison (source vs target)
- Table-by-table validation
- Mismatch reporting
- Identical validation logic

### 5. checksum_validator.py
**MUST ALWAYS include:**
- Data sampling (configurable percentage)
- Checksum calculation
- Integrity verification
- Identical checksum algorithms

### 6. run_migration.sh
**MUST ALWAYS include:**
- Connection validation
- Schema extraction
- DDL conversion
- DDL execution in order: tables → sequences → PK/UK → data → FK → check → indexes → views
- Data migration
- Validation (counts + checksums)
- Schema parity validation
- Report generation
- Identical execution flow

### 7. test_connections.py
**MUST ALWAYS include:**
- Test Oracle connection
- Test PostgreSQL connection
- Verify permissions
- Report connectivity status
- Identical testing logic

## Configuration File Standards

### .env.template
```bash
# Oracle Source Database
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=ORCL
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password

# PostgreSQL Target Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=target_db
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
```

### source_db.yaml
```yaml
database_type: oracle
host: ${ORACLE_HOST}
port: ${ORACLE_PORT}
service_name: ${ORACLE_SERVICE}
username: ${ORACLE_USER}
password: ${ORACLE_PASSWORD}
schema: HR
```

### target_db.yaml
```yaml
database_type: postgresql
host: ${POSTGRES_HOST}
port: ${POSTGRES_PORT}
database: ${POSTGRES_DB}
username: ${POSTGRES_USER}
password: ${POSTGRES_PASSWORD}
schema: public
```

### migration_config.yaml
```yaml
migration:
  batch_size: 10000
  parallel_workers: 4
  validation:
    row_counts: true
    checksums: true
    sample_percentage: 10
  logging:
    level: INFO
    file: logs/migration.log
```

## Python Dependencies (requirements.txt)

**MUST ALWAYS include EXACTLY:**
```
cx-Oracle==8.3.0
psycopg2-binary==2.9.9
PyYAML==6.0.1
python-dotenv==1.0.0
```

## README.md Structure

**MUST ALWAYS include these sections:**
1. Project Overview
2. Prerequisites
3. Installation
4. Configuration
5. Usage
6. Migration Process
7. Validation
8. Troubleshooting
9. Project Structure

## Execution Order (IMMUTABLE)

**Phase 1: Discovery**
1. Test connections
2. Extract schema metadata
3. Analyze dependencies

**Phase 2: Conversion**
1. Convert DDL (tables, sequences, constraints, indexes, views)
2. Generate PostgreSQL-compatible SQL

**Phase 3: Schema Migration**
1. Create tables
2. Create sequences with START WITH
3. Create primary keys and unique constraints
4. (Data migration happens here)
5. Create foreign keys
6. Create check constraints
7. Create indexes
8. Create views

**Phase 4: Data Migration**
1. Migrate data in batches
2. Track progress
3. Handle errors

**Phase 5: Validation**
1. Validate row counts
2. Validate checksums
3. Validate schema parity
4. Generate reports

## Schema Parity Validation (MANDATORY)

**MUST ALWAYS validate:**
- Table count (Oracle vs PostgreSQL)
- Sequence count and starting values
- Primary key count
- Foreign key count
- Unique constraint count
- Check constraint count
- Index count (excluding constraint-backing)
- View count
- Trigger count
- Function/procedure count

**Generate corrective SQL if discrepancies found.**

## Error Handling Standards

**ALL scripts MUST:**
- Use try-except blocks
- Log errors with timestamps
- Rollback transactions on failure
- Provide clear error messages
- Exit with non-zero status on failure

## Logging Standards

**ALL scripts MUST:**
- Log to both console and file
- Use format: `%(asctime)s - %(levelname)s - %(message)s`
- Log to `logs/` and `output/logs/` directories
- Include operation start/end timestamps
- Log progress percentages for long operations

## Zero Variation Guarantee

**ABSOLUTE RULES:**
1. File names are IMMUTABLE - no variations allowed
2. Folder structure is IMMUTABLE - no additions or omissions
3. Core logic is IMMUTABLE - same algorithms every time
4. Configuration templates are IMMUTABLE - same structure every time
5. Execution order is IMMUTABLE - same sequence every time
6. Validation logic is IMMUTABLE - same checks every time
7. Error handling is IMMUTABLE - same patterns every time
8. Logging format is IMMUTABLE - same format every time
9. Dependencies are IMMUTABLE - same versions every time
10. Documentation structure is IMMUTABLE - same sections every time

## Quality Checklist

Before completing ANY Oracle→PostgreSQL migration request, verify:

- [ ] Exact folder structure matches canonical form
- [ ] All 17 core files are present (no more, no less)
- [ ] No docker/ or backups/ folders generated
- [ ] Sequence conversion includes START WITH and MAXVALUE capping
- [ ] Data type mappings are consistent
- [ ] Execution order matches Phase 1-5 sequence
- [ ] Schema parity validation is included
- [ ] All scripts use identical error handling
- [ ] All scripts use identical logging format
- [ ] requirements.txt has exactly 4 dependencies
- [ ] README.md has exactly 9 sections
- [ ] No additional .md files beyond README.md
- [ ] .gitignore includes .env and output directories
- [ ] All YAML configs use environment variable substitution
- [ ] run_migration.sh orchestrates all phases in correct order

## Success Criteria

A migration codebase is considered DETERMINISTIC and CORRECT if:

1. **Structure Test:** Folder tree matches canonical form exactly
2. **File Test:** All 17 core files exist with correct names
3. **Logic Test:** Core algorithms are identical across generations
4. **Config Test:** Configuration files match templates exactly
5. **Dependency Test:** requirements.txt matches exactly
6. **Documentation Test:** README.md structure matches exactly
7. **Exclusion Test:** No docker/, backups/, tests/, or docs/ folders
