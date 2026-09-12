-- Research desk sections for homepage filtering and CMS classification.

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

ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_section_allowed;

-- Normalize legacy labels into the five research desks where possible.
UPDATE public.articles
SET section = CASE
  WHEN section IS NULL OR btrim(section) = '' THEN 'Indian Market'
  WHEN btrim(section) IN ('Economy', 'Macro Intelligence') THEN 'Economics'
  WHEN btrim(section) IN ('Private Equity', 'Deal Tracker') THEN 'Private Markets'
  WHEN btrim(section) IN (
    'Pre-Market Update', 'Morning Market Update', 'Today''s Market Brief',
    'Market Opening Outlook', '12 PM Market Update', 'Market News',
    'Research Reports', 'Stock Analysis', 'Company Updates', 'IPOs',
    'Market Close Update', 'Day Close Update', 'Market Close Summary',
    'Research', 'Opinions & Editorials', 'Editor''s Desk'
  ) THEN 'Indian Market'
  ELSE btrim(section)
END
WHERE section IS NULL
   OR btrim(section) = ''
   OR btrim(section) IN (
     'Economy', 'Macro Intelligence',
     'Private Equity', 'Deal Tracker',
     'Pre-Market Update', 'Morning Market Update', 'Today''s Market Brief',
     'Market Opening Outlook', '12 PM Market Update', 'Market News',
     'Research Reports', 'Stock Analysis', 'Company Updates', 'IPOs',
     'Market Close Update', 'Day Close Update', 'Market Close Summary',
     'Research', 'Opinions & Editorials', 'Editor''s Desk'
   );

UPDATE public.articles
SET section = 'Indian Market'
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
      'Deal Tracker',
      'Editor''s Desk',
      'Private Equity',
      'Indian Market',
      'Private Markets',
      'Hedge Funds',
      'Economics'
   );

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
      'Deal Tracker',
      'Editor''s Desk',
      'Private Equity',
      'Indian Market',
      'Private Markets',
      'Hedge Funds',
      'Economics'
    )
  );

INSERT INTO public.article_categories (name, slug, description, sort_order)
VALUES
  ('Indian Market', 'indian-market', 'India equities, sectors, and company research', 1),
  ('Global Markets', 'global-markets', 'US, Europe, Asia and cross-border markets', 2),
  ('Private Markets', 'private-markets', 'Private equity, venture, and deal intelligence', 3),
  ('Hedge Funds', 'hedge-funds', 'Hedge fund strategies and manager research', 4),
  ('Economics', 'economics', 'Macro, policy, rates, inflation and geopolitics', 5)
ON CONFLICT (slug) DO UPDATE
SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  sort_order = EXCLUDED.sort_order,
  is_active = true,
  updated_at = now();
