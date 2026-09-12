-- Committed fixtures for the concurrent-confirmation test.
--
-- The pgTAP suite runs inside a transaction it rolls back, which is right for
-- everything except this: two sessions cannot see each other's uncommitted
-- work, so proving that exactly one confirmation wins needs data that is
-- actually committed.

INSERT INTO auth.users (id, email)
VALUES ('33333333-3333-3333-3333-333333333333', 'race@example.test')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.client_portfolios (id, user_id, name, portfolio_version)
VALUES ('bbbbbbbb-0000-0000-0000-000000000003',
        '33333333-3333-3333-3333-333333333333', 'Race', 1)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.portfolio_imports (
  id, user_id, portfolio_id, source_type, statement_date, statement_fingerprint,
  plan_summary, status, expires_at, base_portfolio_version)
VALUES (
  'dddddddd-0000-0000-0000-000000000003',
  '33333333-3333-3333-3333-333333333333',
  'bbbbbbbb-0000-0000-0000-000000000003',
  'NSDL', DATE '2026-08-31', 'fp-race',
  jsonb_build_object(
    'source', 'NSDL',
    'adds', jsonb_build_array(jsonb_build_object(
      'row_id', 'race-add',
      'holding', jsonb_build_object('isin', 'INE002A01018', 'name', 'Reliance',
                                    'quantity', 10, 'average_cost', 2700,
                                    'asset_type', 'EQUITY'))),
    'updates', '[]'::jsonb, 'closures', '[]'::jsonb, 'review_queue', '[]'::jsonb),
  'parsed', now() + interval '1 hour', 1)
ON CONFLICT (id) DO NOTHING;
