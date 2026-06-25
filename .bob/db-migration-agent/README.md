# Database Migration Agent Mode

## Overview

The Database Migration Agent mode is a specialized Bob mode for automating database migrations across multiple platforms. It provides end-to-end migration support from requirements gathering through deployment and validation.

## ⚠️ IMPORTANT: Production-First Mode

**This mode operates in Production Migration Mode by default.**

When users request database migration (especially Oracle to PostgreSQL), the mode generates **production-ready, enterprise-grade migration solutions** for live databases, NOT Docker-based demo environments.

See `0_production_mode_instructions.md` for complete production mode guidelines.

### Key Principles:
- ✅ Assume live Oracle and PostgreSQL databases exist
- ✅ Generate directly deployable, production-ready code
- ✅ No Docker containers unless explicitly requested
- ✅ Enterprise-scale performance and error handling
- ✅ Comprehensive validation and reconciliation
- ❌ No demo environments, sample data, or proof-of-concepts by default

## Supported Platforms

### Source Databases
- **Oracle** (11g, 12c, 19c, 21c)
- **SQL Server** (2012, 2014, 2016, 2019, 2022)
- **MySQL** (5.7, 8.0)
- **DB2** (10.5, 11.1, 11.5)
- **PostgreSQL** (9.6+ for upgrades)

### Target Databases
- **PostgreSQL** (12, 13, 14, 15, 16)
- **Snowflake**
- **AWS RDS** (PostgreSQL, MySQL, SQL Server)
- **Azure SQL Database**
- **Google Cloud SQL**

## Key Capabilities

### 1. Discovery & Analysis
- Automatic schema extraction
- Dependency analysis
- Compatibility assessment
- Data volume analysis
- Risk identification

### 2. DDL Conversion
- Data type mapping
- SQL dialect translation
- Syntax conversion
- Platform-specific feature handling

### 3. Data Migration
- Batch processing
- Parallel execution
- Error recovery
- Progress tracking
- Memory-efficient processing

### 4. Validation
- Row count validation
- Data integrity checks
- Constraint validation
- Performance benchmarking

### 5. Automation
- Complete migration framework generation
- Automated script creation
- Configuration management
- Deployment automation

## Workflow

### Phase 1: Requirements Gathering
**Automated** - Bob collects all necessary information through structured questions:
- Source database details
- Target database details
- Migration scope
- Timeline and constraints
- Compliance requirements

### Phase 2: Discovery & Analysis
**Automated** - Bob analyzes the source database:
- Extracts complete schema metadata
- Analyzes table dependencies
- Assesses compatibility
- Estimates effort and risks
- Generates discovery report

### Phase 3: Architecture Design
**Automated** - Bob designs the target architecture:
- Target schema structure
- Data type mappings
- Migration strategy
- Performance optimizations
- Rollback procedures

### Phase 4: Migration Plan Generation
**Automated** - Bob creates detailed execution plan:
- Task breakdown
- Execution order
- Validation checkpoints
- Timeline with dependencies
- Rollback procedures

### Phase 5: Framework Generation
**Automated** - Bob generates complete migration framework:
- Configuration files
- Discovery scripts
- Conversion tools
- Migration scripts
- Validation scripts
- Test suite
- Execution scripts
- Documentation

### Phase 6: Testing
**User-initiated** - Execute tests:
- Unit tests
- Integration tests
- Data validation
- Performance tests

### Phase 7: Execution & Validation
**User-initiated** - Run migration:
- Execute migration scripts
- Monitor progress
- Validate results
- Generate reports
- Document outcomes

### Phase 8: Schema Parity Validation (MANDATORY)
**Automated** - Comprehensive validation:
- Compare object counts (tables, views, sequences, indexes, constraints, triggers, functions, procedures)
- Verify sequence starting values match source
- Validate all constraints are active
- Confirm all indexes exist
- Generate detailed parity report
- If discrepancies found: automatically generate corrective SQL scripts
- Re-validate until 100% parity achieved

## User Experience

### Simple Request
```
User: "Migrate Oracle HR schema to PostgreSQL"
```

### Bob's Response
Bob automatically:
1. ✅ Asks clarifying questions about source and target
2. ✅ Validates connectivity
3. ✅ Discovers and analyzes schema
4. ✅ Designs target architecture
5. ✅ Generates migration plan
6. ✅ Creates complete framework with all scripts
7. ✅ Generates test suite
8. ✅ Provides execution instructions
9. ✅ Documents everything

### Result
A complete, ready-to-execute migration project with:
- All configuration files
- All migration scripts
- Complete test suite
- Comprehensive documentation
- Execution runbook

## Generated Project Structure

