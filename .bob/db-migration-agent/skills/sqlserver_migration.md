# SQL Server Migration Skills

## Overview
Specialized skills for migrating from Microsoft SQL Server to PostgreSQL and other platforms.

## SQL Server-Specific Features

### T-SQL to PL/pgSQL Conversion

**Key Differences:**
- Variable declaration syntax
- Error handling (TRY/CATCH vs EXCEPTION)
- Cursor syntax
- Temporary tables
- Table variables

**Example Conversion:**
```sql
-- SQL Server T-SQL
CREATE PROCEDURE UpdateEmployeeSalary
    @EmployeeID INT,
    @Increase DECIMAL(10,2)
AS
BEGIN
    DECLARE @CurrentSalary DECIMAL(10,2);
    
    BEGIN TRY
        SELECT @CurrentSalary = Salary
        FROM Employees
        WHERE EmployeeID = @EmployeeID;
        
        IF @CurrentSalary IS NULL
            THROW 50001, 'Employee not found', 1;
        
        UPDATE Employees
        SET Salary = Salary + @Increase
        WHERE EmployeeID = @EmployeeID;
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO

-- PostgreSQL PL/pgSQL
CREATE OR REPLACE FUNCTION update_employee_salary(
    p_employee_id INTEGER,
    p_increase NUMERIC(10,2)
) RETURNS VOID AS $$
DECLARE
    v_current_salary NUMERIC(10,2);
BEGIN
    SELECT salary INTO v_current_salary
    FROM employees
    WHERE employee_id = p_employee_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Employee not found';
    END IF;
    
    UPDATE employees
    SET salary = salary + p_increase
    WHERE employee_id = p_employee_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$ LANGUAGE plpgsql;
```

### Identity Columns
SQL Server IDENTITY maps to PostgreSQL SERIAL or IDENTITY.

**SQL Server:**
```sql
CREATE TABLE Employees (
    EmployeeID INT IDENTITY(1,1) PRIMARY KEY,
    Name VARCHAR(100)
);
```

**PostgreSQL:**
```sql
-- Option 1: SERIAL (traditional)
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    name VARCHAR(100)
);

-- Option 2: IDENTITY (SQL standard, PostgreSQL 10+)
CREATE TABLE employees (
    employee_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100)
);
```

### Square Brackets vs Double Quotes
SQL Server uses square brackets for identifiers.

```sql
-- SQL Server
SELECT [First Name], [Last Name] FROM [Employees];

-- PostgreSQL
SELECT "First Name", "Last Name" FROM "Employees";
```

### TOP vs LIMIT
Different syntax for limiting results.

```sql
-- SQL Server
SELECT TOP 10 * FROM Employees ORDER BY Salary DESC;
SELECT TOP 10 PERCENT * FROM Employees;

-- PostgreSQL
SELECT * FROM employees ORDER BY salary DESC LIMIT 10;
-- No direct PERCENT equivalent, calculate manually
SELECT * FROM employees ORDER BY salary DESC 
LIMIT (SELECT CAST(COUNT(*) * 0.1 AS INTEGER) FROM employees);
```

### Date/Time Functions

| SQL Server | PostgreSQL |
|-----------|-----------|
| GETDATE() | CURRENT_TIMESTAMP |
| GETUTCDATE() | CURRENT_TIMESTAMP AT TIME ZONE 'UTC' |
| DATEADD(day, 7, date) | date + INTERVAL '7 days' |
| DATEDIFF(day, date1, date2) | date2 - date1 |
| YEAR(date) | EXTRACT(YEAR FROM date) |
| MONTH(date) | EXTRACT(MONTH FROM date) |
| DAY(date) | EXTRACT(DAY FROM date) |

### String Functions

| SQL Server | PostgreSQL |
|-----------|-----------|
| ISNULL(expr, value) | COALESCE(expr, value) |
| LEN(string) | LENGTH(string) |
| CHARINDEX(substr, str) | POSITION(substr IN str) |
| STUFF(str, start, len, newstr) | OVERLAY(str PLACING newstr FROM start FOR len) |
| REPLICATE(str, count) | REPEAT(str, count) |
| REVERSE(string) | REVERSE(string) |

### Temporary Tables
Different syntax and behavior.

