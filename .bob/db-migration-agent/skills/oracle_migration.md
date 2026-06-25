# Oracle Migration Skills

## Overview
Specialized skills and knowledge for migrating from Oracle databases to other platforms.

## Oracle-Specific Features

### PL/SQL to PL/pgSQL Conversion
Oracle's PL/SQL must be converted to target database procedural language.

**Key Differences:**
- Package structure → Schema organization
- `%TYPE` and `%ROWTYPE` → Similar in PostgreSQL
- Exception handling syntax differs
- Cursor syntax variations
- Dynamic SQL differences

**Example Conversion:**
```sql
-- Oracle PL/SQL
CREATE OR REPLACE PROCEDURE update_salary(
    p_emp_id IN NUMBER,
    p_increase IN NUMBER
) IS
    v_current_salary NUMBER;
BEGIN
    SELECT salary INTO v_current_salary
    FROM employees
    WHERE employee_id = p_emp_id;
    
    UPDATE employees
    SET salary = salary + p_increase
    WHERE employee_id = p_emp_id;
    
    COMMIT;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20001, 'Employee not found');
END;
/

-- PostgreSQL PL/pgSQL
CREATE OR REPLACE FUNCTION update_salary(
    p_emp_id INTEGER,
    p_increase NUMERIC
) RETURNS VOID AS $$
DECLARE
    v_current_salary NUMERIC;
BEGIN
    SELECT salary INTO v_current_salary
    FROM employees
    WHERE employee_id = p_emp_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Employee not found';
    END IF;
    
    UPDATE employees
    SET salary = salary + p_increase
    WHERE employee_id = p_emp_id;
END;
$$ LANGUAGE plpgsql;
```

### Sequence Handling
Oracle sequences need conversion with proper starting values.

**CRITICAL:** When migrating sequences, always set START WITH to Oracle's current LAST_NUMBER value to avoid primary key conflicts with existing data.

**Oracle:**
```sql
CREATE SEQUENCE emp_seq START WITH 1 INCREMENT BY 1;
SELECT emp_seq.NEXTVAL FROM DUAL;

-- Check current sequence value
SELECT sequence_name, last_number FROM user_sequences;
```

**PostgreSQL:**
```sql
-- MUST use Oracle's last_number as START WITH value
CREATE SEQUENCE emp_seq START WITH 207 INCREMENT BY 1;
SELECT nextval('emp_seq');

-- Or use SERIAL/IDENTITY columns
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);
```

**Migration Best Practice:**
1. Extract Oracle sequence metadata including `last_number` and `max_value`
2. Generate PostgreSQL CREATE SEQUENCE with `START WITH <last_number>`
3. Cap MAXVALUE to PostgreSQL's BIGINT limit (9,223,372,036,854,775,807)
4. This ensures new records don't conflict with migrated data
5. Example: If Oracle sequence is at 207, PostgreSQL sequence must start at 207

**Common Mistakes:**
❌ Creating sequences without START WITH → starts at 1 → conflicts with existing data
❌ Using Oracle's MAXVALUE directly → exceeds PostgreSQL BIGINT limit → "value is out of range" error
✅ Creating sequences with START WITH <last_number> → continues from Oracle's value
✅ Capping MAXVALUE to 9,223,372,036,854,775,807 → within PostgreSQL limits

**MAXVALUE Handling:**
Oracle allows MAXVALUE up to 10^28, but PostgreSQL sequences use BIGINT (max: 9,223,372,036,854,775,807).
Always cap Oracle's MAXVALUE to PostgreSQL's limit:

```python
pg_max = 9223372036854775807  # PostgreSQL BIGINT max
if oracle_max_value > pg_max:
    max_value = pg_max
    logger.warning(f"Capping MAXVALUE to PostgreSQL limit")
```

### DUAL Table
Oracle's DUAL table is not needed in PostgreSQL.

