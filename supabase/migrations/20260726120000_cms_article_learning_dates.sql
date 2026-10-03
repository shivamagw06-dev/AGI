-- CMS article learning dates — additive only (Architecture v1.0.1 LOCKED).
-- Tracks when AGI read/learned each uploaded article for daily knowledge updates.

ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS last_learned_at timestamptz;

ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS learn_status text;

ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS last_learn_error text;

ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS learn_count integer DEFAULT 0;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'articles_learn_status_check'
  ) THEN
    ALTER TABLE public.articles
      ADD CONSTRAINT articles_learn_status_check
      CHECK (learn_status IS NULL OR learn_status IN ('pending', 'learned', 'failed', 'skipped'));
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.cms_article_learn_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id uuid REFERENCES public.articles (id) ON DELETE CASCADE,
  learned_at timestamptz NOT NULL DEFAULT now(),
  learning_date date NOT NULL DEFAULT ((now() AT TIME ZONE 'Asia/Kolkata')::date),
  document_id text,
  status text NOT NULL DEFAULT 'learned',
  title text,
  slug text,
  destination text,
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS cms_article_learn_events_date_idx
  ON public.cms_article_learn_events (learning_date DESC);

CREATE INDEX IF NOT EXISTS cms_article_learn_events_article_idx
  ON public.cms_article_learn_events (article_id, learned_at DESC);

ALTER TABLE public.cms_article_learn_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'cms_article_learn_events'
      AND policyname = 'cms_auth_read_learn_events'
  ) THEN
    CREATE POLICY cms_auth_read_learn_events
      ON public.cms_article_learn_events
      FOR SELECT
      TO authenticated
      USING (true);
  END IF;
END $$;
