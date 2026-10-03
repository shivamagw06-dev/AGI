-- Pipeline foundation for CMS intelligence ingest jobs (v1.0.1 LOCKED — additive).
-- Soft-wires priority, stage tracing, leases, cost/confidence, approval — no new engines.

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 3;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS pipeline_stage text NOT NULL DEFAULT 'queued';

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS stage_trace jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS stage_keys jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS lease_token text;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS confidence numeric;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS quality numeric;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS missing_sections integer;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS embedding_version text;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS cost_usd numeric;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS approval_status text DEFAULT 'not_required';

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS require_approval boolean NOT NULL DEFAULT false;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS replay_of text;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS parent_job_id text;

CREATE INDEX IF NOT EXISTS cms_ingest_jobs_priority_idx
  ON public.cms_intelligence_ingest_jobs (status, priority ASC, next_attempt_at ASC)
  WHERE status = 'pending';

COMMENT ON COLUMN public.cms_intelligence_ingest_jobs.priority IS
  '1=market_alert, 2=research_update, 3=default/blog, 4=archive';

COMMENT ON COLUMN public.cms_intelligence_ingest_jobs.pipeline_stage IS
  'Soft stages over existing AGIB layers: queued→wake→kip_ingest→knowledge_compound→completed';
