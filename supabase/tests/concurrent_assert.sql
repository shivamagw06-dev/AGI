-- After two sessions race to confirm the same plan, exactly one must have won.
--
-- Asserted from committed state rather than from either session's return
-- value, because the question is what the database ended up holding.

BEGIN;
SELECT plan(4);

SELECT is(
  (SELECT count(*) FROM public.client_portfolio_holdings
    WHERE portfolio_id = 'bbbbbbbb-0000-0000-0000-000000000003'
      AND isin = 'INE002A01018'),
  1::bigint,
  'the holding was written exactly once');

SELECT is(
  (SELECT portfolio_version FROM public.client_portfolios
    WHERE id = 'bbbbbbbb-0000-0000-0000-000000000003'),
  2::bigint,
  'portfolio_version incremented exactly once');

SELECT is(
  (SELECT status FROM public.portfolio_imports
    WHERE id = 'dddddddd-0000-0000-0000-000000000003'),
  'confirmed',
  'the plan is confirmed');

SELECT is(
  (SELECT count(*) FROM public.portfolio_imports
    WHERE id = 'dddddddd-0000-0000-0000-000000000003'
      AND confirmed_at IS NOT NULL),
  1::bigint,
  'confirmed exactly once, with one timestamp');

SELECT * FROM finish();
ROLLBACK;
