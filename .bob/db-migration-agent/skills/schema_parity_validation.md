# Schema Parity Validation Skills

## Overview
Comprehensive validation methodology to ensure 100% schema parity between source and target databases after migration.

## Validation Objectives

1. **Object Count Parity** - Verify all objects migrated
2. **Object Configuration Parity** - Verify objects configured correctly
3. **Data Integrity Parity** - Verify constraints and relationships preserved
4. **Performance Parity** - Verify indexes and statistics in place

## Validation Checklist

### 1. Tables
- [ ] Count matches source
- [ ] All columns present
- [ ] Data types correctly converted
- [ ] NOT NULL constraints preserved
- [ ] Default values converted

### 2. Sequences
- [ ] Count matches source
- [ ] START WITH values match source last_number
- [ ] INCREMENT BY values match
- [ ] MAXVALUE within target database limits
- [ ] MINVALUE preserved
- [ ] CACHE settings appropriate

### 3. Indexes
- [ ] Count matches source (excluding constraint-backing indexes)
- [ ] Column order preserved
- [ ] ASC/DESC order preserved
- [ ] Unique indexes identified
- [ ] Partial indexes converted (if applicable)

### 4. Constraints
- [ ] Primary key count matches
- [ ] Foreign key count matches
- [ ] Unique constraint count matches
- [ ] Check constraint count matches
- [ ] All constraints ACTIVE (not disabled)
- [ ] Referential integrity preserved

### 5. Views
- [ ] Count matches source
- [ ] View definitions converted
- [ ] Dependencies resolved
- [ ] Materialized views handled

### 6. Triggers
- [ ] Count matches source
- [ ] Trigger logic converted
- [ ] Trigger timing preserved (BEFORE/AFTER)
- [ ] Trigger events preserved (INSERT/UPDATE/DELETE)

### 7. Stored Procedures/Functions
- [ ] Count matches source
- [ ] Logic converted to target dialect
- [ ] Parameters preserved
- [ ] Return types converted

## Validation SQL Queries

### Oracle Object Count Query

```sql
SELECT object_type, object_count FROM (
  SELECT 'TABLES' AS object_type, COUNT(*) AS object_count FROM user_tables
  UNION ALL
  SELECT 'VIEWS', COUNT(*) FROM user_views
  UNION ALL
  SELECT 'MATERIALIZED VIEWS', COUNT(*) FROM user_mviews
  UNION ALL
  SELECT 'SEQUENCES', COUNT(*) FROM user_sequences
  UNION ALL
  SELECT 'INDEXES', COUNT(*) FROM user_indexes 
    WHERE index_name NOT IN (
      SELECT constraint_name FROM user_constraints 
      WHERE constraint_type IN ('P','U')
    )
  UNION ALL
  SELECT 'CONSTRAINTS', COUNT(*) FROM user_constraints
  UNION ALL
  SELECT 'TRIGGERS', COUNT(*) FROM user_triggers
  UNION ALL
  SELECT 'PROCEDURES', COUNT(*) FROM user_procedures WHERE object_type = 'PROCEDURE'
  UNION ALL
  SELECT 'FUNCTIONS', COUNT(*) FROM user_procedures WHERE object_type = 'FUNCTION'
  UNION ALL
  SELECT 'PACKAGES', COUNT(*) FROM user_procedures WHERE object_type = 'PACKAGE'
)
ORDER BY object_type;
```

### PostgreSQL Object Count Query

```sql
SELECT object_type, COUNT(*) AS object_count FROM (
  SELECT 'TABLES' AS object_type FROM pg_tables WHERE schemaname = 'target_schema'
  UNION ALL
  SELECT 'VIEWS' FROM pg_views WHERE schemaname = 'target_schema'
  UNION ALL
  SELECT 'MATERIALIZED VIEWS' FROM pg_matviews WHERE schemaname = 'target_schema'
  UNION ALL
  SELECT 'SEQUENCES' FROM pg_sequences WHERE schemaname = 'target_schema'
  UNION ALL
  SELECT 'INDEXES' FROM pg_indexes WHERE schemaname = 'target_schema' 
    AND indexname NOT IN (
      SELECT conname FROM pg_constraint 
      WHERE contype IN ('p','u') 
      AND connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'target_schema')
    )
  UNION ALL
  SELECT 'CONSTRAINTS' FROM pg_constraint 
    WHERE connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'target_schema')
  UNION ALL
  SELECT 'TRIGGERS' FROM pg_trigger t 
    JOIN pg_class c ON t.tgrelid = c.oid 
    JOIN pg_namespace n ON c.relnamespace = n.oid 
    WHERE n.nspname = 'target_schema' AND NOT t.tgisinternal
  UNION ALL
  SELECT 'FUNCTIONS' FROM pg_proc p 
    JOIN pg_namespace n ON p.pronamespace = n.oid 
    WHERE n.nspname = 'target_schema' AND p.prokind = 'f'
  UNION ALL
  SELECT 'PROCEDURES' FROM pg_proc p 
    JOIN pg_namespace n ON p.pronamespace = n.oid 
    WHERE n.nspname = 'target_schema' AND p.prokind = 'p'
) x
GROUP BY object_type
ORDER BY object_type;
```

