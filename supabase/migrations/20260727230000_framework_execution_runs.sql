-- Phase 1 — Immutable framework execution telemetry (Architecture v1.0.1 LOCKED; additive).
-- One row per framework attempt. Rows are append-only: never UPDATE, never DELETE.
-- This is the learning dataset for framework calibration.

CREATE TABLE IF NOT EXISTS public.framework_execution_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id text NOT NULL,
  answer_id text,
  path text,

  -- Question
  question text NOT NULL,
  question_type text NOT NULL,
  question_confidence numeric,

  -- Entity resolution
  entity_id text,
  entity_name text,
  entity_type text,
  entity_confidence numeric,

  -- Contract + validation provenance
  evidence_contract_version text,
  validation_version text,
  governance_version text,
  required_evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  observed_evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  missing_evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  evidence_provenance jsonb NOT NULL DEFAULT '[]'::jsonb,
  validation_result jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- Framework
  framework_id text,
  framework_name text,
  framework_version text,
  execution_status text NOT NULL,
  failure_reason text,
  outputs jsonb NOT NULL DEFAULT '{}'::jsonb,
  confidence numeric,

  -- Committee / narrative governance
  committee_stance text,
  committee_conclusion text,
  narrative_allowed boolean,

  execution_ms integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS framework_execution_runs_run_id_idx
  ON public.framework_execution_runs (run_id);
CREATE INDEX IF NOT EXISTS framework_execution_runs_entity_idx
  ON public.framework_execution_runs (entity_id, question_type);
CREATE INDEX IF NOT EXISTS framework_execution_runs_framework_idx
  ON public.framework_execution_runs (framework_id, execution_status);
CREATE INDEX IF NOT EXISTS framework_execution_runs_created_idx
  ON public.framework_execution_runs (created_at DESC);

ALTER TABLE public.framework_execution_runs ENABLE ROW LEVEL SECURITY;

-- Service role only (bypasses RLS). No anon/authenticated access.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'framework_execution_runs'
      AND policyname = 'framework_execution_runs_service_only'
  ) THEN
    CREATE POLICY framework_execution_runs_service_only
      ON public.framework_execution_runs
      FOR ALL
      TO authenticated
      USING (false)
      WITH CHECK (false);
  END IF;
END $$;

-- Immutability: block UPDATE and DELETE even for privileged roles.
CREATE OR REPLACE FUNCTION public.framework_execution_runs_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'framework_execution_runs is append-only (attempted %)', TG_OP;
END $$;

DROP TRIGGER IF EXISTS framework_execution_runs_no_update ON public.framework_execution_runs;
CREATE TRIGGER framework_execution_runs_no_update
  BEFORE UPDATE ON public.framework_execution_runs
  FOR EACH ROW EXECUTE FUNCTION public.framework_execution_runs_immutable();

DROP TRIGGER IF EXISTS framework_execution_runs_no_delete ON public.framework_execution_runs;
CREATE TRIGGER framework_execution_runs_no_delete
  BEFORE DELETE ON public.framework_execution_runs
  FOR EACH ROW EXECUTE FUNCTION public.framework_execution_runs_immutable();

COMMENT ON TABLE public.framework_execution_runs IS
  'Append-only Phase 1 telemetry: one row per framework execution attempt (evidence-first governance).';
