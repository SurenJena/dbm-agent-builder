#!/usr/bin/env bash
# =============================================================================
# run_migration.sh — Oracle to PostgreSQL Migration Orchestrator
# =============================================================================
# Usage:
#   ./scripts/run_migration.sh                  # Full migration (all phases)
#   ./scripts/run_migration.sh --schema-only    # Skip Phase 5 (data) + 8-9 (validation)
#   ./scripts/run_migration.sh --skip-validation # Skip Phases 8-9 only
#   ./scripts/run_migration.sh --data-only      # Skip Phases 2-4 (schema already applied)
#
# Phase sequence (RULE 11 — immutable order):
#   Phase 0  — Prerequisites + __pycache__ purge  (always runs)
#   Phase 1  — Connection tests                   (always runs)
#   Phase 2  — Schema discovery                   (skipped with --data-only)
#   Phase 3  — DDL conversion                     (skipped with --data-only)
#   Phase 4  — Apply schema to PostgreSQL         (skipped with --data-only)
#   Phase 5  — Data migration                     (skipped with --schema-only)
#   Phase 6  — Post-data DDL: FK/CHECK/indexes    (always runs)
#   Phase 7  — View creation                      (always runs)
#   Phase 8  — Row-count validation               (skipped with --schema-only / --skip-validation)
#   Phase 9  — Checksum validation                (skipped with --schema-only / --skip-validation)
#   Phase 10 — Schema parity validation           (always runs)
#   Phase 11 — ANALYZE / statistics               (always runs; always final)
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve project root (directory containing this script's parent)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Load .env (if present)
# ---------------------------------------------------------------------------
ENV_FILE="${BASE_DIR}/config/.env"
if [[ -f "${ENV_FILE}" ]]; then
    # Export only KEY=VALUE lines (ignore comments and blanks)
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
fi

# ---------------------------------------------------------------------------
# Defaults (overridable via .env or shell environment)
# ---------------------------------------------------------------------------
ORACLE_HOST="${ORACLE_HOST:-localhost}"
ORACLE_PORT="${ORACLE_PORT:-1521}"
ORACLE_SERVICE="${ORACLE_SERVICE:-ORCL}"
ORACLE_SCHEMA="${ORACLE_SCHEMA:-HR}"
ORACLE_USER="${ORACLE_USER:-hr}"
ORACLE_PASSWORD="${ORACLE_PASSWORD:-hr}"

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_DATABASE="${PG_DATABASE:-hr_db}"
PG_SCHEMA="${PG_SCHEMA:-hr}"
PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-postgres}"

OUTPUT_DIR="${OUTPUT_DIR:-${BASE_DIR}/output}"
LOG_DIR="${LOG_DIR:-${BASE_DIR}/logs}"

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
SCHEMA_ONLY=false
SKIP_VALIDATION=false
DATA_ONLY=false

for arg in "$@"; do
    case "${arg}" in
        --schema-only)     SCHEMA_ONLY=true ;;
        --skip-validation) SKIP_VALIDATION=true ;;
        --data-only)       DATA_ONLY=true ;;
        *)
            echo "Unknown flag: ${arg}"
            echo "Usage: $0 [--schema-only|--skip-validation|--data-only]"
            exit 1
            ;;
    esac
done

# --schema-only implies --skip-validation
if [[ "${SCHEMA_ONLY}" == "true" ]]; then
    SKIP_VALIDATION=true
fi

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/run_migration_$(date +%Y%m%d_%H%M%S).log"

step()  { echo "" | tee -a "${LOG_FILE}"; echo "══════════════════════════════════════════════════════════" | tee -a "${LOG_FILE}"; echo "  ▶ $*" | tee -a "${LOG_FILE}"; echo "══════════════════════════════════════════════════════════" | tee -a "${LOG_FILE}"; }
info()  { echo "  [INFO]  $*" | tee -a "${LOG_FILE}"; }
warn()  { echo "  [WARN]  $*" | tee -a "${LOG_FILE}"; }
fail()  { echo "  [ERROR] $*" | tee -a "${LOG_FILE}"; exit 1; }
ok()    { echo "  [OK]    $*" | tee -a "${LOG_FILE}"; }

