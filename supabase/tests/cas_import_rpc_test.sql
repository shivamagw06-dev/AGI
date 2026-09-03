-- Transactional behaviour of confirm_cas_import, against a real Postgres.
--
-- Run by .github/workflows/db-tests.yml against a Postgres service container,
-- because these assertions are about locking, rollback and RLS and none of
-- those can be checked by reading the SQL.
--
-- auth.uid() is stubbed by setting request.jwt.claims, which is how Supabase
-- resolves it, so the policies and the functions see a real identity.

BEGIN;
SELECT plan(34);

-- ---------------------------------------------------------------------------
-- Fixtures: two users, so isolation can be asserted rather than assumed.
-- ---------------------------------------------------------------------------
-- Identifiers are written out rather than held in a temp table: once a test
-- switches the session role to `authenticated`, a temp table created as
-- postgres is no longer readable, and the failure surfaces as an unrelated
-- 'permission denied for table ids' several assertions later.
\set user_a '11111111-1111-1111-1111-111111111111'
\set user_b '22222222-2222-2222-2222-222222222222'
\set folio_a 'aaaaaaaa-0000-0000-0000-000000000001'
\set folio_b 'aaaaaaaa-0000-0000-0000-000000000002'

CREATE OR REPLACE FUNCTION act_as(p_user uuid) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
  PERFORM set_config('request.jwt.claims',
                     json_build_object('sub', p_user::text)::text, true);
  PERFORM set_config('role', 'authenticated', true);
END;
$$;

INSERT INTO auth.users (id, email)
VALUES (:'user_a'::uuid, 'a@example.test') ON CONFLICT DO NOTHING;
INSERT INTO auth.users (id, email)
VALUES (:'user_b'::uuid, 'b@example.test') ON CONFLICT DO NOTHING;

INSERT INTO public.client_portfolios (id, user_id, name, portfolio_version)
VALUES (:'folio_a'::uuid, :'user_a'::uuid, 'A', 1);
INSERT INTO public.client_portfolios (id, user_id, name, portfolio_version)
VALUES (:'folio_b'::uuid, :'user_b'::uuid, 'B', 1);

-- One imported lot and one manual lot, so protection can be asserted.
INSERT INTO public.client_portfolio_holdings
  (id, user_id, portfolio_id, source, isin, asset_name, quantity, average_cost, is_active)
VALUES ('cccccccc-0000-0000-0000-000000000001', :'user_a'::uuid, :'folio_a'::uuid,
        'NSDL', 'INE002A01018', 'Reliance', 25, 2715.4, true);
INSERT INTO public.client_portfolio_holdings
  (id, user_id, portfolio_id, source, isin, asset_name, quantity, average_cost, is_active)
VALUES ('cccccccc-0000-0000-0000-000000000002', :'user_a'::uuid, :'folio_a'::uuid,
        'MANUAL', 'INE009A01021', 'Infosys (typed by client)', 10, 1500, true);

-- A plan proposing one add, one update and one closure.
CREATE OR REPLACE FUNCTION make_plan(p_user uuid, p_folio uuid, p_version bigint)
RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE v_id uuid;
BEGIN
  INSERT INTO public.portfolio_imports (
    user_id, portfolio_id, source_type, statement_date, statement_fingerprint,
    plan_summary, status, expires_at, base_portfolio_version)
  VALUES (
    -- A distinct fingerprint per plan. Reusing one trips
    -- portfolio_imports_fingerprint_once, which is correct behaviour and the
    -- subject of its own assertion; here it would only mask the test below it.
    p_user, p_folio, 'NSDL', DATE '2026-08-31', 'fp-' || gen_random_uuid()::text,
    jsonb_build_object(
      'source', 'NSDL',
      'adds', jsonb_build_array(jsonb_build_object(
        'row_id', 'add-1',
        'holding', jsonb_build_object('isin', 'INE040A01034', 'name', 'HDFC Bank',
                                      'quantity', 100, 'average_cost', 700.8,
                                      'asset_type', 'EQUITY'))),
      'updates', jsonb_build_array(jsonb_build_object(
        'row_id', 'upd-1',
        'id', 'cccccccc-0000-0000-0000-000000000001',
        'holding', jsonb_build_object('quantity', 30, 'average_cost', 2715.4))),
      'closures', jsonb_build_array(jsonb_build_object(
        'row_id', 'cls-1',
        'id', 'cccccccc-0000-0000-0000-000000000001')),
      'review_queue', jsonb_build_array(jsonb_build_object(
        'reason', 'isin_line_did_not_parse', 'excerpt', 'masked'))),
    'parsed', now() + interval '1 hour', p_version)
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$;

