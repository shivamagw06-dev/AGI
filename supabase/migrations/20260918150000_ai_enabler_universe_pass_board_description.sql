-- The universe pass, second run: the SME board, and stored descriptions.
--
-- board: 'main' for EQUITY_L.csv, 'sme' for SME_EQUITY_L.csv (NSE Emerge).
-- The first run covered the main board only, which is why ESDS and Supreme
-- Power, both on Emerge, were recorded as not in the list.
--
-- description: the company's Upstox business description, so a change to
-- the nomination rules can be re-scored without refetching every profile.
-- Provider text: read by the server only, never returned by the API.
--
-- Additive only. Existing rows are kept; the first run's rows get
-- board = 'main', which is what they were.
alter table public.ai_enabler_universe_pass
  add column if not exists board text not null default 'main'
    check (board in ('main', 'sme'));

alter table public.ai_enabler_universe_pass
  add column if not exists description text;

notify pgrst, 'reload schema';