info "Migration log: ${LOG_FILE}"
info "BASE_DIR     : ${BASE_DIR}"
info "Flags        : schema-only=${SCHEMA_ONLY}  skip-validation=${SKIP_VALIDATION}  data-only=${DATA_ONLY}"

# POSIX-portable uppercase (bash 3.2 safe — macOS ships bash 3.2)
ORA_SCHEMA_UPPER="$(echo "${ORACLE_SCHEMA}" | tr '[:lower:]' '[:upper:]')"
PG_SCHEMA_LOWER="$(echo "${PG_SCHEMA}"    | tr '[:upper:]' '[:lower:]')"

# Export vars for Python scripts
export ORACLE_HOST ORACLE_PORT ORACLE_SERVICE ORACLE_SCHEMA ORACLE_USER ORACLE_PASSWORD
export PG_HOST PG_PORT PG_DATABASE PG_SCHEMA PG_USER PG_PASSWORD
export OUTPUT_DIR LOG_DIR

# psql connection string (no password in command line; use PGPASSWORD)
export PGPASSWORD="${PG_PASSWORD}"
PSQL="psql -h ${PG_HOST} -p ${PG_PORT} -U ${PG_USER} -d ${PG_DATABASE}"

DDL_DIR="${OUTPUT_DIR}/ddl"

# =============================================================================
# Phase 0 — Prerequisites + __pycache__ purge
# =============================================================================
step "Phase 0 — Prerequisites check + __pycache__ purge"

# Purge stale bytecode BEFORE any python3 call (MANDATORY — Rule 7)
find "${BASE_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
ok "__pycache__ purged"

# python3
if ! command -v python3 &>/dev/null; then
    fail "python3 not found — install Python 3.9+"
fi
PYTHON_VER="$(python3 --version 2>&1)"
ok "python3: ${PYTHON_VER}"

# psql
if ! command -v psql &>/dev/null; then
    fail "psql not found — install PostgreSQL client"
fi
PSQL_VER="$(psql --version 2>&1)"
ok "psql: ${PSQL_VER}"

# Python packages
for pkg in oracledb psycopg2 yaml dotenv; do
    if ! python3 -c "import ${pkg}" 2>/dev/null; then
        fail "Python package missing: ${pkg}  →  run: pip install -r requirements.txt"
    fi
done
ok "Python packages verified"

# Ensure output directories exist
mkdir -p "${DDL_DIR}" "${OUTPUT_DIR}/reports" "${LOG_DIR}"
ok "Output directories ready"

# =============================================================================
# Phase 1 — Connection tests (always runs)
# =============================================================================
step "Phase 1 — Connection tests"
python3 "${SCRIPT_DIR}/test_connections.py" \
    || fail "Connection tests failed — check credentials and network"
ok "Connections verified"

# =============================================================================
# Phase 2 — Schema discovery
# =============================================================================
step "Phase 2 — Schema discovery"
if [[ "${DATA_ONLY}" == "true" ]]; then
    warn "Phase 2 SKIPPED — --data-only flag set (schema assumed to exist)"
else
    python3 "${BASE_DIR}/discovery/extract_schema.py" \
        || fail "Schema extraction failed"
    python3 "${BASE_DIR}/discovery/analyze_dependencies.py" \
        || fail "Dependency analysis failed"
    ok "Schema discovery complete"
fi

# =============================================================================
# Phase 3 — DDL conversion
# =============================================================================
step "Phase 3 — DDL conversion"
if [[ "${DATA_ONLY}" == "true" ]]; then
    warn "Phase 3 SKIPPED — --data-only flag set"
else
    python3 "${BASE_DIR}/conversion/ddl_converter.py" \
        || fail "DDL conversion failed"
    ok "DDL conversion complete — files in ${DDL_DIR}/"
fi

# =============================================================================
# Phase 4 — Apply schema to PostgreSQL
# =============================================================================
step "Phase 4 — Apply schema to PostgreSQL (tables → sequences → PK/UK)"
if [[ "${DATA_ONLY}" == "true" ]]; then
    warn "Phase 4 SKIPPED — --data-only flag set"
