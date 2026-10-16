-- Dual CMS destinations:
--   draft         = work in progress
--   published     = live on the public website
--   intelligence  = private knowledge for Ask AGI only (not website)

ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS meta_description text;

ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS intelligence_document_id text;

ALTER TABLE public.articles
  ADD COLUMN IF NOT EXISTS intelligence_ingested_at timestamptz;

-- Soft-drop common status check constraints if present, then re-add expanded set.
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
      AND rel.relname = 'articles'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS %I', cname);
  END LOOP;
END $$;

ALTER TABLE public.articles
  DROP CONSTRAINT IF EXISTS articles_status_check;

ALTER TABLE public.articles
  ADD CONSTRAINT articles_status_check
  CHECK (status IN ('draft', 'published', 'intelligence'));

-- Public visitors may only read live website articles.
DROP POLICY IF EXISTS "Public read published articles" ON public.articles;
DROP POLICY IF EXISTS "anon_read_published_articles" ON public.articles;
DROP POLICY IF EXISTS "Public can read published articles" ON public.articles;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'articles' AND policyname = 'cms_public_read_published_only'
  ) THEN
    CREATE POLICY cms_public_read_published_only
      ON public.articles
      FOR SELECT
      TO anon
      USING (status = 'published');
  END IF;
END $$;

-- Authenticated CMS users can manage all article destinations.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'articles' AND policyname = 'cms_auth_manage_articles'
  ) THEN
    CREATE POLICY cms_auth_manage_articles
      ON public.articles
      FOR ALL
      TO authenticated
      USING (true)
      WITH CHECK (true);
  END IF;
END $$;
