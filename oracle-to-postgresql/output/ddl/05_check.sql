-- =============================================================
-- 05_check.sql  —  CHECK constraints
-- Schema: hr_schema
-- Generated: 2026-06-25T23:36:36.461646
-- =============================================================

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'hr_schema' AND c.conname = 'JHIST_DATE_INTERVAL'
  ) THEN
    ALTER TABLE "hr_schema"."JOB_HISTORY" ADD CONSTRAINT "JHIST_DATE_INTERVAL" CHECK ("END_DATE" > "START_DATE");
  END IF;
END $$;
