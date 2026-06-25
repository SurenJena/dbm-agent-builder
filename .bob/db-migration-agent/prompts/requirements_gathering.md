# Requirements Gathering Prompts

## Phase 1: Initial Assessment

When a user requests a database migration (e.g., "Migrate Oracle HR schema to PostgreSQL"), automatically gather the following information through structured questions.

## Source Database Questions

### 1. Database Platform and Version
**Question:** "What is your source database platform and version?"

**Options:**
- Oracle (11g, 12c, 19c, 21c)
- SQL Server (2012, 2014, 2016, 2019, 2022)
- MySQL (5.7, 8.0)
- DB2 (10.5, 11.1, 11.5)
- PostgreSQL (for upgrades: 9.6, 10, 11, 12, 13, 14, 15)

**Follow-up:** "What is the exact version number?" (e.g., 19.3.0.0.0 for Oracle)

### 2. Connection Details
**Questions:**
- "What is the hostname or IP address of the source database?"
- "What port is the database listening on?" (Provide default based on platform)
- "What is the database/service name?"
- "Which schema(s) should be migrated?" (Can be multiple)

### 3. Authentication
**Questions:**
- "What authentication method is used?"
  - Username/Password
  - Kerberos
  - Windows Authentication (SQL Server)
  - Oracle Wallet
  - Other
- "Is SSL/TLS required for the connection?"

### 4. Access Credentials
**Note:** "I'll need database credentials during the migration execution phase. For now, I'll create a secure .env.template file where you can add them later."

## Target Database Questions

### 1. Database Platform and Version
**Question:** "What is your target database platform?"

**Options:**
- PostgreSQL (12, 13, 14, 15, 16)
- Snowflake
- AWS RDS (PostgreSQL, MySQL, SQL Server)
- Azure SQL Database
- Google Cloud SQL

**Follow-up:** "What version?" (if applicable)

### 2. Connection Details
**Questions:**
- "What is the hostname/endpoint of the target database?"
- "What port?" (Provide default)
- "What is the target database name?"
- "What schema should be used?" (default: public for PostgreSQL)

### 3. Environment
**Questions:**
- "Is this a cloud-hosted database?" (Yes/No)
- If cloud: "Which region/availability zone?"
- "Is this a new database or existing?" (New/Existing)

## Migration Scope Questions

### 1. Objects to Migrate
**Questions:**
- "Should all tables be migrated?" (Yes/No)
  - If No: "Which tables should be included/excluded?"
- "Should views be migrated?" (Yes/No/Convert to tables)
- "Should stored procedures be migrated?" (Yes/No/Convert)
- "Should triggers be migrated?" (Yes/No/Convert)
- "Should sequences be migrated?" (Yes/No)

### 2. Data Migration
**Questions:**
- "Should data be migrated?" (Yes/No/Schema only)
- If Yes: "Estimated data volume?" (GB/TB)
- "Are there any large tables (>1GB)?" (Yes/No)
  - If Yes: "Which tables and their approximate sizes?"

### 3. Special Considerations
**Questions:**
- "Are there any tables with LOB columns (CLOB, BLOB)?" (Yes/No)
- "Are there any partitioned tables?" (Yes/No)
- "Are there any tables with special characters in names?" (Yes/No)
- "Are there any custom data types?" (Yes/No)

## Constraints and Requirements

### 1. Timeline
**Questions:**
- "What is your target migration date?"
- "What is your acceptable downtime window?" (Hours/Minutes)
- "Is this a one-time migration or ongoing replication?" (One-time/Ongoing)

### 2. Performance Requirements
**Questions:**
- "What are your performance requirements?"
  - Same as source
  - Better than source
  - No specific requirement
- "What is the expected query load?" (Low/Medium/High)
- "Are there any specific queries that must be optimized?"

### 3. Compliance and Security
**Questions:**
- "Are there any compliance requirements?" (GDPR, HIPAA, PCI DSS, SOX, None)
- "Is data encryption required?" (In transit/At rest/Both/None)
- "Are there any data masking requirements?" (Yes/No)
- "Should audit logging be enabled?" (Yes/No)

### 4. Business Requirements
**Questions:**
- "What is the primary reason for migration?"
  - Cost reduction
  - Performance improvement
  - Cloud migration
  - Platform modernization
  - End of support for current platform
  - Other
- "Are there any critical business processes dependent on this database?"
- "What is the rollback criteria?" (What would trigger a rollback?)

## Environment and Infrastructure

### 1. Network
**Questions:**
- "Are source and target databases on the same network?" (Yes/No)
- "What is the network bandwidth between source and target?"
- "Are there any firewall rules to configure?" (Yes/No)

### 2. Resources
**Questions:**
- "Is there a staging/test environment available?" (Yes/No)
- "Can we test the migration in non-production first?" (Yes/No)
- "Who will be involved in the migration?" (DBA, Developer, DevOps, etc.)

### 3. Backup and Recovery
**Questions:**
- "Are current backups available?" (Yes/No)
- "When was the last backup taken?"
- "What is the backup retention policy?"
- "Is there a tested restore procedure?" (Yes/No)

## Summary Confirmation

After gathering all information, present a summary:

```
Migration Summary:
==================

Source Database:
- Platform: [Oracle 19c]
- Host: [hostname]
- Database: [ORCL]
- Schema: [HR]

Target Database:
- Platform: [PostgreSQL 15]
- Host: [hostname]
- Database: [hr_db]
- Schema: [public]

Migration Scope:
- Tables: [All / Specific list]
- Views: [Yes/No]
- Procedures: [Yes/No/Convert]
- Data: [Yes/No]
- Estimated Volume: [X GB]

Timeline:
- Target Date: [Date]
- Downtime Window: [X hours]

Requirements:
- Compliance: [List]
- Performance: [Requirements]
- Special Considerations: [List]

Is this information correct? (Yes/No)
```

## Next Steps

After confirmation:
1. "I'll now analyze the source database schema and generate a detailed migration plan."
2. "This will take a few moments..."
3. Proceed to Phase 2: Discovery & Analysis

## Error Handling

If information is missing or unclear:
- "I need more information about [specific item]"
- "Could you clarify [specific point]?"
- "This information is required to proceed: [list]"

## Tips for Bob

- Be conversational but efficient
- Provide sensible defaults when possible
- Explain why certain information is needed
- Group related questions together
- Don't ask for credentials yet (use .env.template)
- Validate responses (e.g., valid port numbers, dates)
- Offer to skip optional items
- Provide examples when helpful