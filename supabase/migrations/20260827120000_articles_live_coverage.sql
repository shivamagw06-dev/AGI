-- Continuing / live articles: same URL, timestamped updates, LIVE badge.
ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS is_live boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS live_updates jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS live_started_at timestamptz,
  ADD COLUMN IF NOT EXISTS live_ended_at timestamptz;

CREATE INDEX IF NOT EXISTS articles_is_live_idx
  ON public.articles (updated_at DESC)
  WHERE is_live AND status = 'published';
