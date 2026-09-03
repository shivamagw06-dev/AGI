-- Base tables the migration chain alters but never creates.
--
-- The history is not self-contained and has not been since migration 001,
-- whose own comment says "Run this in Supabase SQL Editor". Four tables were
-- created by hand in the dashboard and only ever altered by migrations:
--
--   articles, profiles, client_portfolios, client_portfolio_holdings
--
-- Two of them are the ones CAS import extends, so a blank database cannot
-- replay the chain without them. This file supplies the minimum contract the
-- migrations rely on, so the chain can be exercised end to end in CI.
--
-- It is a test fixture and not a description of production. The columns here
-- are the ones migrations and application code actually reference; production
-- may carry more. A test passing against this shape says the migrations apply
-- and the RPCs behave, not that this matches the live schema column for
-- column. Making the real chain self-contained is a separate piece of work.

CREATE TABLE IF NOT EXISTS public.articles (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug       text UNIQUE,
  title      text,
  body       text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.profiles (
  id         uuid PRIMARY KEY,
  email      text,
  full_name  text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.client_portfolios (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL DEFAULT auth.uid()
                 REFERENCES auth.users(id) ON DELETE CASCADE,
  name         text NOT NULL,
  base_currency text NOT NULL DEFAULT 'INR',
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.client_portfolio_holdings (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id uuid NOT NULL
                 REFERENCES public.client_portfolios(id) ON DELETE CASCADE,
  user_id      uuid NOT NULL DEFAULT auth.uid()
                 REFERENCES auth.users(id) ON DELETE CASCADE,
  symbol       text,
  asset_name   text,
  quantity     numeric,
  average_cost numeric,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.client_portfolios          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_portfolio_holdings  ENABLE ROW LEVEL SECURITY;

-- The policies production relies on. Without these the RLS isolation
-- assertions would pass for the wrong reason: no policy means no rows for
-- anyone, which looks like isolation and is not.
CREATE POLICY client_portfolios_own ON public.client_portfolios
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id)
  WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY client_portfolio_holdings_own ON public.client_portfolio_holdings
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id)
  WITH CHECK ((SELECT auth.uid()) = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE
  ON public.client_portfolios, public.client_portfolio_holdings
  TO authenticated, service_role;
