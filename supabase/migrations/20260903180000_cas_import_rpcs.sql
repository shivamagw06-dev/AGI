-- Confirming a CAS import, in one transaction.
--
-- Three narrow functions instead of a sequence of client writes. A confirmation
-- that ran as several round trips could be interrupted between them, and the
-- portfolio would be left holding half a statement with no record of which
-- half. A function body is a single transaction: every failure below rolls the
-- whole thing back.
--
-- SECURITY INVOKER throughout. These functions read and write only tables the
-- caller already has row-level policies on, so the policies do the enforcement
-- and there is no privilege to escalate. A DEFINER function here would have to
-- re-implement ownership checks that RLS already performs correctly, and would
-- fail open if one were forgotten. Identity comes from auth.uid() and never
-- from an argument.
--
-- The secrets table is deliberately untouched by all of this. Nothing here
-- reads broker_connection_secrets, and no function returns a token.

-- ---------------------------------------------------------------------------
-- create_cas_import_plan
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.create_cas_import_plan(
  p_portfolio_id  uuid,
  p_source_type   text,
  p_statement_date date,
  p_fingerprint   text,
  p_plan          jsonb,
  p_expires_at    timestamptz
) RETURNS TABLE (import_id uuid, base_version bigint)
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_user    uuid := auth.uid();
  v_version bigint;
  v_id      uuid;
BEGIN
  IF v_user IS NULL THEN
    RAISE EXCEPTION 'authentication_required' USING ERRCODE = '28000';
  END IF;

  -- The version the plan was computed against. Read under a share lock so a
  -- concurrent confirmation cannot bump it between this read and the insert.
  SELECT p.portfolio_version INTO v_version
    FROM public.client_portfolios p
   WHERE p.id = p_portfolio_id AND p.user_id = v_user
     FOR SHARE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'portfolio_not_found' USING ERRCODE = 'P0002';
  END IF;

  INSERT INTO public.portfolio_imports (
    user_id, portfolio_id, source_type, statement_date,
    statement_fingerprint, plan_summary, status, expires_at,
    base_portfolio_version, matched_count, unmatched_count, warning_count
  ) VALUES (
    v_user, p_portfolio_id, p_source_type, p_statement_date,
    p_fingerprint, COALESCE(p_plan, '{}'::jsonb), 'parsed', p_expires_at,
    v_version,
    COALESCE(jsonb_array_length(p_plan->'adds'), 0)
      + COALESCE(jsonb_array_length(p_plan->'updates'), 0),
    COALESCE(jsonb_array_length(p_plan->'review_queue'), 0),
    COALESCE(jsonb_array_length(p_plan->'warnings'), 0)
  )
  RETURNING id INTO v_id;

  RETURN QUERY SELECT v_id, v_version;
END;
$$;