else
    for sql_file in 01_tables.sql 02_sequences.sql 03_pk_uk.sql; do
        if [[ -f "${DDL_DIR}/${sql_file}" ]]; then
            info "Applying ${sql_file} …"
            ${PSQL} -f "${DDL_DIR}/${sql_file}" \
                || fail "Failed to apply ${sql_file}"
            ok "${sql_file} applied"
        else
            warn "${sql_file} not found — skipping"
        fi
    done
fi

# =============================================================================
# Phase 5 — Data migration
# =============================================================================
step "Phase 5 — Data migration"
if [[ "${SCHEMA_ONLY}" == "true" ]]; then
    warn "Phase 5 SKIPPED — --schema-only flag set"
else
    # Drop existing FKs before data load to allow idempotent re-runs
    # (circular FK dependencies block TRUNCATE CASCADE if FKs exist)
    info "Dropping existing FK constraints before data load …"
    ${PSQL} -t -c "
        SELECT 'ALTER TABLE \"' || n.nspname || '\".\"' || t.relname || '\" DROP CONSTRAINT IF EXISTS \"' || c.conname || '\";'
        FROM   pg_constraint c
        JOIN   pg_class t     ON t.oid = c.conrelid
        JOIN   pg_namespace n ON n.oid = c.connamespace
        WHERE  c.contype = 'f'
          AND  n.nspname = '${PG_SCHEMA_LOWER}'
    " | ${PSQL} -f - 2>/dev/null || true
    ok "Existing FK constraints dropped"

    python3 "${BASE_DIR}/migration/data_migrator.py" \
        || fail "Data migration failed"
    ok "Data migration complete"
fi

# =============================================================================
# Phase 6 — Post-data DDL: FK / CHECK / indexes (always runs)
# =============================================================================
step "Phase 6 — Post-data DDL (FK constraints → CHECK constraints → indexes)"
for sql_file in 04_fk.sql 05_check.sql 06_indexes.sql; do
    if [[ -f "${DDL_DIR}/${sql_file}" ]]; then
        info "Applying ${sql_file} …"
        ${PSQL} -f "${DDL_DIR}/${sql_file}" \
            || fail "Failed to apply ${sql_file}"
        ok "${sql_file} applied"
    else
        warn "${sql_file} not found — skipping"
    fi
done

# =============================================================================
# Phase 7 — View creation (always runs)
# =============================================================================
step "Phase 7 — View creation"
if [[ -f "${DDL_DIR}/07_views.sql" ]]; then
    ${PSQL} -f "${DDL_DIR}/07_views.sql" \
        || fail "Failed to apply 07_views.sql"
    ok "Views applied"
else
    warn "07_views.sql not found — no views to create"
fi

# =============================================================================
# Phase 8 — Row-count validation
# =============================================================================
step "Phase 8 — Row-count validation"
if [[ "${SKIP_VALIDATION}" == "true" ]]; then
    warn "Phase 8 SKIPPED — $(if [[ "${SCHEMA_ONLY}" == "true" ]]; then echo "--schema-only"; else echo "--skip-validation"; fi) flag set"
else
    python3 "${BASE_DIR}/validation/count_validator.py" \
        || fail "Row-count validation failed — see ${OUTPUT_DIR}/reports/count_validation.json"
    ok "Row-count validation PASSED"
fi

# =============================================================================
# Phase 9 — Checksum validation
# =============================================================================
step "Phase 9 — Checksum validation"
if [[ "${SKIP_VALIDATION}" == "true" ]]; then
    warn "Phase 9 SKIPPED — $(if [[ "${SCHEMA_ONLY}" == "true" ]]; then echo "--schema-only"; else echo "--skip-validation"; fi) flag set"
else
    python3 "${BASE_DIR}/validation/checksum_validator.py" \
        || fail "Checksum validation failed — see ${OUTPUT_DIR}/reports/checksum_validation.json"
    ok "Checksum validation PASSED"
fi

# =============================================================================
# Phase 10 — Schema parity validation (always runs)
# =============================================================================
step "Phase 10 — Schema parity validation"

PARITY_REPORT="${OUTPUT_DIR}/reports/schema_parity.txt"
{
    echo "Schema Parity Report"
    echo "Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Oracle schema  : ${ORA_SCHEMA_UPPER}"
    echo "PostgreSQL schema: ${PG_SCHEMA_LOWER}"
    echo "=========================================="
} > "${PARITY_REPORT}"

