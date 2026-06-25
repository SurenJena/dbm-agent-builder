# Database Migration Project Structure

This template defines the **STANDARD, DETERMINISTIC** structure for all database migration projects.

**CRITICAL:** This structure MUST be generated identically for ALL Oracle→PostgreSQL migration requests, regardless of how the user phrases the request (e.g., "Migrate Oracle schema", "Transform Oracle to PostgreSQL", "Convert Oracle database", etc.).

**EXCLUDED FOLDERS:** The following folders are NOT generated (user manages separately):
- `docker/` - User provides their own Docker setup
- `backups/` - User manages their own backup strategy

```
{project-name}/
├── config/
│   ├── .env.template              # Environment variables template
│   ├── source_db.yaml             # Source database configuration
│   ├── target_db.yaml             # Target database configuration
│   └── migration_config.yaml      # Migration execution parameters
│
├── discovery/
│   ├── extract_schema.py          # Extract schema metadata from source
│   ├── analyze_dependencies.py    # Analyze table dependencies
│   └── generate_report.py         # Generate discovery report
│
├── conversion/
│   ├── ddl_converter.py           # Convert DDL to target dialect
│   ├── data_type_mapper.py        # Map data types between platforms
│   └── sql_dialect_translator.py  # Translate SQL syntax
│
├── migration/
│   ├── schema_migrator.py         # Migrate schema (DDL)
│   ├── data_migrator.py           # Migrate data (DML)
│   └── batch_processor.py         # Process data in batches
│
├── validation/
│   ├── count_validator.py         # Validate row counts
│   ├── checksum_validator.py      # Validate data checksums
│   └── integrity_checker.py       # Check constraints and relationships
│
├── reporting/
│   └── html_report_generator.py   # Generate HTML validation reports
│
├── tests/
│   ├── test_conversion.py         # Test DDL conversion
│   ├── test_migration.py          # Test data migration
│   └── test_validation.py         # Test validation logic
│
├── scripts/
│   ├── run_migration.sh           # Main migration execution script
│   ├── rollback.sh                # Rollback script
│   ├── validate.sh                # Validation script
│   └── test_connections.py        # Test database connectivity
│
├── output/
│   ├── ddl/
│   │   ├── 01_tables.sql          # Generated table DDL
│   │   ├── 02_sequences.sql       # Generated sequence DDL
│   │   ├── 03_constraints_pk_unique.sql  # PK and unique constraints
│   │   ├── 04_constraints_fk.sql  # Foreign key constraints
│   │   ├── 05_constraints_check.sql # Check constraints
│   │   ├── 06_indexes.sql         # Generated index DDL
│   │   └── 07_views.sql           # Generated view DDL
│   ├── logs/
│   │   └── (generated during execution)
│   └── reports/
│       ├── schema_metadata.json   # Extracted schema metadata
│       ├── dependency_analysis.md # Dependency analysis report
│       └── schema_parity_validation.md # Parity validation report
│
├── docs/
│   ├── MIGRATION_PLAN.md          # Detailed migration plan
│   ├── SCHEMA_MAPPING.md          # Schema conversion details
│   ├── RUNBOOK.md                 # Execution runbook
│   └── SEQUENCE_MIGRATION_FIX.md  # Sequence handling documentation
│
├── logs/
│   └── (created during execution)
│
├── .gitignore                     # Git ignore file
├── requirements.txt               # Python dependencies
└── README.md                      # Project documentation
```

**IMPORTANT NOTES:**
1. `docker/` folder is NOT generated - users provide their own Docker setup
2. `backups/` folder is NOT generated - users manage their own backup strategy
3. All other folders and files MUST be generated identically every time
4. File names, folder structure, and logic MUST be deterministic
5. No variation allowed based on prompt phrasing

## File Descriptions

### Configuration Files

**`.env.template`**
- Template for environment variables
- Contains placeholders for sensitive data
- Should be copied to `.env` and filled with actual values
- `.env` should be in `.gitignore`

**`source_db.yaml`**
- Source database connection details
- Migration scope (tables, views, procedures)
- Authentication configuration

