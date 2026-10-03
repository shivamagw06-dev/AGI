-- Harden CMS intelligence ingest jobs (v1.0.1 LOCKED — additive).
-- Adds dead-letter status, metrics columns, and reclaim-friendly indexes.

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS failure_class text;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS worker_id text;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS wake_time_ms integer;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS engine_latency_ms integer;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD COLUMN IF NOT EXISTS queued_at timestamptz;

UPDATE public.cms_intelligence_ingest_jobs
SET queued_at = COALESCE(queued_at, created_at)
WHERE queued_at IS NULL;

-- Expand status check to include failed_permanent (dead-letter).
DO $$
DECLARE
  cname text;
BEGIN
  FOR cname IN
    SELECT con.conname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'public'
      AND rel.relname = 'cms_intelligence_ingest_jobs'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE public.cms_intelligence_ingest_jobs DROP CONSTRAINT IF EXISTS %I', cname);
  END LOOP;
END $$;

ALTER TABLE public.cms_intelligence_ingest_jobs
  ADD CONSTRAINT cms_intelligence_ingest_jobs_status_check
  CHECK (status IN ('pending', 'waking', 'processing', 'completed', 'failed', 'failed_permanent'));

CREATE INDEX IF NOT EXISTS cms_ingest_jobs_stall_idx
  ON public.cms_intelligence_ingest_jobs (status, updated_at ASC)
  WHERE status IN ('waking', 'processing');

CREATE INDEX IF NOT EXISTS cms_ingest_jobs_queued_alert_idx
  ON public.cms_intelligence_ingest_jobs (status, created_at ASC)
  WHERE status = 'pending';
