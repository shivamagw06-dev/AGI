-- CMS intelligence ingest job queue (Architecture v1.0.1 LOCKED — soft additive only).
-- Browser never waits on Render wake / embeddings; Node worker owns the long path.

CREATE TABLE IF NOT EXISTS public.cms_intelligence_ingest_jobs (
  id text PRIMARY KEY,
  article_id text,
  slug text,
  content_hash text NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'waking', 'processing', 'completed', 'failed')),
  phase text NOT NULL DEFAULT 'queued',
  attempt integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 6,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  document_id text,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  next_attempt_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cms_ingest_jobs_status_next_idx
  ON public.cms_intelligence_ingest_jobs (status, next_attempt_at ASC);

CREATE INDEX IF NOT EXISTS cms_ingest_jobs_article_idx
  ON public.cms_intelligence_ingest_jobs (article_id, created_at DESC);

CREATE INDEX IF NOT EXISTS cms_ingest_jobs_hash_idx
  ON public.cms_intelligence_ingest_jobs (content_hash, created_at DESC);

-- One active job per article+content hash (idempotency).
CREATE UNIQUE INDEX IF NOT EXISTS cms_ingest_jobs_active_article_hash_uidx
  ON public.cms_intelligence_ingest_jobs (article_id, content_hash)
  WHERE status IN ('pending', 'waking', 'processing')
    AND article_id IS NOT NULL;

ALTER TABLE public.cms_intelligence_ingest_jobs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'cms_intelligence_ingest_jobs'
      AND policyname = 'cms_auth_read_ingest_jobs'
  ) THEN
    CREATE POLICY cms_auth_read_ingest_jobs
      ON public.cms_intelligence_ingest_jobs
      FOR SELECT
      TO authenticated
      USING (true);
  END IF;
END $$;
