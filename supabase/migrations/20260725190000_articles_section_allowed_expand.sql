-- Expand articles.section check constraint for AGI Letters + Intelligence CMS.
-- Safe for existing data: normalizes unknown sections before re-adding the check.

-- 1) Drop old section check constraints
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
      AND (
        con.conname ILIKE '%section%'
        OR pg_get_constraintdef(con.oid) ILIKE '%section%'
      )
  LOOP
    EXECUTE format('ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS %I', cname);
  END LOOP;
END $$;

ALTER TABLE public.articles
  DROP CONSTRAINT IF EXISTS articles_section_allowed;

-- 2) Normalize common aliases / legacy labels
UPDATE public.articles
SET section = CASE
  WHEN section IS NULL OR btrim(section) = '' THEN 'Research Reports'
  WHEN lower(btrim(section)) IN ('pre-market update', 'pre market update', 'morning brief', 'agi morning brief')
    THEN 'Morning Market Update'
  WHEN lower(btrim(section)) IN ('market close update', 'market close summary', 'evening brief', 'agi evening brief', 'market close')
    THEN 'Day Close Update'
  WHEN lower(btrim(section)) IN ('macro', 'agi macro', 'macro intelligence', 'macroeconomics')
    THEN 'Economy'
  WHEN lower(btrim(section)) IN ('intelligence', 'agi intelligence', 'private intelligence', 'intelligence-only')
    THEN 'Intelligence'
  WHEN lower(btrim(section)) IN ('research', 'research report', 'research notes')
    THEN 'Research Reports'
  WHEN lower(btrim(section)) IN ('company update', 'company-updates')
    THEN 'Company Updates'
  ELSE btrim(section)
END
WHERE section IS NULL
   OR btrim(section) = ''
   OR lower(btrim(section)) IN (
     'pre-market update', 'pre market update', 'morning brief', 'agi morning brief',
     'market close update', 'market close summary', 'evening brief', 'agi evening brief', 'market close',
     'macro', 'agi macro', 'macro intelligence', 'macroeconomics',
     'intelligence', 'agi intelligence', 'private intelligence', 'intelligence-only',
     'research', 'research report', 'research notes',
     'company update', 'company-updates'
   );

-- 3) Force any remaining unknown sections into a safe default
UPDATE public.articles
SET section = 'Research Reports'
WHERE section IS NULL
   OR btrim(section) = ''
   OR btrim(section) NOT IN (
      'Pre-Market Update',
      'Morning Market Update',
      'Today''s Market Brief',
      'Market Opening Outlook',
      '12 PM Market Update',
      'Market News',
      'Research Reports',
      'Stock Analysis',
      'Company Updates',
      'IPOs',
      'Market Close Update',
      'Day Close Update',
      'Market Close Summary',
      'Macro Intelligence',
      'Economy',
      'Global Markets',
      'Commodities',
      'Intelligence',
      'AGI Intelligence',
      'Research',
      'Opinions & Editorials',
      'Deal Tracker'
   );

-- Optional: inspect remaining distinct sections before constraint
-- SELECT section, count(*) FROM public.articles GROUP BY 1 ORDER BY 2 DESC;

-- 4) Re-add expanded constraint
ALTER TABLE public.articles
  ADD CONSTRAINT articles_section_allowed
  CHECK (
    section IS NULL
    OR section IN (
      'Pre-Market Update',
      'Morning Market Update',
      'Today''s Market Brief',
      'Market Opening Outlook',
      '12 PM Market Update',
      'Market News',
      'Research Reports',
      'Stock Analysis',
      'Company Updates',
      'IPOs',
      'Market Close Update',
      'Day Close Update',
      'Market Close Summary',
      'Macro Intelligence',
      'Economy',
      'Global Markets',
      'Commodities',
      'Intelligence',
      'AGI Intelligence',
      'Research',
      'Opinions & Editorials',
      'Deal Tracker'
    )
  );

-- 5) Ensure categories exist for the new letter names.
INSERT INTO public.article_categories (name, slug, description, sort_order)
VALUES
  ('Pre-Market Update', 'pre-market-update', 'AGI Morning Brief — everything before the opening bell', 1),
  ('Market Close Update', 'market-close-update', 'AGI Evening Brief — what moved markets today and why', 5),
  ('Macro Intelligence', 'macro-intelligence', 'AGI Macro — policy, inflation, rates, FX, geopolitics', 7),
  ('Intelligence', 'intelligence', 'Private AGI Intelligence notes (not public website)', 20)
ON CONFLICT (slug) DO NOTHING;