PARITY_ERRORS=0

# ── Table count ──────────────────────────────────────────────────────────────
ORA_TABLES=$(python3 - <<'PYEOF'
import os, oracledb
conn = oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=f"{os.environ['ORACLE_HOST']}:{os.environ['ORACLE_PORT']}/{os.environ['ORACLE_SERVICE']}"
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM all_tables WHERE owner = :1", [os.environ["ORACLE_SCHEMA"].upper()])
print(cur.fetchone()[0])
conn.close()
PYEOF
)

PG_TABLES=$(${PSQL} -t -c "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = '${PG_SCHEMA_LOWER}' AND table_type = 'BASE TABLE'
" | tr -d ' ')

info "Tables — Oracle: ${ORA_TABLES}  PostgreSQL: ${PG_TABLES}"
echo "Tables  — Oracle: ${ORA_TABLES}  PostgreSQL: ${PG_TABLES}" >> "${PARITY_REPORT}"
if [[ "${ORA_TABLES}" != "${PG_TABLES}" ]]; then
    warn "Table count MISMATCH: Oracle=${ORA_TABLES}  PG=${PG_TABLES}"
    PARITY_ERRORS=$((PARITY_ERRORS + 1))
fi

# ── View count ───────────────────────────────────────────────────────────────
ORA_VIEWS=$(python3 - <<'PYEOF'
import os, oracledb
conn = oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=f"{os.environ['ORACLE_HOST']}:{os.environ['ORACLE_PORT']}/{os.environ['ORACLE_SERVICE']}"
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM all_views WHERE owner = :1", [os.environ["ORACLE_SCHEMA"].upper()])
print(cur.fetchone()[0])
conn.close()
PYEOF
)

PG_VIEWS=$(${PSQL} -t -c "
    SELECT COUNT(*) FROM information_schema.views
    WHERE table_schema = '${PG_SCHEMA_LOWER}'
" | tr -d ' ')

info "Views  — Oracle: ${ORA_VIEWS}  PostgreSQL: ${PG_VIEWS}"
echo "Views   — Oracle: ${ORA_VIEWS}  PostgreSQL: ${PG_VIEWS}" >> "${PARITY_REPORT}"
if [[ "${ORA_VIEWS}" != "${PG_VIEWS}" ]]; then
    warn "View count MISMATCH: Oracle=${ORA_VIEWS}  PG=${PG_VIEWS}"
    PARITY_ERRORS=$((PARITY_ERRORS + 1))
fi

# ── Sequence count ───────────────────────────────────────────────────────────
ORA_SEQS=$(python3 - <<'PYEOF'
import os, oracledb
conn = oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=f"{os.environ['ORACLE_HOST']}:{os.environ['ORACLE_PORT']}/{os.environ['ORACLE_SERVICE']}"
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM all_sequences WHERE sequence_owner = :1", [os.environ["ORACLE_SCHEMA"].upper()])
print(cur.fetchone()[0])
conn.close()
PYEOF
)

PG_SEQS=$(${PSQL} -t -c "
    SELECT COUNT(*) FROM pg_sequences
    WHERE schemaname = '${PG_SCHEMA_LOWER}'
" | tr -d ' ')

info "Sequences — Oracle: ${ORA_SEQS}  PostgreSQL: ${PG_SEQS}"
echo "Sequences — Oracle: ${ORA_SEQS}  PostgreSQL: ${PG_SEQS}" >> "${PARITY_REPORT}"
if [[ "${ORA_SEQS}" != "${PG_SEQS}" ]]; then
    warn "Sequence count MISMATCH: Oracle=${ORA_SEQS}  PG=${PG_SEQS}"
    PARITY_ERRORS=$((PARITY_ERRORS + 1))
fi

# ── Index count ──────────────────────────────────────────────────────────────
ORA_IDX=$(python3 - <<'PYEOF'
import os, oracledb
conn = oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=f"{os.environ['ORACLE_HOST']}:{os.environ['ORACLE_PORT']}/{os.environ['ORACLE_SERVICE']}"
)
cur = conn.cursor()
cur.execute("""
    SELECT COUNT(*) FROM all_indexes i
    WHERE i.owner = :1
      AND NOT EXISTS (
        SELECT 1 FROM all_constraints c
        WHERE c.owner = :2
          AND c.constraint_name = i.index_name
          AND c.constraint_type IN ('P','U')
      )
""", [os.environ["ORACLE_SCHEMA"].upper(), os.environ["ORACLE_SCHEMA"].upper()])
print(cur.fetchone()[0])
conn.close()
PYEOF
)

PG_IDX=$(${PSQL} -t -c "
    SELECT COUNT(*) FROM pg_indexes
    WHERE schemaname = '${PG_SCHEMA_LOWER}'
      AND indexname NOT IN (
        SELECT conname FROM pg_constraint WHERE contype IN ('p','u')
      )
" | tr -d ' ')

info "Indexes   — Oracle: ${ORA_IDX}  PostgreSQL: ${PG_IDX}"
echo "Indexes   — Oracle: ${ORA_IDX}  PostgreSQL: ${PG_IDX}" >> "${PARITY_REPORT}"
if [[ "${ORA_IDX}" != "${PG_IDX}" ]]; then
    warn "Index count MISMATCH: Oracle=${ORA_IDX}  PG=${PG_IDX}"
    PARITY_ERRORS=$((PARITY_ERRORS + 1))
fi

# ── Constraint counts ────────────────────────────────────────────────────────
ORA_CONS=$(python3 - <<'PYEOF'
import os, oracledb
conn = oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=f"{os.environ['ORACLE_HOST']}:{os.environ['ORACLE_PORT']}/{os.environ['ORACLE_SERVICE']}"
)
cur = conn.cursor()
cur.execute("""
    SELECT COUNT(*) FROM all_constraints
    WHERE owner = :1 AND constraint_type IN ('P','U','R','C') AND status = 'ENABLED'
""", [os.environ["ORACLE_SCHEMA"].upper()])
print(cur.fetchone()[0])
conn.close()
PYEOF
)

PG_CONS=$(${PSQL} -t -c "
    SELECT COUNT(*) FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = '${PG_SCHEMA_LOWER}'
      AND c.contype IN ('p','u','f','c')
" | tr -d ' ')

info "Constraints — Oracle: ${ORA_CONS}  PostgreSQL: ${PG_CONS}"
echo "Constraints — Oracle: ${ORA_CONS}  PostgreSQL: ${PG_CONS}" >> "${PARITY_REPORT}"
if [[ "${ORA_CONS}" != "${PG_CONS}" ]]; then
    warn "Constraint count MISMATCH: Oracle=${ORA_CONS}  PG=${PG_CONS}"
    PARITY_ERRORS=$((PARITY_ERRORS + 1))
fi

echo "" >> "${PARITY_REPORT}"
echo "Parity errors: ${PARITY_ERRORS}" >> "${PARITY_REPORT}"

info "Parity report saved: ${PARITY_REPORT}"

if [[ "${PARITY_ERRORS}" -gt 0 ]]; then
    warn "Schema parity: ${PARITY_ERRORS} discrepancies found — review ${PARITY_REPORT}"
else
    ok "Schema parity: 0 discrepancies ✓"
fi

# =============================================================================
# Phase 11 — ANALYZE / statistics (always runs; always final)
# =============================================================================
step "Phase 11 — ANALYZE (gather PostgreSQL statistics)"
${PSQL} -c "ANALYZE;" \
    || fail "ANALYZE failed"
ok "ANALYZE complete"

# =============================================================================
# Final summary
# =============================================================================
echo "" | tee -a "${LOG_FILE}"
step "Migration Complete"
info "Flags used      : schema-only=${SCHEMA_ONLY}  skip-validation=${SKIP_VALIDATION}  data-only=${DATA_ONLY}"
info "Parity errors   : ${PARITY_ERRORS}"
info "Log file        : ${LOG_FILE}"
info "Parity report   : ${PARITY_REPORT}"
if [[ -f "${OUTPUT_DIR}/reports/count_validation.json" ]]; then
    info "Count report    : ${OUTPUT_DIR}/reports/count_validation.json"
fi
if [[ -f "${OUTPUT_DIR}/reports/checksum_validation.json" ]]; then
    info "Checksum report : ${OUTPUT_DIR}/reports/checksum_validation.json"
fi
ok "All phases completed successfully ✓"