### SQL Server Object Count Query

```sql
SELECT object_type, COUNT(*) AS object_count FROM (
  SELECT 'TABLES' AS object_type FROM sys.tables WHERE schema_id = SCHEMA_ID('target_schema')
  UNION ALL
  SELECT 'VIEWS' FROM sys.views WHERE schema_id = SCHEMA_ID('target_schema')
  UNION ALL
  SELECT 'SEQUENCES' FROM sys.sequences WHERE schema_id = SCHEMA_ID('target_schema')
  UNION ALL
  SELECT 'INDEXES' FROM sys.indexes i 
    JOIN sys.tables t ON i.object_id = t.object_id
    WHERE t.schema_id = SCHEMA_ID('target_schema') 
    AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
  UNION ALL
  SELECT 'CONSTRAINTS' FROM sys.objects 
    WHERE schema_id = SCHEMA_ID('target_schema') 
    AND type IN ('PK','F','UQ','C')
  UNION ALL
  SELECT 'TRIGGERS' FROM sys.triggers t
    JOIN sys.tables tb ON t.parent_id = tb.object_id
    WHERE tb.schema_id = SCHEMA_ID('target_schema')
  UNION ALL
  SELECT 'PROCEDURES' FROM sys.procedures WHERE schema_id = SCHEMA_ID('target_schema')
  UNION ALL
  SELECT 'FUNCTIONS' FROM sys.objects 
    WHERE schema_id = SCHEMA_ID('target_schema') 
    AND type IN ('FN','IF','TF')
) x
GROUP BY object_type
ORDER BY object_type;
```

### MySQL Object Count Query

```sql
SELECT object_type, COUNT(*) AS object_count FROM (
  SELECT 'TABLES' AS object_type FROM information_schema.tables 
    WHERE table_schema = 'target_schema' AND table_type = 'BASE TABLE'
  UNION ALL
  SELECT 'VIEWS' FROM information_schema.views WHERE table_schema = 'target_schema'
  UNION ALL
  SELECT 'INDEXES' FROM information_schema.statistics 
    WHERE table_schema = 'target_schema' 
    AND index_name NOT IN ('PRIMARY')
  UNION ALL
  SELECT 'CONSTRAINTS' FROM information_schema.table_constraints 
    WHERE table_schema = 'target_schema'
  UNION ALL
  SELECT 'TRIGGERS' FROM information_schema.triggers WHERE trigger_schema = 'target_schema'
  UNION ALL
  SELECT 'PROCEDURES' FROM information_schema.routines 
    WHERE routine_schema = 'target_schema' AND routine_type = 'PROCEDURE'
  UNION ALL
  SELECT 'FUNCTIONS' FROM information_schema.routines 
    WHERE routine_schema = 'target_schema' AND routine_type = 'FUNCTION'
) x
GROUP BY object_type
ORDER BY object_type;
```

## Discrepancy Analysis

### Common Discrepancies and Resolutions

#### 1. Missing Sequences
**Symptom:** Sequence count mismatch  
**Cause:** Sequences not created or creation failed  
**Resolution:**
```sql
-- Generate missing sequences
CREATE SEQUENCE sequence_name 
  START WITH <oracle_last_number>
  INCREMENT BY <increment_value>
  MAXVALUE 9223372036854775807;
```

#### 2. Missing Indexes
**Symptom:** Index count mismatch  
**Cause:** Index creation failed or skipped  
**Resolution:**
```sql
-- Regenerate missing indexes
CREATE INDEX index_name ON table_name (column1, column2);
```

#### 3. Disabled Constraints
**Symptom:** Constraints exist but not enforced  
**Cause:** Constraint validation failed during creation  
**Resolution:**
```sql
-- Enable constraints
ALTER TABLE table_name ENABLE CONSTRAINT constraint_name;
-- Or recreate if needed
ALTER TABLE table_name ADD CONSTRAINT constraint_name ...;
```

#### 4. Incorrect Sequence Starting Values
**Symptom:** Sequence exists but starts at 1  
**Cause:** START WITH clause not included  
**Resolution:**
```sql
-- Drop and recreate with correct START WITH
DROP SEQUENCE sequence_name;
CREATE SEQUENCE sequence_name START WITH <correct_value> ...;
```