```
migration-project/
├── config/                    # Configuration files
├── discovery/                 # Schema discovery scripts
├── conversion/                # DDL conversion tools
├── migration/                 # Data migration scripts
├── validation/                # Validation scripts
├── tests/                     # Test suite
├── scripts/                   # Execution scripts
├── output/                    # Generated files and logs
├── docs/                      # Documentation
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

## Key Features

### Intelligent Data Type Mapping
Automatically maps data types between platforms:
- Oracle NUMBER → PostgreSQL NUMERIC/INTEGER/BIGINT
- SQL Server BIT → PostgreSQL BOOLEAN
- MySQL TINYINT(1) → PostgreSQL BOOLEAN
- Platform-specific type handling

### SQL Dialect Translation
Converts SQL syntax differences:
- Oracle NVL → PostgreSQL COALESCE
- SQL Server TOP → PostgreSQL LIMIT
- MySQL backticks → PostgreSQL double quotes
- Function conversions

### Dependency Management
Handles complex relationships:
- Foreign key dependencies
- View dependencies
- Stored procedure call chains
- Topological sorting for migration order

### Error Recovery
Robust error handling:
- Transaction management
- Retry logic
- Partial failure handling
- Detailed error logging

### Performance Optimization
Optimized for large datasets:
- Batch processing
- Parallel execution
- Index creation strategy
- Memory management
- Connection pooling

## Documentation

### Rules and Workflows
- `1_migration_workflow.xml` - Complete 7-phase workflow
- `2_database_platforms.xml` - Platform specifications
- `3_file_templates.xml` - Code templates
- `4_best_practices.xml` - Best practices and troubleshooting

### Skills
- `skills/oracle_migration.md` - Oracle-specific migration skills
- `skills/sqlserver_migration.md` - SQL Server migration skills
- `skills/mysql_migration.md` - MySQL migration skills
- `skills/schema_parity_validation.md` - Comprehensive schema validation methodology

### Templates
- `templates/project_structure.md` - Standard project structure

### Prompts
- `prompts/requirements_gathering.md` - Requirements gathering questions

## Usage Examples

### Example 1: Oracle to PostgreSQL
```
User: "Migrate Oracle HR schema to PostgreSQL 15"

Bob will:
1. Ask for connection details
2. Extract Oracle schema
3. Convert PL/SQL to PL/pgSQL
4. Map Oracle data types to PostgreSQL
5. Generate complete migration framework
6. Provide execution instructions
```

### Example 2: SQL Server to PostgreSQL
```
User: "Migrate SQL Server AdventureWorks to PostgreSQL"

Bob will:
1. Gather requirements
2. Convert T-SQL to PL/pgSQL
3. Handle IDENTITY columns
4. Convert indexes and constraints
5. Generate migration scripts
6. Create validation suite
```

### Example 3: MySQL to PostgreSQL
```
User: "Migrate MySQL e-commerce database to PostgreSQL"

Bob will:
1. Assess storage engines (InnoDB, MyISAM)
2. Convert AUTO_INCREMENT to SERIAL
3. Handle ENUM types
4. Convert stored procedures
5. Generate complete framework
6. Provide testing guidance
```

## Best Practices

### Pre-Migration
- ✅ Always backup source database
- ✅ Test in non-production environment first
- ✅ Validate connectivity and permissions
- ✅ Plan for capacity and performance
- ✅ Document current state

### During Migration
- ✅ Use phased approach
- ✅ Process data in batches
- ✅ Leverage parallel execution
- ✅ Create indexes after data load
- ✅ Monitor progress continuously
- ✅ Maintain comprehensive logs

### Post-Migration
- ✅ Comprehensive validation
- ✅ Performance testing
- ✅ Gather database statistics
- ✅ Document everything
- ✅ Plan for rollback if needed

## Common Pitfalls to Avoid

1. **Data Type Mismatches** - Carefully review type mappings
2. **Character Encoding Issues** - Ensure UTF-8 throughout
3. **NULL Handling** - Different NULL semantics between platforms
4. **Case Sensitivity** - Different rules between platforms
5. **Transaction Size** - Don't migrate too much in one transaction
6. **Foreign Key Order** - Respect dependency order
7. **Index Timing** - Create indexes after data load
8. **Missing Validation** - Always validate thoroughly

## Troubleshooting

### Connection Issues
- Verify network connectivity
- Check firewall rules
- Validate credentials
- Test with simple query

### Performance Issues
- Reduce batch size
- Increase parallel threads
- Drop indexes before load
- Optimize network

### Data Validation Failures
- Review data type mappings
- Check character encoding
- Verify timezone handling
- Re-run affected tables

### Constraint Violations
- Check migration order
- Temporarily disable constraints
- Clean up data quality issues
- Review constraint definitions

## Security Considerations

- ✅ Never store credentials in code
- ✅ Use environment variables
- ✅ Encrypt data in transit (SSL/TLS)
- ✅ Encrypt backups
- ✅ Implement least privilege access
- ✅ Maintain audit logs
- ✅ Follow compliance requirements

## Tools and Utilities

### Python Libraries
- `psycopg2` - PostgreSQL driver
- `cx_Oracle` - Oracle driver
- `pymssql` - SQL Server driver
- `pymysql` - MySQL driver
- `ibm_db` - DB2 driver
- `snowflake-connector-python` - Snowflake driver

### Migration Tools
- `pgloader` - MySQL to PostgreSQL migration
- `ora2pg` - Oracle to PostgreSQL migration
- Custom Python scripts for flexibility

### Monitoring
- Database-specific monitoring tools
- Custom logging and reporting
- Progress tracking dashboards

## Support and Resources

### Documentation
- Platform-specific migration guides in `skills/`
- Best practices in `4_best_practices.xml`
- Templates in `templates/`

### Testing
- Complete test suite generated
- Unit, integration, and validation tests
- Performance benchmarks

### Rollback
- Documented rollback procedures
- Backup verification
- Recovery time estimates
- Rollback testing

## Version History

- **v1.0** - Initial release with Oracle, SQL Server, MySQL, DB2 support
- Support for PostgreSQL, Snowflake, and cloud databases as targets
- Complete automation from requirements to deployment

## Contributing

This mode is part of Bob's custom modes. To enhance:
1. Add new database platform support in `2_database_platforms.xml`
2. Add platform-specific skills in `skills/`
3. Update templates and prompts as needed
4. Test thoroughly with real migrations

## License

Part of Bob AI Assistant custom modes.