**`target_db.yaml`**
- Target database connection details
- Optimization settings
- Performance tuning parameters

**`migration_config.yaml`**
- Batch size and parallel threads
- Phase configuration
- Validation settings
- Logging configuration

### Discovery Scripts

**`extract_schema.py`**
- Connects to source database
- Extracts complete schema metadata
- Outputs JSON file with all schema objects

**`analyze_dependencies.py`**
- Analyzes foreign key relationships
- Performs topological sort
- Generates migration order
- Identifies circular dependencies

**`generate_report.py`**
- Creates human-readable discovery report
- Includes statistics and recommendations
- Highlights potential issues

### Conversion Scripts

**`ddl_converter.py`**
- Converts DDL from source to target dialect
- Maps data types
- Translates SQL syntax
- Generates target DDL files

**`data_type_mapper.py`**
- Maintains data type mapping rules
- Handles platform-specific types
- Provides conversion functions

**`sql_dialect_translator.py`**
- Translates SQL functions
- Converts syntax differences
- Handles platform-specific features

### Migration Scripts

**`schema_migrator.py`**
- Creates target schema
- Executes DDL statements
- Handles errors and retries

**`data_migrator.py`**
- Migrates data in batches
- Supports parallel execution
- Implements error recovery

**`batch_processor.py`**
- Processes data in configurable batches
- Manages memory efficiently
- Provides progress tracking

### Validation Scripts

**`count_validator.py`**
- Compares row counts between source and target
- Generates count validation report

**`data_validator.py`**
- Samples and compares data
- Validates data integrity
- Checks for data corruption

**`integrity_checker.py`**
- Validates foreign key relationships
- Checks constraint violations
- Verifies referential integrity

### Test Files

**`test_conversion.py`**
- Unit tests for DDL conversion
- Tests data type mapping
- Validates SQL translation

**`test_migration.py`**
- Integration tests for migration process
- Tests end-to-end migration
- Validates error handling

**`test_validation.py`**
- Tests validation logic
- Ensures validation accuracy

### Execution Scripts

**`run_migration.sh`**
- Main orchestration script
- Executes all migration phases
- Handles errors and logging

**`rollback.sh`**
- Rollback procedures
- Restores from backup
- Reverts changes

**`validate.sh`**
- Runs all validation checks
- Generates validation report

**`test_connections.py`**
- Tests source database connectivity
- Tests target database connectivity
- Validates permissions

### Output Files

**DDL Files**
- Generated SQL statements for target database
- Organized by object type
- Ready for execution

**Log Files**
- Detailed execution logs
- Error logs with stack traces
- Timestamped entries

**Report Files**
- Markdown-formatted reports
- Include statistics and findings
- Provide recommendations

### Documentation

**`MIGRATION_PLAN.md`**
- Comprehensive migration plan
- Timeline and milestones
- Risk assessment
- Rollback procedures

**`SCHEMA_MAPPING.md`**
- Detailed schema conversion mapping
- Data type conversions
- Object name mappings

**`RUNBOOK.md`**
- Step-by-step execution guide
- Prerequisites and setup
- Troubleshooting guide

**`KNOWN_ISSUES.md`**
- Known limitations
- Workarounds
- Platform-specific issues

## Usage

1. **Setup:**
   ```bash
   cp config/.env.template config/.env
   # Edit .env with actual values
   pip install -r requirements.txt
   ```

2. **Discovery:**
   ```bash
   python discovery/extract_schema.py
   python discovery/analyze_dependencies.py
   python discovery/generate_report.py
   ```

3. **Conversion:**
   ```bash
   python conversion/ddl_converter.py oracle postgresql
   ```

4. **Migration:**
   ```bash
   chmod +x scripts/run_migration.sh
   ./scripts/run_migration.sh
   ```

5. **Validation:**
   ```bash
   chmod +x scripts/validate.sh
   ./scripts/validate.sh
   ```

## Best Practices

1. Always test in non-production environment first
2. Keep backups before starting migration
3. Review generated DDL before execution
4. Monitor migration progress
5. Validate thoroughly before cutover
6. Document all decisions and changes
7. Have rollback plan ready