**Conversion:**
```sql
-- Oracle
SELECT SYSDATE FROM DUAL;
SELECT user_seq.NEXTVAL FROM DUAL;

-- PostgreSQL
SELECT CURRENT_TIMESTAMP;
SELECT nextval('user_seq');
```

### Date/Time Functions
Oracle date functions need conversion.

| Oracle | PostgreSQL |
|--------|-----------|
| SYSDATE | CURRENT_TIMESTAMP |
| TRUNC(date) | DATE_TRUNC('day', timestamp) |
| ADD_MONTHS(date, n) | date + INTERVAL 'n months' |
| MONTHS_BETWEEN(d1, d2) | EXTRACT(YEAR FROM AGE(d1, d2)) * 12 + EXTRACT(MONTH FROM AGE(d1, d2)) |
| TO_CHAR(date, format) | TO_CHAR(timestamp, format) |

### String Functions
Oracle string functions conversion.

| Oracle | PostgreSQL |
|--------|-----------|
| NVL(expr1, expr2) | COALESCE(expr1, expr2) |
| NVL2(expr, val1, val2) | CASE WHEN expr IS NOT NULL THEN val1 ELSE val2 END |
| DECODE(expr, search, result, ..., default) | CASE expr WHEN search THEN result ... ELSE default END |
| SUBSTR(string, start, length) | SUBSTRING(string FROM start FOR length) |
| INSTR(string, substring) | POSITION(substring IN string) |
| LENGTH(string) | LENGTH(string) or CHAR_LENGTH(string) |
| CONCAT(str1, str2) | str1 \|\| str2 or CONCAT(str1, str2) |

### Outer Join Syntax
Oracle's (+) syntax needs conversion to ANSI joins.

```sql
-- Oracle
SELECT e.name, d.dept_name
FROM employees e, departments d
WHERE e.dept_id = d.dept_id(+);

-- PostgreSQL
SELECT e.name, d.dept_name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.dept_id;
```

### Hierarchical Queries
Oracle's CONNECT BY needs conversion to recursive CTEs.

```sql
-- Oracle
SELECT employee_id, manager_id, name, LEVEL
FROM employees
START WITH manager_id IS NULL
CONNECT BY PRIOR employee_id = manager_id;

-- PostgreSQL
WITH RECURSIVE emp_hierarchy AS (
    SELECT employee_id, manager_id, name, 1 as level
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    SELECT e.employee_id, e.manager_id, e.name, eh.level + 1
    FROM employees e
    JOIN emp_hierarchy eh ON e.manager_id = eh.employee_id
)
SELECT * FROM emp_hierarchy;
```

### Partitioning
Oracle partitioning syntax differs from PostgreSQL.

**Oracle:**
```sql
CREATE TABLE sales (
    sale_id NUMBER,
    sale_date DATE,
    amount NUMBER
)
PARTITION BY RANGE (sale_date) (
    PARTITION p2023 VALUES LESS THAN (TO_DATE('2024-01-01', 'YYYY-MM-DD')),
    PARTITION p2024 VALUES LESS THAN (TO_DATE('2025-01-01', 'YYYY-MM-DD'))
);
```

**PostgreSQL:**
```sql
CREATE TABLE sales (
    sale_id INTEGER,
    sale_date DATE,
    amount NUMERIC
) PARTITION BY RANGE (sale_date);

CREATE TABLE sales_2023 PARTITION OF sales
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE sales_2024 PARTITION OF sales
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### Materialized Views
Both support materialized views but with different refresh syntax.

**Oracle:**
```sql
CREATE MATERIALIZED VIEW mv_sales_summary
REFRESH FAST ON COMMIT
AS SELECT ...;

EXEC DBMS_MVIEW.REFRESH('mv_sales_summary');
```

**PostgreSQL:**
```sql
CREATE MATERIALIZED VIEW mv_sales_summary
AS SELECT ...;