-- ---------------------------------------------------------------------------
SELECT act_as(:'user_a'::uuid);

-- 1-3: a straightforward confirmation
DO $$
DECLARE v_import uuid; v_out jsonb;
BEGIN
  v_import := make_plan('11111111-1111-1111-1111-111111111111',
                        'aaaaaaaa-0000-0000-0000-000000000001', 1);
  v_out := public.confirm_cas_import(v_import, ARRAY['add-1', 'upd-1']);
  CREATE TEMP TABLE first_run AS SELECT v_import AS id, v_out AS out;
END;
$$;

SELECT is((SELECT (out->>'inserted')::int FROM first_run), 1, 'one holding inserted');
SELECT is((SELECT (out->>'updated')::int FROM first_run), 1, 'one holding updated');
SELECT is((SELECT (out->>'closed')::int FROM first_run), 0,
          'a closure not selected is not applied');

-- 4: the version moved exactly once
SELECT is((SELECT portfolio_version FROM public.client_portfolios
            WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001'), 2::bigint,
          'portfolio_version incremented once');

-- 5-6: the writes actually landed
SELECT is((SELECT quantity FROM public.client_portfolio_holdings
            WHERE id = 'cccccccc-0000-0000-0000-000000000001'), 30::numeric,
          'quantity taken from the stored plan');
SELECT is((SELECT count(*) FROM public.client_portfolio_holdings
            WHERE portfolio_id = 'aaaaaaaa-0000-0000-0000-000000000001'
              AND isin = 'INE040A01034'), 1::bigint, 'new holding inserted');

-- 7: the manual holding is untouched
SELECT is((SELECT quantity FROM public.client_portfolio_holdings
            WHERE id = 'cccccccc-0000-0000-0000-000000000002'), 10::numeric,
          'a manual holding is never written by an import');

-- 8: unmatched rows went to review, not to holdings
SELECT is((SELECT count(*) FROM public.portfolio_import_review
            WHERE import_id = (SELECT id FROM first_run)), 1::bigint,
          'unmatched rows are queued for review');
SELECT is((SELECT count(*) FROM public.client_portfolio_holdings
            WHERE asset_name = 'masked'), 0::bigint,
          'an unmatched row never becomes a holding');

-- 9: audit counts match what was written
SELECT is((SELECT matched_count FROM public.portfolio_imports
            WHERE id = (SELECT id FROM first_run)), 2,
          'audit matched_count equals inserts plus updates');
SELECT is((SELECT status FROM public.portfolio_imports
            WHERE id = (SELECT id FROM first_run)), 'confirmed',
          'plan marked confirmed');

-- 10: confirming twice
SELECT throws_ok(
  format('SELECT public.confirm_cas_import(%L::uuid, ARRAY[''add-1''])',
         (SELECT id FROM first_run)),
  'import_already_resolved', 'a plan cannot be confirmed twice');

-- 11: expiry
DO $$
DECLARE v_id uuid;
BEGIN
  v_id := make_plan('11111111-1111-1111-1111-111111111111',
                    'aaaaaaaa-0000-0000-0000-000000000001', 2);
  UPDATE public.portfolio_imports SET expires_at = now() - interval '1 minute'
   WHERE id = v_id;
  CREATE TEMP TABLE expired AS SELECT v_id AS id;
END;
$$;
SELECT throws_ok(
  format('SELECT public.confirm_cas_import(%L::uuid, ARRAY[''add-1''])',
         (SELECT id FROM expired)),
  'import_expired', 'an expired plan is refused');

-- 12: a stale base version
DO $$
DECLARE v_id uuid;
BEGIN
  v_id := make_plan('11111111-1111-1111-1111-111111111111',
                    'aaaaaaaa-0000-0000-0000-000000000001', 99);
  CREATE TEMP TABLE stale AS SELECT v_id AS id;
END;
$$;
SELECT throws_ok(
  format('SELECT public.confirm_cas_import(%L::uuid, ARRAY[''add-1''])',
         (SELECT id FROM stale)),
  'portfolio_changed', 'a portfolio that moved invalidates the plan');

-- 13-14: empty and unknown selections
DO $$
DECLARE v_id uuid;
BEGIN
  v_id := make_plan('11111111-1111-1111-1111-111111111111',
                    'aaaaaaaa-0000-0000-0000-000000000001', 2);
  CREATE TEMP TABLE fresh AS SELECT v_id AS id;
END;
$$;
SELECT throws_ok(
  format('SELECT public.confirm_cas_import(%L::uuid, ARRAY[]::text[])',
         (SELECT id FROM fresh)),
  'nothing_selected', 'an empty selection is refused');

-- 15-17: unknown ids are reported, valid ones still applied
DO $$
DECLARE v_out jsonb;
BEGIN
  v_out := public.confirm_cas_import((SELECT id FROM fresh),
                                     ARRAY['add-1', 'add-1', 'nope']);
  CREATE TEMP TABLE mixed AS SELECT v_out AS out;
END;
$$;
SELECT is((SELECT (out->>'inserted')::int FROM mixed), 1,
          'a duplicated row id is applied once');
SELECT is((SELECT jsonb_array_length(out->'unknown_row_ids') FROM mixed), 1,
          'an unknown row id is reported');
SELECT is((SELECT out->'unknown_row_ids'->>0 FROM mixed), 'nope',
          'the unknown id is named');

-- 18-20: closures apply only when explicitly selected
DO $$
DECLARE v_id uuid; v_out jsonb;
BEGIN
  v_id := make_plan('11111111-1111-1111-1111-111111111111',
                    'aaaaaaaa-0000-0000-0000-000000000001', 3);
  v_out := public.confirm_cas_import(v_id, ARRAY['cls-1']);
  CREATE TEMP TABLE closed AS SELECT v_out AS out;
END;
$$;
SELECT is((SELECT (out->>'closed')::int FROM closed), 1, 'a selected closure applies');
SELECT is((SELECT is_active FROM public.client_portfolio_holdings
            WHERE id = 'cccccccc-0000-0000-0000-000000000001'), false,
          'a closed holding is inactive');
SELECT isnt((SELECT closed_at FROM public.client_portfolio_holdings
              WHERE id = 'cccccccc-0000-0000-0000-000000000001'), NULL,
            'a closed holding is marked, not deleted');

-- 21-23: cross-user isolation
DO $$
DECLARE v_id uuid;
BEGIN
  PERFORM act_as('22222222-2222-2222-2222-222222222222');
  v_id := make_plan('22222222-2222-2222-2222-222222222222',
                    'aaaaaaaa-0000-0000-0000-000000000002', 1);
  CREATE TEMP TABLE b_plan AS SELECT v_id AS id;
  PERFORM act_as('11111111-1111-1111-1111-111111111111');
END;
$$;
SELECT throws_ok(
  format('SELECT public.confirm_cas_import(%L::uuid, ARRAY[''add-1''])',
         (SELECT id FROM b_plan)),
  'import_plan_missing', 'user A cannot even see user B''s plan');

SELECT is((SELECT count(*) FROM public.portfolio_imports
            WHERE user_id = '22222222-2222-2222-2222-222222222222'), 0::bigint,
          'RLS hides another user''s imports entirely');
SELECT is((SELECT count(*) FROM public.client_portfolio_holdings
            WHERE user_id = '22222222-2222-2222-2222-222222222222'), 0::bigint,
          'RLS hides another user''s holdings entirely');

-- 24: an unauthenticated caller gets nothing
SELECT set_config('request.jwt.claims', NULL, true);
SELECT throws_ok(
  'SELECT public.confirm_cas_import(gen_random_uuid(), ARRAY[''x''])',
  'authentication_required', 'an anonymous caller is refused');

-- 25-26: the functions never expose secrets
SELECT act_as(:'user_a'::uuid);
SELECT is(
  (SELECT count(*) FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN ('create_cas_import_plan','confirm_cas_import','discard_cas_import')
      AND p.prosecdef), 0::bigint,
  'no import function is SECURITY DEFINER');
SELECT is(
  (SELECT count(*) FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN ('create_cas_import_plan','confirm_cas_import','discard_cas_import')
      AND pg_get_functiondef(p.oid) LIKE '%broker_connection_secrets%'), 0::bigint,
  'no import function reads the secrets table');

-- ---------------------------------------------------------------------------
-- Rollback. A function body is one statement to the caller, so a failure on a
-- later action must undo the earlier ones. This needs no second session:
-- Postgres rolls the whole call back, and pgTAP's throws_ok wraps it in a
-- subtransaction so the outer test survives to inspect the wreckage.
-- ---------------------------------------------------------------------------
DO $$
DECLARE v_id uuid;
BEGIN
  -- Two adds. The first is valid; the second carries an asset_type the CHECK
  -- constraint rejects, so it fails after the first has already been written.
  INSERT INTO public.portfolio_imports (
    user_id, portfolio_id, source_type, statement_date, statement_fingerprint,
    plan_summary, status, expires_at, base_portfolio_version)
  VALUES (
    '11111111-1111-1111-1111-111111111111',
    'aaaaaaaa-0000-0000-0000-000000000001',
    'NSDL', DATE '2026-08-31', 'fp-rollback-' || gen_random_uuid()::text,
    jsonb_build_object(
      'source', 'NSDL',
      'adds', jsonb_build_array(
        jsonb_build_object('row_id', 'good-1',
          'holding', jsonb_build_object('isin', 'INE123A01016', 'name', 'Written first',
                                        'quantity', 5, 'asset_type', 'EQUITY')),
        jsonb_build_object('row_id', 'bad-1',
          'holding', jsonb_build_object('isin', 'INE456A01017', 'name', 'Fails the check',
                                        'quantity', 5, 'asset_type', 'NOT_AN_ASSET_TYPE'))),
      'updates', '[]'::jsonb, 'closures', '[]'::jsonb, 'review_queue', '[]'::jsonb),
    'parsed', now() + interval '1 hour',
    (SELECT portfolio_version FROM public.client_portfolios
      WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001'))
  RETURNING id INTO v_id;
  CREATE TEMP TABLE rb AS
    SELECT v_id AS id,
           (SELECT portfolio_version FROM public.client_portfolios
             WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001') AS version_before,
           (SELECT count(*) FROM public.client_portfolio_holdings
             WHERE portfolio_id = 'aaaaaaaa-0000-0000-0000-000000000001') AS holdings_before,
           (SELECT count(*) FROM public.portfolio_import_review) AS review_before;
END;
$$;

SELECT throws_ok(
  format('SELECT public.confirm_cas_import(%L::uuid, ARRAY[''good-1'',''bad-1''])',
         (SELECT id FROM rb)),
  '23514', 'a constraint failure on a later action raises');

SELECT is((SELECT count(*) FROM public.client_portfolio_holdings
            WHERE portfolio_id = 'aaaaaaaa-0000-0000-0000-000000000001'),
          (SELECT holdings_before FROM rb),
          'the earlier holding was rolled back, not left behind');

SELECT is((SELECT count(*) FROM public.client_portfolio_holdings
            WHERE asset_name = 'Written first'), 0::bigint,
          'the row written before the failure is gone');

SELECT is((SELECT portfolio_version FROM public.client_portfolios
            WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001'),
          (SELECT version_before FROM rb),
          'portfolio_version was not incremented');

SELECT is((SELECT status FROM public.portfolio_imports WHERE id = (SELECT id FROM rb)),
          'parsed', 'the plan remains unconfirmed and can be retried');

SELECT is((SELECT confirmed_at FROM public.portfolio_imports WHERE id = (SELECT id FROM rb)),
          NULL, 'no confirmation timestamp was recorded');

SELECT is((SELECT count(*) FROM public.portfolio_import_review),
          (SELECT review_before FROM rb),
          'audit and review rows were rolled back too');

SELECT * FROM finish();
ROLLBACK;
