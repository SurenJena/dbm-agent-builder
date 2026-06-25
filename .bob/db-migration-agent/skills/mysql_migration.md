# MySQL Migration Skills

## Overview
Specialized skills for migrating from MySQL to PostgreSQL and other platforms.

## MySQL-Specific Features

### Storage Engines
MySQL supports multiple storage engines with different characteristics.

**Common Engines:**
- **InnoDB:** ACID-compliant, supports transactions and foreign keys
- **MyISAM:** Non-transactional, no foreign key support
- **Memory:** In-memory tables

**PostgreSQL:** Single storage engine with ACID compliance and full feature support.

**Migration Impact:**
- MyISAM tables need careful handling (no transaction support)
- Memory tables → PostgreSQL UNLOGGED or TEMPORARY tables
- InnoDB → Direct migration

### AUTO_INCREMENT to SERIAL

**MySQL:**
```sql
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100)
);
```

**PostgreSQL:**
```sql
-- Option 1: SERIAL
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);

-- Option 2: IDENTITY (PostgreSQL 10+)
CREATE TABLE employees (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100)
);
```

### Backticks to Double Quotes

**MySQL:**
```sql
SELECT `first name`, `last name` FROM `employees`;
```

**PostgreSQL:**
```sql
SELECT "first name", "last name" FROM "employees";
```

### LIMIT Syntax Differences

**MySQL:**
```sql
-- LIMIT with offset
SELECT * FROM employees LIMIT 10, 20;  -- Skip 10, return 20
```

**PostgreSQL:**
```sql
-- LIMIT OFFSET syntax
SELECT * FROM employees LIMIT 20 OFFSET 10;
```

### Date/Time Functions

| MySQL | PostgreSQL |
|-------|-----------|
| NOW() | CURRENT_TIMESTAMP or NOW() |
| CURDATE() | CURRENT_DATE |
| CURTIME() | CURRENT_TIME |
| DATE_ADD(date, INTERVAL n DAY) | date + INTERVAL 'n days' |
| DATE_SUB(date, INTERVAL n DAY) | date - INTERVAL 'n days' |
| DATEDIFF(date1, date2) | date1 - date2 |
| YEAR(date) | EXTRACT(YEAR FROM date) |
| MONTH(date) | EXTRACT(MONTH FROM date) |
| DAY(date) | EXTRACT(DAY FROM date) |
| DATE_FORMAT(date, format) | TO_CHAR(date, format) |

### String Functions

| MySQL | PostgreSQL |
|-------|-----------|
| CONCAT(str1, str2, ...) | CONCAT(str1, str2, ...) or str1 \|\| str2 |
| CONCAT_WS(sep, str1, str2) | CONCAT_WS(sep, str1, str2) |
| LENGTH(string) | LENGTH(string) or CHAR_LENGTH(string) |
| LOCATE(substr, str) | POSITION(substr IN str) |
| SUBSTRING(str, pos, len) | SUBSTRING(str FROM pos FOR len) |
| REPLACE(str, from, to) | REPLACE(str, from, to) |
| LOWER(string) | LOWER(string) |
| UPPER(string) | UPPER(string) |
| TRIM(string) | TRIM(string) |

### ENUM Type
MySQL ENUM needs special handling.

**MySQL:**
```sql
CREATE TABLE users (
    id INT,
    status ENUM('active', 'inactive', 'pending')
);
```

**PostgreSQL Options:**

**Option 1: PostgreSQL ENUM**
```sql
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'pending');

CREATE TABLE users (
    id INTEGER,
    status user_status
);
```

**Option 2: VARCHAR with CHECK constraint**
```sql
CREATE TABLE users (
    id INTEGER,
    status VARCHAR(20) CHECK (status IN ('active', 'inactive', 'pending'))
);
```

### TINYINT(1) as Boolean

**MySQL:**
```sql
CREATE TABLE settings (
    id INT,
    is_enabled TINYINT(1)  -- Used as boolean
);
```

**PostgreSQL:**
```sql
CREATE TABLE settings (
    id INTEGER,
    is_enabled BOOLEAN
);
```

### UNSIGNED Integers
MySQL supports UNSIGNED integers, PostgreSQL doesn't.

**MySQL:**
```sql
CREATE TABLE counters (
    id INT UNSIGNED,
    count BIGINT UNSIGNED
);
```

**PostgreSQL:**
```sql
-- Use larger signed type or CHECK constraint
CREATE TABLE counters (
    id BIGINT CHECK (id >= 0),
    count NUMERIC(20,0) CHECK (count >= 0)
);

-- Or just use signed types if range is sufficient
CREATE TABLE counters (
    id INTEGER,
    count BIGINT
);
```