-- ---------------------------------------------------------------------------
-- confirm_cas_import
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.confirm_cas_import(
  p_import_id        uuid,
  p_selected_row_ids text[]
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_user        uuid := auth.uid();
  v_import      public.portfolio_imports%ROWTYPE;
  v_version     bigint;
  v_plan        jsonb;
  v_selected    text[] := COALESCE(p_selected_row_ids, ARRAY[]::text[]);
  v_row         jsonb;
  v_holding     jsonb;
  v_inserted    integer := 0;
  v_updated     integer := 0;
  v_closed      integer := 0;
  v_unknown     text[] := ARRAY[]::text[];
  v_reviewed    integer := 0;
  v_existing_id uuid;
BEGIN
  IF v_user IS NULL THEN
    RAISE EXCEPTION 'authentication_required' USING ERRCODE = '28000';
  END IF;
  IF array_length(v_selected, 1) IS NULL THEN
    RAISE EXCEPTION 'nothing_selected' USING ERRCODE = 'P0001';
  END IF;

  -- Lock the plan first. Two confirmations of the same import serialise here,
  -- and the second finds status already 'confirmed' below.
  SELECT * INTO v_import
    FROM public.portfolio_imports
   WHERE id = p_import_id
     FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'import_plan_missing' USING ERRCODE = 'P0002';
  END IF;
  -- RLS already restricts the row, but say it explicitly: a caller asking
  -- about someone else's plan gets a refusal, not a not-found.
  IF v_import.user_id <> v_user THEN
    RAISE EXCEPTION 'not_your_import' USING ERRCODE = '42501';
  END IF;
  IF v_import.status <> 'parsed' THEN
    RAISE EXCEPTION 'import_already_resolved' USING ERRCODE = 'P0001';
  END IF;
  IF v_import.expires_at IS NOT NULL AND v_import.expires_at <= now() THEN
    RAISE EXCEPTION 'import_expired' USING ERRCODE = 'P0001';
  END IF;

  -- Lock the portfolio. Everything below writes holdings under this lock, so
  -- two imports into one portfolio cannot interleave.
  SELECT p.portfolio_version INTO v_version
    FROM public.client_portfolios p
   WHERE p.id = v_import.portfolio_id AND p.user_id = v_user
     FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'portfolio_not_found' USING ERRCODE = 'P0002';
  END IF;
  IF v_import.base_portfolio_version IS NOT NULL
     AND v_version <> v_import.base_portfolio_version THEN
    -- The portfolio moved after the client reviewed the plan. Applying it now
    -- would write changes they never saw.
    RAISE EXCEPTION 'portfolio_changed' USING ERRCODE = 'P0001';
  END IF;

  v_plan := COALESCE(v_import.plan_summary, '{}'::jsonb);

  -- Every selected id must exist in the stored plan. An id we did not issue
  -- means the client saw something we did not produce.
  SELECT COALESCE(array_agg(sel), ARRAY[]::text[]) INTO v_unknown
    FROM unnest(v_selected) AS sel
   WHERE sel NOT IN (
     SELECT jsonb_array_elements(COALESCE(v_plan->'adds', '[]'::jsonb))->>'row_id'
     UNION ALL
     SELECT jsonb_array_elements(COALESCE(v_plan->'updates', '[]'::jsonb))->>'row_id'
     UNION ALL
     SELECT jsonb_array_elements(COALESCE(v_plan->'closures', '[]'::jsonb))->>'row_id'
   );

  ---------------------------------------------------------------------------
  -- New holdings
  ---------------------------------------------------------------------------
  FOR v_row IN
    SELECT value FROM jsonb_array_elements(COALESCE(v_plan->'adds', '[]'::jsonb))
     WHERE value->>'row_id' = ANY (v_selected)
  LOOP
    v_holding := v_row->'holding';
    INSERT INTO public.client_portfolio_holdings (
      user_id, portfolio_id, source, broker_connection_id,
      isin, symbol, asset_name, asset_type, exchange,
      quantity, average_cost, as_of_date, is_active
    ) VALUES (
      v_user, v_import.portfolio_id, v_import.source_type, NULL,
      v_holding->>'isin', v_holding->>'symbol', v_holding->>'name',
      COALESCE(v_holding->>'asset_type', 'EQUITY'), v_holding->>'exchange',
      NULLIF(v_holding->>'quantity', '')::numeric,
      NULLIF(v_holding->>'average_cost', '')::numeric,
      v_import.statement_date, true
    );
    v_inserted := v_inserted + 1;
  END LOOP;

  ---------------------------------------------------------------------------
  -- Updated holdings
  ---------------------------------------------------------------------------
  FOR v_row IN
    SELECT value FROM jsonb_array_elements(COALESCE(v_plan->'updates', '[]'::jsonb))
     WHERE value->>'row_id' = ANY (v_selected)
  LOOP
    v_existing_id := NULLIF(v_row->>'id', '')::uuid;
    v_holding := v_row->'holding';
    -- Scoped to this user and to a row the import owns. A manual holding is
    -- never matched here because the plan never proposes one.
    UPDATE public.client_portfolio_holdings h
       SET quantity     = COALESCE(NULLIF(v_holding->>'quantity', '')::numeric, h.quantity),
           average_cost = COALESCE(NULLIF(v_holding->>'average_cost', '')::numeric, h.average_cost),
           as_of_date   = v_import.statement_date,
           updated_at   = now()
     WHERE h.id = v_existing_id
       AND h.user_id = v_user
       AND h.portfolio_id = v_import.portfolio_id
       AND COALESCE(h.source, 'MANUAL') <> 'MANUAL';
    IF FOUND THEN
      v_updated := v_updated + 1;
    END IF;
  END LOOP;

  ---------------------------------------------------------------------------
  -- Closures, only where explicitly selected
  ---------------------------------------------------------------------------
  FOR v_row IN
    SELECT value FROM jsonb_array_elements(COALESCE(v_plan->'closures', '[]'::jsonb))
     WHERE value->>'row_id' = ANY (v_selected)
  LOOP
    v_existing_id := NULLIF(v_row->>'id', '')::uuid;
    UPDATE public.client_portfolio_holdings h
       SET is_active  = false,
           closed_at  = now(),
           as_of_date = v_import.statement_date,
           updated_at = now()
     WHERE h.id = v_existing_id
       AND h.user_id = v_user
       AND h.portfolio_id = v_import.portfolio_id
       AND COALESCE(h.source, 'MANUAL') <> 'MANUAL';
    IF FOUND THEN
      v_closed := v_closed + 1;
    END IF;
  END LOOP;

  ---------------------------------------------------------------------------
  -- Unmatched rows go to review, never to holdings
  ---------------------------------------------------------------------------
  INSERT INTO public.portfolio_import_review (import_id, user_id, reason, excerpt, payload)
  SELECT p_import_id, v_user,
         COALESCE(value->>'reason', 'unparsed'),
         value->>'excerpt',
         COALESCE(value, '{}'::jsonb)
    FROM jsonb_array_elements(COALESCE(v_plan->'review_queue', '[]'::jsonb));
  GET DIAGNOSTICS v_reviewed = ROW_COUNT;

  ---------------------------------------------------------------------------
  -- Audit, version, and the plan itself
  ---------------------------------------------------------------------------
  IF v_inserted + v_updated + v_closed > 0 THEN
    UPDATE public.client_portfolios
       SET portfolio_version = portfolio_version + 1
     WHERE id = v_import.portfolio_id AND user_id = v_user;
    v_version := v_version + 1;
  END IF;

  UPDATE public.portfolio_imports
     SET status = 'confirmed',
         confirmed_at = now(),
         -- Counts of what was actually written, not what was proposed.
         matched_count = v_inserted + v_updated,
         unmatched_count = v_reviewed
   WHERE id = p_import_id;

  RETURN jsonb_build_object(
    'ok', true,
    'inserted', v_inserted,
    'updated', v_updated,
    'closed', v_closed,
    'review_queued', v_reviewed,
    'unknown_row_ids', to_jsonb(v_unknown),
    'portfolio_version', v_version
  );
END;
$$;

-- ---------------------------------------------------------------------------
-- discard_cas_import
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.discard_cas_import(p_import_id uuid)
RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_user uuid := auth.uid();
  v_rows integer;
BEGIN
  IF v_user IS NULL THEN
    RAISE EXCEPTION 'authentication_required' USING ERRCODE = '28000';
  END IF;

  UPDATE public.portfolio_imports
     SET status = 'discarded'
   WHERE id = p_import_id AND user_id = v_user AND status = 'parsed';
  GET DIAGNOSTICS v_rows = ROW_COUNT;

  RETURN jsonb_build_object('ok', v_rows > 0, 'discarded', v_rows);
END;
$$;

-- ---------------------------------------------------------------------------
-- Execution rights
-- ---------------------------------------------------------------------------
REVOKE ALL ON FUNCTION public.create_cas_import_plan(uuid, text, date, text, jsonb, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.confirm_cas_import(uuid, text[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.discard_cas_import(uuid) FROM PUBLIC;

-- The BFF holds the service role and calls these on a signed-in user's behalf.
-- `authenticated` is granted as well because the functions are INVOKER and RLS
-- confines them to the caller's own rows either way, so a direct call from a
-- session token is safe and gains nothing a client could not already do.
GRANT EXECUTE ON FUNCTION public.create_cas_import_plan(uuid, text, date, text, jsonb, timestamptz) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.confirm_cas_import(uuid, text[]) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.discard_cas_import(uuid) TO authenticated, service_role;