REFRESH MATERIALIZED VIEW mv_sales_summary;
-- Or with CONCURRENTLY to avoid locking
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_summary;
```

## Common Oracle Migration Challenges

### 1. NUMBER Data Type
Oracle's NUMBER is flexible but needs careful mapping.

**Decision Tree:**
- NUMBER without precision → NUMERIC
- NUMBER(p,0) where p ≤ 9 → INTEGER
- NUMBER(p,0) where p > 9 → BIGINT
- NUMBER(p,s) where s > 0 → NUMERIC(p,s)

### 2. Empty Strings vs NULL
Oracle treats empty strings as NULL. PostgreSQL distinguishes them.

**Impact:** Queries using `IS NULL` or `IS NOT NULL` may behave differently.

**Solution:** Review and test all NULL-related logic.

### 3. Implicit Type Conversions
Oracle is more permissive with implicit conversions.

**Example:**
```sql
-- Works in Oracle, may fail in PostgreSQL
SELECT * FROM table WHERE number_column = '123';

-- PostgreSQL requires explicit cast
SELECT * FROM table WHERE number_column = '123'::INTEGER;
```

### 4. Case Sensitivity
Oracle is case-insensitive by default (unless quoted).
PostgreSQL is case-sensitive for quoted identifiers.

**Best Practice:** Use consistent lowercase naming or always quote identifiers.

### 5. Transaction Handling
Oracle auto-commits DDL statements. PostgreSQL allows DDL in transactions.

**Advantage:** PostgreSQL allows rollback of schema changes.

## Migration Checklist

- [ ] Identify all PL/SQL packages, procedures, and functions
- [ ] Map Oracle data types to PostgreSQL equivalents
- [ ] Convert DUAL table references
- [ ] Convert date/time functions
- [ ] Convert string functions (NVL, DECODE, etc.)
- [ ] Convert outer join (+) syntax to ANSI joins
- [ ] Convert hierarchical queries to recursive CTEs
- [ ] Review and convert partitioning schemes
- [ ] Convert materialized view refresh logic
- [ ] Test NULL handling differences
- [ ] Review implicit type conversions
- [ ] Standardize identifier casing
- [ ] Convert Oracle-specific hints to PostgreSQL equivalents
- [ ] Review and convert bitmap indexes
- [ ] Test transaction behavior differences

## Performance Considerations

### Statistics
Oracle: `EXEC DBMS_STATS.GATHER_SCHEMA_STATS('schema_name');`
PostgreSQL: `ANALYZE;`

### Explain Plans
Oracle: `EXPLAIN PLAN FOR ...` then `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);`
PostgreSQL: `EXPLAIN ANALYZE ...`

### Index Types
- Oracle bitmap indexes → PostgreSQL GIN or BRIN indexes
- Oracle function-based indexes → PostgreSQL expression indexes
- Oracle reverse key indexes → Consider hash indexes or partitioning

## Tools and Utilities

### Oracle SQL*Loader → PostgreSQL COPY
```sql
-- PostgreSQL COPY is much faster than INSERT
COPY table_name FROM '/path/to/file.csv' WITH (FORMAT csv, HEADER true);
```

### Oracle Data Pump → pg_dump/pg_restore
PostgreSQL's native backup/restore tools.

### ora2pg
Open-source tool for Oracle to PostgreSQL migration.
- Automates schema conversion
- Generates migration reports
- Handles PL/SQL conversion

## Testing Strategy

1. **Unit Tests:** Test individual function conversions
2. **Integration Tests:** Test procedure call chains
3. **Data Validation:** Compare row counts and checksums
4. **Performance Tests:** Compare query execution times
5. **Load Tests:** Test under production-like load
6. **Regression Tests:** Ensure existing functionality works

## Rollback Plan

1. Keep Oracle database running during migration
2. Maintain Oracle backups
3. Document all conversion decisions
4. Have reverse migration scripts ready
5. Plan for DNS/connection string switchback