### INSERT ... ON DUPLICATE KEY UPDATE
MySQL's upsert syntax needs conversion.

**MySQL:**
```sql
INSERT INTO users (id, name, email)
VALUES (1, 'John', 'john@example.com')
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    email = VALUES(email);
```

**PostgreSQL:**
```sql
INSERT INTO users (id, name, email)
VALUES (1, 'John', 'john@example.com')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email;
```

### REPLACE Statement
MySQL REPLACE needs conversion.

**MySQL:**
```sql
REPLACE INTO users (id, name) VALUES (1, 'John');
```

**PostgreSQL:**
```sql
-- Use INSERT ... ON CONFLICT
INSERT INTO users (id, name) VALUES (1, 'John')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
```

### GROUP_CONCAT
MySQL's GROUP_CONCAT needs conversion.

**MySQL:**
```sql
SELECT dept_id, GROUP_CONCAT(name ORDER BY name SEPARATOR ', ')
FROM employees
GROUP BY dept_id;
```

**PostgreSQL:**
```sql
SELECT dept_id, STRING_AGG(name, ', ' ORDER BY name)
FROM employees
GROUP BY dept_id;
```

### IF Function
MySQL's IF function needs conversion.

**MySQL:**
```sql
SELECT IF(salary > 50000, 'High', 'Low') FROM employees;
```

**PostgreSQL:**
```sql
SELECT CASE WHEN salary > 50000 THEN 'High' ELSE 'Low' END FROM employees;
```

### IFNULL Function

**MySQL:**
```sql
SELECT IFNULL(column, 'default') FROM table;
```

**PostgreSQL:**
```sql
SELECT COALESCE(column, 'default') FROM table;
```

### Full-Text Search
Different implementations.

**MySQL:**
```sql
CREATE FULLTEXT INDEX ft_content ON documents(content);

SELECT * FROM documents
WHERE MATCH(content) AGAINST('search term' IN NATURAL LANGUAGE MODE);
```

**PostgreSQL:**
```sql
-- Add tsvector column
ALTER TABLE documents ADD COLUMN content_tsv tsvector;

-- Create GIN index
CREATE INDEX idx_documents_fts ON documents USING GIN(content_tsv);

-- Update tsvector
UPDATE documents SET content_tsv = to_tsvector('english', content);

-- Search
SELECT * FROM documents
WHERE content_tsv @@ to_tsquery('english', 'search & term');
```

### Stored Procedures
MySQL procedures need conversion to PostgreSQL functions.

**MySQL:**
```sql
DELIMITER //
CREATE PROCEDURE GetEmployeeCount(OUT emp_count INT)
BEGIN
    SELECT COUNT(*) INTO emp_count FROM employees;
END //
DELIMITER ;

CALL GetEmployeeCount(@count);
SELECT @count;
```

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION get_employee_count()
RETURNS INTEGER AS $$
DECLARE
    emp_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO emp_count FROM employees;
    RETURN emp_count;
END;
$$ LANGUAGE plpgsql;

SELECT get_employee_count();
```

### Triggers
Similar but with syntax differences.

**MySQL:**
```sql
DELIMITER //
CREATE TRIGGER before_employee_update
BEFORE UPDATE ON employees
FOR EACH ROW
BEGIN
    SET NEW.updated_at = NOW();
