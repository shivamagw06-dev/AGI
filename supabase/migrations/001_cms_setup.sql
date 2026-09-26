-- Run this in Supabase SQL Editor to enable full CMS category management.
-- Safe to run multiple times (uses IF NOT EXISTS).

ALTER TABLE articles ADD COLUMN IF NOT EXISTS meta_description text;

CREATE TABLE IF NOT EXISTS article_categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  slug text NOT NULL UNIQUE,
  description text,
  sort_order int DEFAULT 0,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Seed default categories
INSERT INTO article_categories (name, slug, description, sort_order) VALUES
  ('Morning Market Update', 'morning-market-update', 'Pre-market and opening bell analysis', 1),
  ('12 PM Market Update', '12-pm-market-update', 'Midday market snapshot and key moves', 2),
  ('Day Close Update', 'day-close-update', 'End-of-day market wrap and closing analysis', 3),
  ('Market News', 'market-news', 'Breaking market news and headlines', 4),
  ('Research Reports', 'research-reports', 'In-depth institutional research reports', 5),
  ('Stock Analysis', 'stock-analysis', 'Company and equity analysis', 6),
  ('Economy', 'economy', 'Macroeconomic trends, GDP, inflation and policy', 7),
  ('Global Markets', 'global-markets', 'US, Europe, Asia and cross-border markets', 8),
  ('Commodities', 'commodities', 'Oil, gold, metals and commodity markets', 9),
  ('IPOs', 'ipos', 'IPO pipeline, listings and new issues', 10)
ON CONFLICT (slug) DO NOTHING;

ALTER TABLE article_categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read active categories"
  ON article_categories FOR SELECT
  USING (is_active = true);

CREATE POLICY "Authenticated manage categories"
  ON article_categories FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);
