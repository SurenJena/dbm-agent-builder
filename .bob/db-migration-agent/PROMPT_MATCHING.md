# Prompt Matching and Normalization for Oracle→PostgreSQL Migration

## Overview
This document defines how the db-migration agent normalizes all Oracle→PostgreSQL migration prompt variations into a single canonical form, ensuring deterministic output.

## Canonical Form
**Target:** `"Migrate Oracle schema to PostgreSQL"`

All prompt variations are normalized to this canonical form before processing.

## Normalization Algorithm

### Step 1: Extract Database Types
- **Source:** Oracle (case-insensitive)
- **Target:** PostgreSQL, Postgres, PG (all normalized to PostgreSQL)

### Step 2: Ignore Action Verbs
The following action verbs are treated as equivalent:
- migrate
- transform
- convert
- port
- move
- transfer
- change
- switch

### Step 3: Ignore Prepositions
The following prepositions are treated as equivalent:
- to
- into
- onto
- towards

### Step 4: Ignore Object Variations
The following objects are treated as equivalent:
- schema
- database
- database schema
- DB
- tables
- data

### Step 5: Ignore Qualifiers
The following qualifiers are ignored:
- compatible
- format
- structure
- specific schema names (e.g., HR, SALES, FINANCE)

### Step 6: Map to Canonical Form
Result: `"Oracle to PostgreSQL migration"`

## Equivalent Prompt Examples

### Group 1: Basic Variations
All of these produce IDENTICAL output:
1. "Migrate Oracle schema to PostgreSQL"
2. "Migrate Oracle schema into PostgreSQL"
3. "Migrate Oracle to PostgreSQL"
4. "Migrate Oracle database to PostgreSQL"
5. "Migrate Oracle DB to PostgreSQL"

### Group 2: Transform Variations
All of these produce IDENTICAL output:
1. "Transform Oracle schema to PostgreSQL"
2. "Transform Oracle schema into PostgreSQL"
3. "Transform Oracle schema into PostgreSQL compatible schema"
4. "Transform Oracle database to PostgreSQL format"
5. "Transform Oracle to PostgreSQL"

### Group 3: Convert Variations
All of these produce IDENTICAL output:
1. "Convert Oracle schema to PostgreSQL"
2. "Convert Oracle schema into PostgreSQL"
3. "Convert Oracle database to PostgreSQL"
4. "Convert Oracle database schema to PostgreSQL"
5. "Convert Oracle database schema to PostgreSQL format"
6. "Convert Oracle schema to PostgreSQL format"

### Group 4: Port/Move/Transfer Variations
All of these produce IDENTICAL output:
1. "Port Oracle schema to PostgreSQL"
2. "Port Oracle database to PostgreSQL"
3. "Move Oracle schema to PostgreSQL"
4. "Move Oracle tables to PostgreSQL"
5. "Transfer Oracle schema to PostgreSQL"
6. "Transfer Oracle data to PostgreSQL"

### Group 5: Short Form Variations
All of these produce IDENTICAL output:
1. "Oracle to PostgreSQL"
2. "Oracle to Postgres"
3. "Oracle → PostgreSQL"
4. "Oracle PostgreSQL migration"
5. "Oracle Postgres migration"

### Group 6: Schema-Specific Variations
All of these produce IDENTICAL output:
1. "Migrate Oracle HR schema to PostgreSQL"
2. "Migrate Oracle SALES schema to PostgreSQL"
3. "Convert Oracle FINANCE database to PostgreSQL"
4. "Transform Oracle INVENTORY schema into PostgreSQL"

**Note:** Schema names (HR, SALES, FINANCE, etc.) are extracted for configuration but do NOT affect the generated codebase structure.

## Output Guarantee

### What Stays IDENTICAL Across All Prompts:
1. **Project name:** `oracle-to-postgresql/`
2. **Folder structure:** 8 directories (config, discovery, conversion, migration, validation, scripts, output, logs)
3. **File count:** Exactly 17 files
4. **File names:** Identical across all generations
5. **File content:** Identical logic and algorithms
6. **Execution order:** Identical migration phases
7. **Validation logic:** Identical checks
8. **Error handling:** Identical patterns
9. **Logging format:** Identical structure
10. **Dependencies:** Identical 4 packages in requirements.txt

### What Changes Based on User Input:
1. **Connection details:** Oracle host, port, service_name, username, password
2. **Target details:** PostgreSQL host, port, database, username, password
3. **Schema name:** Extracted from prompt (e.g., HR, SALES) and used in config files
4. **Migration scope:** Tables to include/exclude (if specified)

### What NEVER Changes:
- Project structure
- File names
- Core migration logic
- Validation algorithms
- Error handling patterns
- Logging format
- Documentation structure

## Verification Checklist

Before completing any Oracle→PostgreSQL migration request, verify:

- [ ] Project name is `oracle-to-postgresql/` (not oracle-postgres/, ora2pg/, etc.)
- [ ] Exactly 17 files generated (no more, no less)
- [ ] Exactly 8 directories (config, discovery, conversion, migration, validation, scripts, output, logs)
- [ ] No docker/ or backups/ folders
- [ ] No tests/ or docs/ folders (unless explicitly requested)
- [ ] Only 1 .md file: README.md (no additional documentation files)
- [ ] requirements.txt has exactly 4 dependencies
- [ ] README.md has exactly 9 sections
- [ ] All file names match canonical structure
- [ ] Sequence handling includes START WITH and MAXVALUE capping
- [ ] Schema parity validation included in run_migration.sh

## Testing Prompt Normalization

To test that normalization works correctly, try these prompts and verify IDENTICAL output:

```bash
# Test 1: Basic variations
"Migrate Oracle schema to PostgreSQL"
"Transform Oracle schema into PostgreSQL"
"Convert Oracle database to PostgreSQL"

# Test 2: With qualifiers
"Migrate Oracle schema into PostgreSQL compatible format"
"Transform Oracle database schema to PostgreSQL structure"
"Convert Oracle schema to PostgreSQL format"

# Test 3: With schema names
"Migrate Oracle HR schema to PostgreSQL"
"Convert Oracle SALES database to PostgreSQL"
"Transform Oracle FINANCE schema into PostgreSQL"

# Test 4: Short forms
"Oracle to PostgreSQL"
"Oracle PostgreSQL migration"
"Oracle → Postgres"
```

**Expected Result:** All tests produce the EXACT SAME oracle-to-postgresql/ codebase with ZERO variation in structure, file names, or logic.

## Error Cases

### Invalid Prompts (Should NOT trigger this mode):
- "Migrate MySQL to PostgreSQL" (different source)
- "Migrate Oracle to Snowflake" (different target)
- "Migrate PostgreSQL to Oracle" (reverse direction)
- "Optimize Oracle database" (not a migration)
- "Backup Oracle schema" (not a migration)

### Ambiguous Prompts (Should ask for clarification):
- "Migrate database" (source and target not specified)
- "Convert schema to PostgreSQL" (source not specified)
- "Oracle migration" (target not specified)

## Success Criteria

Prompt normalization is successful if:
1. All equivalent prompts generate identical project structure
2. File names are consistent across all generations
3. Core logic and algorithms are identical
4. No unnecessary files or folders are created
5. Output is deterministic and reproducible
6. User gets single source of truth for Oracle→PostgreSQL migrations

## References

- See `.bob/db-migration-agent/DETERMINISTIC_GENERATION.md` for complete output structure
- See `.bob/custom_modes.yaml` (db-migration-agent section) for mode configuration
- See `oracle-to-postgresql/` for reference implementation