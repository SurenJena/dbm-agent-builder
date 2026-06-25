-- =============================================================
-- 04_fk.sql  —  FOREIGN KEY constraints (applied after data load)
-- Schema: hr_schema
-- Generated: 2026-06-25T23:36:36.461595
-- =============================================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'COUNTR_REG_FK'
  ) THEN
    ALTER TABLE "hr_schema"."COUNTRIES" ADD CONSTRAINT "COUNTR_REG_FK" FOREIGN KEY ("REGION_ID") REFERENCES "hr_schema"."REGIONS" ("REGION_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'DEPT_LOC_FK'
  ) THEN
    ALTER TABLE "hr_schema"."DEPARTMENTS" ADD CONSTRAINT "DEPT_LOC_FK" FOREIGN KEY ("LOCATION_ID") REFERENCES "hr_schema"."LOCATIONS" ("LOCATION_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'DEPT_MGR_FK'
  ) THEN
    ALTER TABLE "hr_schema"."DEPARTMENTS" ADD CONSTRAINT "DEPT_MGR_FK" FOREIGN KEY ("MANAGER_ID") REFERENCES "hr_schema"."EMPLOYEES" ("EMPLOYEE_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'EMP_DEPT_FK'
  ) THEN
    ALTER TABLE "hr_schema"."EMPLOYEES" ADD CONSTRAINT "EMP_DEPT_FK" FOREIGN KEY ("DEPARTMENT_ID") REFERENCES "hr_schema"."DEPARTMENTS" ("DEPARTMENT_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'EMP_JOB_FK'
  ) THEN
    ALTER TABLE "hr_schema"."EMPLOYEES" ADD CONSTRAINT "EMP_JOB_FK" FOREIGN KEY ("JOB_ID") REFERENCES "hr_schema"."JOBS" ("JOB_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'EMP_MANAGER_FK'
  ) THEN
    ALTER TABLE "hr_schema"."EMPLOYEES" ADD CONSTRAINT "EMP_MANAGER_FK" FOREIGN KEY ("MANAGER_ID") REFERENCES "hr_schema"."EMPLOYEES" ("EMPLOYEE_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'JHIST_DEPT_FK'
  ) THEN
    ALTER TABLE "hr_schema"."JOB_HISTORY" ADD CONSTRAINT "JHIST_DEPT_FK" FOREIGN KEY ("DEPARTMENT_ID") REFERENCES "hr_schema"."DEPARTMENTS" ("DEPARTMENT_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'JHIST_EMP_FK'
  ) THEN
    ALTER TABLE "hr_schema"."JOB_HISTORY" ADD CONSTRAINT "JHIST_EMP_FK" FOREIGN KEY ("EMPLOYEE_ID") REFERENCES "hr_schema"."EMPLOYEES" ("EMPLOYEE_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'JHIST_JOB_FK'
  ) THEN
    ALTER TABLE "hr_schema"."JOB_HISTORY" ADD CONSTRAINT "JHIST_JOB_FK" FOREIGN KEY ("JOB_ID") REFERENCES "hr_schema"."JOBS" ("JOB_ID");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'LOC_C_ID_FK'
  ) THEN
    ALTER TABLE "hr_schema"."LOCATIONS" ADD CONSTRAINT "LOC_C_ID_FK" FOREIGN KEY ("COUNTRY_ID") REFERENCES "hr_schema"."COUNTRIES" ("COUNTRY_ID");
  END IF;
END $$;
