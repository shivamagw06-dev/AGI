-- A monotonic version for concurrency control.
--
-- The import plan already carries a digest of the holdings it was computed
-- against, which detects a portfolio that moved. A counter does the same job
-- more cheaply and more clearly: comparing two integers under a row lock is
-- exact, whereas a hash has to be recomputed over every holding on each
-- confirmation and says only that something differs, not that anything moved
-- forward. The digest stays as a second check; the version is what serialises
-- concurrent confirmations.

ALTER TABLE public.client_portfolios
  ADD COLUMN IF NOT EXISTS portfolio_version bigint NOT NULL DEFAULT 1;

ALTER TABLE public.portfolio_imports
  ADD COLUMN IF NOT EXISTS base_portfolio_version bigint;

COMMENT ON COLUMN public.client_portfolios.portfolio_version IS
  'Incremented on every write that changes holdings. An import plan records the value it was computed against and refuses to apply if it has moved.';

COMMENT ON COLUMN public.portfolio_imports.base_portfolio_version IS
  'client_portfolios.portfolio_version as it stood when this plan was built.';