#### 5. Missing Views
**Symptom:** View count mismatch  
**Cause:** View dependencies not resolved or SQL conversion failed  
**Resolution:**
- Resolve view dependencies (create in correct order)
- Convert Oracle-specific SQL to target dialect
- Recreate views

## Validation Report Template

```markdown
# Schema Parity Validation Report

## Executive Summary
- Migration Status: [COMPLETE PARITY / DISCREPANCIES FOUND]
- Total Objects Migrated: X/Y
- Discrepancies: N

## Object Count Comparison

| Object Type | Source | Target | Status | Notes |
|------------|--------|--------|--------|-------|
| TABLES     | X      | Y      | ✅/❌  |       |
| SEQUENCES  | X      | Y      | ✅/❌  |       |
| ...        | ...    | ...    | ...    | ...   |

## Detailed Findings

### Tables
- [List of tables with status]

### Sequences
- [List of sequences with START WITH validation]

### Constraints
- [List of constraints with active/disabled status]

## Discrepancies Found

### 1. [Discrepancy Type]
- **Object:** [object_name]
- **Issue:** [description]
- **Resolution:** [SQL script or action]

## Corrective Actions Taken

1. [Action 1]
2. [Action 2]

## Final Validation

After corrections:
- All object counts match: ✅
- All sequences have correct START WITH: ✅
- All constraints active: ✅
- All indexes present: ✅

## Conclusion

[Summary of migration quality and readiness]
```

## Automation Script Template

```python
#!/usr/bin/env python3
"""
Schema Parity Validation Script
Compares source and target database schemas
"""

import psycopg2
import cx_Oracle
from typing import Dict, List

class SchemaParityValidator:
    def __init__(self, source_conn, target_conn):
        self.source_conn = source_conn
        self.target_conn = target_conn
        self.discrepancies = []
    
    def get_object_counts(self, conn, db_type: str) -> Dict[str, int]:
        """Get object counts from database"""
        if db_type == 'oracle':
            return self._get_oracle_counts(conn)
        elif db_type == 'postgresql':
            return self._get_postgresql_counts(conn)
    
    def compare_counts(self, source_counts: Dict, target_counts: Dict) -> List[Dict]:
        """Compare object counts and identify discrepancies"""
        discrepancies = []
        for obj_type in source_counts:
            if source_counts[obj_type] != target_counts.get(obj_type, 0):
                discrepancies.append({
                    'object_type': obj_type,
                    'source_count': source_counts[obj_type],
                    'target_count': target_counts.get(obj_type, 0),
                    'difference': source_counts[obj_type] - target_counts.get(obj_type, 0)
                })
        return discrepancies
    
    def generate_report(self, discrepancies: List[Dict]) -> str:
        """Generate validation report"""
        if not discrepancies:
            return "✅ COMPLETE PARITY ACHIEVED - No discrepancies found"
        
        report = "❌ DISCREPANCIES FOUND:\n\n"
        for disc in discrepancies:
            report += f"- {disc['object_type']}: "
            report += f"Source={disc['source_count']}, "
            report += f"Target={disc['target_count']}, "
            report += f"Difference={disc['difference']}\n"
        
        return report
    
    def validate(self) -> bool:
        """Run complete validation"""
        source_counts = self.get_object_counts(self.source_conn, 'oracle')
        target_counts = self.get_object_counts(self.target_conn, 'postgresql')
        
        self.discrepancies = self.compare_counts(source_counts, target_counts)
        
        report = self.generate_report(self.discrepancies)
        print(report)
        
        return len(self.discrepancies) == 0
```

## Best Practices

1. **Always Validate After Migration** - Never skip validation
2. **Validate Multiple Times** - After schema creation, after data load, after index creation
3. **Document Everything** - Generate detailed reports
4. **Automate Validation** - Use scripts for consistency
5. **Fix Discrepancies Immediately** - Don't proceed with discrepancies
6. **Re-validate After Fixes** - Ensure corrections worked
7. **Keep Validation Logs** - For audit trail

## Success Criteria

Migration is complete ONLY when:
- ✅ All object counts match exactly
- ✅ All sequences have correct START WITH values
- ✅ All constraints are ACTIVE
- ✅ All indexes exist
- ✅ No discrepancies in validation report
- ✅ 100% schema parity achieved

## Troubleshooting

### Validation Query Fails
- Check database connectivity
- Verify schema/user permissions
- Ensure correct schema name used

### Object Count Mismatch
- Review migration logs for errors
- Check if objects were skipped
- Verify object creation scripts ran successfully

### Sequence Values Incorrect
- Re-extract Oracle sequence metadata
- Regenerate sequence DDL with correct START WITH
- Drop and recreate sequences

### Constraints Not Active
- Check constraint validation errors
- Review data quality issues
- Fix data and re-enable constraints

## Made with Bob