**SQL Server:**
```sql
-- Local temp table
CREATE TABLE #TempEmployees (
    EmployeeID INT,
    Name VARCHAR(100)
);

-- Global temp table
CREATE TABLE ##GlobalTemp (
    ID INT
);
```

**PostgreSQL:**
```sql
-- Temporary table (session-scoped)
CREATE TEMPORARY TABLE temp_employees (
    employee_id INTEGER,
    name VARCHAR(100)
);

-- Or use TEMP
CREATE TEMP TABLE temp_employees (
    employee_id INTEGER,
    name VARCHAR(100)
);
```

### Table Variables
SQL Server table variables don't have direct PostgreSQL equivalent.

**SQL Server:**
```sql
DECLARE @TempTable TABLE (
    ID INT,
    Name VARCHAR(100)
);

INSERT INTO @TempTable VALUES (1, 'John');
SELECT * FROM @TempTable;
```

**PostgreSQL Alternative:**
```sql
-- Use temporary table
CREATE TEMP TABLE temp_table (
    id INTEGER,
    name VARCHAR(100)
);

INSERT INTO temp_table VALUES (1, 'John');
SELECT * FROM temp_table;
```

### Computed Columns
SQL Server computed columns need conversion.

**SQL Server:**
```sql
CREATE TABLE Orders (
    OrderID INT,
    Quantity INT,
    UnitPrice DECIMAL(10,2),
    TotalPrice AS (Quantity * UnitPrice) PERSISTED
);
```

**PostgreSQL:**
```sql
-- Option 1: Generated column (PostgreSQL 12+)
CREATE TABLE orders (
    order_id INTEGER,
    quantity INTEGER,
    unit_price NUMERIC(10,2),
    total_price NUMERIC(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Option 2: Trigger
CREATE OR REPLACE FUNCTION calculate_total_price()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_price := NEW.quantity * NEW.unit_price;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calculate_total
BEFORE INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION calculate_total_price();
```

### Indexes
Different index types and syntax.

**SQL Server:**
```sql
-- Clustered index (one per table)
CREATE CLUSTERED INDEX IX_Employees_ID ON Employees(EmployeeID);

-- Non-clustered index
CREATE NONCLUSTERED INDEX IX_Employees_Name ON Employees(Name);

-- Included columns
CREATE INDEX IX_Employees_Dept 
ON Employees(DepartmentID) 
INCLUDE (Name, Salary);
```

**PostgreSQL:**
```sql
-- Primary key acts as clustered index
ALTER TABLE employees ADD PRIMARY KEY (employee_id);

-- Regular index (B-tree by default)
CREATE INDEX ix_employees_name ON employees(name);

-- Covering index (include columns)
CREATE INDEX ix_employees_dept 
ON employees(department_id) 
INCLUDE (name, salary);
```

### Full-Text Search
Different implementations.

**SQL Server:**
```sql
CREATE FULLTEXT INDEX ON Documents(Content)
KEY INDEX PK_Documents;

SELECT * FROM Documents
WHERE CONTAINS(Content, 'search term');
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

### Schemas
Both support schemas but with different defaults.

**SQL Server:**
- Default schema: dbo
- Schema ownership model

**PostgreSQL:**
- Default schema: public
- Simpler schema model

### Transactions and Locking
Different isolation levels and locking hints.

**SQL Server:**
```sql
-- Locking hints
SELECT * FROM Employees WITH (NOLOCK);
SELECT * FROM Employees WITH (UPDLOCK);

-- Isolation levels
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
```

**PostgreSQL:**
```sql
-- No locking hints, use transaction isolation
BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
-- Note: PostgreSQL treats READ UNCOMMITTED as READ COMMITTED