END //
DELIMITER ;
```

**PostgreSQL:**
```sql
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_employee_update
BEFORE UPDATE ON employees
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();
```

## Data Type Mappings

| MySQL | PostgreSQL | Notes |
|-------|-----------|-------|
| INT | INTEGER | |
| BIGINT | BIGINT | |
| SMALLINT | SMALLINT | |
| TINYINT | SMALLINT | PostgreSQL has no TINYINT |
| TINYINT(1) | BOOLEAN | When used as boolean |
| DECIMAL(p,s) | NUMERIC(p,s) | |
| FLOAT | REAL | |
| DOUBLE | DOUBLE PRECISION | |
| VARCHAR(n) | VARCHAR(n) | |
| CHAR(n) | CHAR(n) | |
| TEXT | TEXT | |
| TINYTEXT | TEXT | |
| MEDIUMTEXT | TEXT | |
| LONGTEXT | TEXT | |
| BLOB | BYTEA | |
| TINYBLOB | BYTEA | |
| MEDIUMBLOB | BYTEA | |
| LONGBLOB | BYTEA | |
| DATE | DATE | |
| DATETIME | TIMESTAMP | |
| TIMESTAMP | TIMESTAMP WITH TIME ZONE | |
| TIME | TIME | |
| YEAR | SMALLINT | |
| ENUM | ENUM or VARCHAR with CHECK | |
| SET | ARRAY or separate table | |
| JSON | JSON or JSONB | JSONB recommended |

## Common Migration Challenges

### 1. Case Sensitivity
MySQL case sensitivity depends on operating system:
- Windows: Case-insensitive
- Linux: Case-sensitive for table names

PostgreSQL: Case-sensitive for quoted identifiers.

**Solution:** Standardize on lowercase naming.

### 2. Zero Dates
MySQL allows '0000-00-00' as a date value.
PostgreSQL doesn't allow invalid dates.

**Solution:** Convert to NULL or valid date during migration.

### 3. String Comparison
MySQL string comparison is case-insensitive by default (depends on collation).
PostgreSQL is case-sensitive.

**MySQL:**
```sql
SELECT * FROM users WHERE name = 'john';  -- Matches 'John', 'JOHN', etc.
```

**PostgreSQL:**
```sql
SELECT * FROM users WHERE name = 'john';  -- Only matches 'john'
SELECT * FROM users WHERE LOWER(name) = 'john';  -- Case-insensitive
```

### 4. Division by Zero
MySQL returns NULL for division by zero (with warning).
PostgreSQL raises an error.

**Solution:** Add explicit checks:
```sql
SELECT CASE WHEN divisor = 0 THEN NULL ELSE dividend / divisor END;
```

### 5. Empty Strings vs NULL
Both MySQL and PostgreSQL distinguish empty strings from NULL.
But MySQL's CONCAT behavior differs:

**MySQL:** CONCAT with NULL returns NULL
**PostgreSQL:** CONCAT with NULL returns the non-NULL values

### 6. AUTO_INCREMENT Behavior
MySQL AUTO_INCREMENT continues from max value even after deletions.
PostgreSQL SERIAL sequences continue from last generated value.

**Impact:** May have gaps in sequence after migration.

## Migration Checklist

- [ ] Identify storage engines (InnoDB, MyISAM, Memory)
- [ ] Convert AUTO_INCREMENT to SERIAL or IDENTITY
- [ ] Convert backticks to double quotes
- [ ] Convert LIMIT offset syntax
- [ ] Convert date/time functions
- [ ] Convert string functions
- [ ] Handle ENUM types
- [ ] Convert TINYINT(1) to BOOLEAN
- [ ] Handle UNSIGNED integers
- [ ] Convert INSERT ... ON DUPLICATE KEY UPDATE
- [ ] Convert REPLACE statements
- [ ] Convert GROUP_CONCAT to STRING_AGG
- [ ] Convert IF function to CASE
- [ ] Convert IFNULL to COALESCE
- [ ] Convert full-text search
- [ ] Convert stored procedures
- [ ] Convert triggers
- [ ] Handle zero dates
- [ ] Review string comparison (case sensitivity)
- [ ] Test division by zero handling

## Performance Considerations

### MyISAM to InnoDB/PostgreSQL
MyISAM tables don't support transactions. Consider:
- Batch operations for better performance
- Add appropriate indexes
- Test concurrent access patterns

### Index Types
MySQL supports various index types:
- B-tree (default)
- Hash (Memory engine)
- Full-text
- Spatial

PostgreSQL equivalents:
- B-tree (default)
- Hash
- GIN (for full-text)
- GiST (for spatial)

### Query Cache
MySQL has query cache (deprecated in 8.0).
PostgreSQL doesn't have query cache but has better query planning.

## Tools

### mysqldump
MySQL's backup utility.

**Export:**
```bash
mysqldump -u user -p database > backup.sql
```

**Import to PostgreSQL:**
Requires conversion of SQL syntax.

### MySQL Workbench
MySQL's GUI tool.

PostgreSQL alternatives:
- pgAdmin
- DBeaver
- DataGrip

### pgloader
Specialized tool for MySQL to PostgreSQL migration:
```bash
pgloader mysql://user:pass@localhost/mydb postgresql://user:pass@localhost/pgdb
```

Features:
- Automatic schema conversion
- Data type mapping
- Parallel loading
- Progress reporting

## Testing Strategy

1. **Schema Validation:** Verify all tables, indexes, constraints
2. **Data Validation:** Compare row counts and data samples
3. **Procedure Testing:** Test all converted procedures/functions
4. **Trigger Testing:** Verify trigger behavior
5. **Performance Testing:** Compare query execution times
6. **Character Set Testing:** Verify UTF-8 handling
7. **Case Sensitivity Testing:** Test string comparisons
8. **Integration Testing:** Test with applications

## Rollback Plan

1. Keep MySQL database running during migration
2. Maintain MySQL backups
3. Document all conversion decisions
4. Have connection string switchback plan
5. Test rollback procedures before production migration