-- For explicit locking
SELECT * FROM employees FOR UPDATE;
SELECT * FROM employees FOR SHARE;
```

## Data Type Mappings

| SQL Server | PostgreSQL | Notes |
|-----------|-----------|-------|
| INT | INTEGER | |
| BIGINT | BIGINT | |
| SMALLINT | SMALLINT | |
| TINYINT | SMALLINT | PostgreSQL has no TINYINT |
| BIT | BOOLEAN | |
| DECIMAL(p,s) | NUMERIC(p,s) | |
| MONEY | NUMERIC(19,4) | |
| FLOAT | DOUBLE PRECISION | |
| REAL | REAL | |
| VARCHAR(n) | VARCHAR(n) | |
| NVARCHAR(n) | VARCHAR(n) | PostgreSQL is Unicode by default |
| CHAR(n) | CHAR(n) | |
| TEXT | TEXT | |
| NTEXT | TEXT | |
| DATETIME | TIMESTAMP | |
| DATETIME2 | TIMESTAMP | |
| DATE | DATE | |
| TIME | TIME | |
| DATETIMEOFFSET | TIMESTAMP WITH TIME ZONE | |
| UNIQUEIDENTIFIER | UUID | |
| BINARY(n) | BYTEA | |
| VARBINARY(n) | BYTEA | |
| IMAGE | BYTEA | |
| XML | XML | |

## Common Migration Challenges

### 1. Case Sensitivity
SQL Server is case-insensitive by default (depends on collation).
PostgreSQL is case-sensitive for quoted identifiers.

**Solution:** Standardize on lowercase or always quote identifiers.

### 2. NULL Concatenation
SQL Server: NULL + 'text' = NULL
PostgreSQL: NULL || 'text' = NULL (same behavior)

But SQL Server has SET CONCAT_NULL_YIELDS_NULL option.

### 3. Empty Strings
SQL Server distinguishes empty strings from NULL.
PostgreSQL also distinguishes them (unlike Oracle).

### 4. Implicit Conversions
SQL Server is more permissive with implicit type conversions.

**Example:**
```sql
-- Works in SQL Server
SELECT * FROM table WHERE int_column = '123';

-- PostgreSQL requires explicit cast
SELECT * FROM table WHERE int_column = '123'::INTEGER;
```

### 5. Stored Procedure Return Values
SQL Server procedures can return values directly.
PostgreSQL functions return values, procedures don't.

**SQL Server:**
```sql
CREATE PROCEDURE GetEmployeeCount
AS
BEGIN
    RETURN (SELECT COUNT(*) FROM Employees);
END;
```

**PostgreSQL:**
```sql
CREATE FUNCTION get_employee_count()
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM employees);
END;
$$ LANGUAGE plpgsql;
```

## Migration Checklist

- [ ] Convert T-SQL procedures to PL/pgSQL functions
- [ ] Map IDENTITY columns to SERIAL or IDENTITY
- [ ] Convert square brackets to double quotes
- [ ] Convert TOP to LIMIT
- [ ] Convert date/time functions
- [ ] Convert string functions (ISNULL, CHARINDEX, etc.)
- [ ] Convert temporary tables and table variables
- [ ] Convert computed columns to generated columns or triggers
- [ ] Convert clustered/non-clustered indexes
- [ ] Convert full-text search implementation
- [ ] Review transaction isolation levels
- [ ] Test NULL handling
- [ ] Review implicit type conversions
- [ ] Convert stored procedure return values
- [ ] Test error handling (TRY/CATCH vs EXCEPTION)

## Performance Considerations

### Statistics
SQL Server: `UPDATE STATISTICS table_name;`
PostgreSQL: `ANALYZE table_name;`

### Execution Plans
SQL Server: `SET SHOWPLAN_ALL ON;` or SQL Server Management Studio
PostgreSQL: `EXPLAIN ANALYZE query;`

### Index Maintenance
SQL Server: `ALTER INDEX ALL ON table_name REBUILD;`
PostgreSQL: `REINDEX TABLE table_name;`

## Tools

### SQL Server Integration Services (SSIS)
For ETL, consider PostgreSQL alternatives:
- Apache Airflow
- Talend
- Custom Python scripts

### SQL Server Management Studio (SSMS)
PostgreSQL alternatives:
- pgAdmin
- DBeaver
- DataGrip

### bcp Utility
SQL Server's bulk copy utility.
PostgreSQL equivalent: `COPY` command or `\copy` in psql.

## Testing Strategy

1. **Schema Validation:** Verify all objects created correctly
2. **Data Validation:** Compare row counts and data samples
3. **Procedure Testing:** Test all converted procedures/functions
4. **Performance Testing:** Compare query execution times
5. **Integration Testing:** Test with applications
6. **Load Testing:** Test under production-like load

## Rollback Plan

1. Maintain SQL Server database during migration
2. Keep SQL Server backups
3. Document all conversion decisions
4. Have connection string switchback plan
5. Test rollback procedures