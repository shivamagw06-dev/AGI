-- All CAS migrations, in order, in ONE transaction.
--
-- Paste this whole file and Run. Because it is wrapped in BEGIN/COMMIT,
-- either every statement applies or none of them do - there is no state
-- where half the schema exists. Running the files individually and out
-- of order is what produced 'relation public.portfolio_imports does not
-- exist': the third file needs the table the second one creates.
--
-- The last migration repairs a trigger installed by the first. Applying
-- them together means the delete bug never exists in this database.
--
-- Generated 2026-09-05T05:26:40Z from main.

BEGIN;

-- ============================================================
-- 20260903060000_broker_connections.sql
-- ============================================================
-- Read-only broker connections, and the holdings they import.
--
-- Two tables rather than one, because a row-level policy cannot hide a column.
-- `broker_connections` is metadata the client is allowed to read - which broker,
-- which account, when it last synced. `broker_connection_secrets` holds the
-- tokens and carries no policy for `authenticated` at all, so the anon key
-- cannot select them under any query. Only the backend, holding service_role,
-- can exchange or refresh a token. Putting an encrypted_access_token column on
-- a client-readable table would mean the browser could fetch the ciphertext,
-- which is a key-rotation problem waiting to happen rather than a safe design.
--
-- AGI never receives a broker password, PIN, TPIN or OTP. The client
-- authenticates on the broker's own domain and the broker returns a code.

CREATE TABLE IF NOT EXISTS public.broker_connections (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                  uuid NOT NULL DEFAULT auth.uid()
                             REFERENCES auth.users(id) ON DELETE CASCADE,
  portfolio_id             uuid REFERENCES public.client_portfolios(id) ON DELETE SET NULL,
  broker                   text NOT NULL,
  -- Masked by the backend before it is written: a display reference such as
  -- "****4821", never the full client code.
  broker_account_reference text,
  scopes                   text[] NOT NULL DEFAULT ARRAY[]::text[],
  status                   text NOT NULL DEFAULT 'pending',
  last_synced_at           timestamptz,
  last_sync_error          text,
  -- A failed sync must not erase a good portfolio, so the last success is kept
  -- separately from the last attempt.
  last_successful_sync_at  timestamptz,
  created_at               timestamptz NOT NULL DEFAULT now(),
  revoked_at               timestamptz,

  CONSTRAINT broker_connections_broker_known CHECK (
    broker IN ('UPSTOX','ZERODHA','ANGELONE','GROWW','ICICIDIRECT')),
  CONSTRAINT broker_connections_status_known CHECK (
    status IN ('pending','active','expired','revoked','error')),
  -- One live connection per broker per user. A second authorisation replaces
  -- the first rather than quietly accumulating duplicate holdings.
  CONSTRAINT broker_connections_one_live UNIQUE (user_id, broker, revoked_at)
);

CREATE TABLE IF NOT EXISTS public.broker_connection_secrets (
  connection_id     uuid PRIMARY KEY
                      REFERENCES public.broker_connections(id) ON DELETE CASCADE,
  access_token_enc  text NOT NULL,
  refresh_token_enc text,
  token_expires_at  timestamptz,
  key_version       text NOT NULL DEFAULT 'v1',
  updated_at        timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.broker_connection_secrets IS
  'Encrypted broker tokens. No policy exists for the authenticated role on '
  'purpose: the browser must never be able to read these, even as ciphertext.';

ALTER TABLE public.broker_connections        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.broker_connection_secrets ENABLE ROW LEVEL SECURITY;

CREATE POLICY broker_connections_own_select ON public.broker_connections
  FOR SELECT TO authenticated USING ((SELECT auth.uid()) = user_id);
-- The client may disconnect. Creating a connection is the backend's job,
-- because only it can complete the token exchange.
CREATE POLICY broker_connections_own_revoke ON public.broker_connections
  FOR UPDATE TO authenticated
  USING ((SELECT auth.uid()) = user_id)
  WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE INDEX IF NOT EXISTS broker_connections_user_idx
  ON public.broker_connections (user_id, broker) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- Imported holdings live in the existing table, not a parallel one.
--
-- client_portfolio_holdings already carries user_id, portfolio_id, isin and
-- instrument_id under working RLS. A second `portfolio_holdings` table would
-- mean two answers to "what does this client own", and the desk spent today
-- proving how that ends: daily_market_history holds three feeds that disagree
-- about split adjustment, and the page showed a five-day-old price because the
-- reader and the writer had different ideas about the same column.
-- ---------------------------------------------------------------------------

ALTER TABLE public.client_portfolio_holdings
  ADD COLUMN IF NOT EXISTS broker_connection_id uuid
    REFERENCES public.broker_connections(id) ON DELETE SET NULL,
  -- MANUAL, CAS, or a broker code. The distinction is load-bearing: a sync
  -- must never overwrite something the client typed.
  ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'MANUAL',
  ADD COLUMN IF NOT EXISTS asset_type text NOT NULL DEFAULT 'EQUITY',
  ADD COLUMN IF NOT EXISTS scheme_code text,
  ADD COLUMN IF NOT EXISTS exchange text,
  ADD COLUMN IF NOT EXISTS as_of_date timestamptz,
  -- A sold position is marked, not deleted: the history is what makes a
  -- return computable, and a disappeared row silently changes past figures.
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS closed_at timestamptz;

-- No asset_type CHECK here, deliberately.
--
-- An earlier version of this migration added one allowing
-- ('EQUITY','ETF','MUTUAL_FUND','BOND','REIT','INVIT','CASH','OTHER'). That
-- vocabulary came from the CAS normaliser and was never checked against what
-- the application already writes, which is lowercase and narrower:
--
--   indian_stock, us_stock, mutual_fund, etf, cash
--     (src/pages/ClientPortfolioIntelligence.jsx, assetLabels)
--
-- The two sets are disjoint. A Postgres CHECK is case-sensitive, so 'etf'
-- fails 'ETF', and indian_stock and us_stock have no member at all. NOT VALID
-- would not have saved it either: it skips the initial scan but enforces on
-- every INSERT and UPDATE afterwards, including updates that never touch the
-- column. Applying it would have broken saveClientHolding's upsert
-- (client_portfolio_holdings has a unique key on portfolio_id, symbol,
-- asset_type, market) and both write paths in record_client_transaction --
-- that is, adding a holding, recording a trade, and editing an existing
-- position. The entire manual holdings feature, which is the only part of this
-- product currently in use.
--
-- Constraining the column needs a decision this migration cannot make. The
-- application vocabulary is narrower than CAS requires: EQUITY maps to
-- indian_stock or us_stock depending on the exchange, and BOND, REIT and INVIT
-- have no equivalent at all. Widening the constraint to accept both spellings
-- would put two vocabularies in one column and hand every reader the job of
-- knowing both.
--
-- So the column stays unconstrained until the vocabularies are unified on
-- purpose. The CAS importer validates its own values before writing
-- (portfolio_import/cas_parser.py _asset_type, server/services/brokers/
-- normalise.js assetTypeOf), so nothing is unchecked in the new path; what is
-- absent is a database-level guarantee, and that is the honest position while
-- two producers disagree about what the values mean.

-- One row per security per connection. The same stock held at two brokers is
-- two lots and stays two lots -- merging them at write time would destroy the
-- per-broker average cost and make a disconnect unpickable. The portfolio view
-- aggregates; the store does not.
CREATE UNIQUE INDEX IF NOT EXISTS client_portfolio_holdings_broker_lot_idx
  ON public.client_portfolio_holdings (portfolio_id, broker_connection_id, isin)
  WHERE broker_connection_id IS NOT NULL AND isin IS NOT NULL;

CREATE INDEX IF NOT EXISTS client_portfolio_holdings_source_idx
  ON public.client_portfolio_holdings (user_id, source) WHERE is_active;

-- Imported rows are the broker's statement of fact, so a client corrects them
-- with a manual adjustment rather than by editing them. Without this the next
-- sync would silently revert the edit and look like data loss.
CREATE OR REPLACE FUNCTION public.broker_holdings_are_read_only()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
  IF OLD.broker_connection_id IS NOT NULL AND auth.uid() IS NOT NULL THEN
    RAISE EXCEPTION
      'holding % was imported from a broker and cannot be edited directly; '
      'record a manual adjustment instead', OLD.id
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS client_portfolio_holdings_broker_readonly
  ON public.client_portfolio_holdings;
CREATE TRIGGER client_portfolio_holdings_broker_readonly
  BEFORE UPDATE OR DELETE ON public.client_portfolio_holdings
  FOR EACH ROW EXECUTE FUNCTION public.broker_holdings_are_read_only();

COMMENT ON COLUMN public.client_portfolio_holdings.source IS
  'MANUAL, CAS, or a broker code. A broker sync writes only rows whose source '
  'matches its own broker; it never touches MANUAL rows.';

-- ============================================================
-- 20260903090000_portfolio_imports.sql
-- ============================================================
-- A record of every statement import, without keeping the statement.
--
-- The fingerprint is a SHA-256 of the uploaded file. It makes a re-upload a
-- no-op instead of a duplicate portfolio, and it is a digest, so the row
-- proves which document was imported without retaining any of it. The PDF
-- itself is parsed in memory and never written anywhere.
--
-- Nothing here stores a password. The client supplies one to open the PDF for
-- the duration of a single request and it is discarded when that request ends.

CREATE TABLE IF NOT EXISTS public.portfolio_imports (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid NOT NULL DEFAULT auth.uid()
                          REFERENCES auth.users(id) ON DELETE CASCADE,
  portfolio_id          uuid REFERENCES public.client_portfolios(id) ON DELETE CASCADE,
  source_type           text NOT NULL,
  statement_date        date,
  statement_fingerprint text NOT NULL,
  status                text NOT NULL DEFAULT 'parsed',
  matched_count         integer NOT NULL DEFAULT 0,
  unmatched_count       integer NOT NULL DEFAULT 0,
  warning_count         integer NOT NULL DEFAULT 0,
  -- The plan the client was shown, kept so a confirmation can be audited
  -- against what was actually presented. Holdings only; no document text.
  plan_summary          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  confirmed_at          timestamptz,

  CONSTRAINT portfolio_imports_source_known CHECK (
    source_type IN ('NSDL','CDSL','CAMS_KFINTECH','BROKER_CSV','UNKNOWN')),
  CONSTRAINT portfolio_imports_status_known CHECK (
    status IN ('parsed','confirmed','discarded','failed')),
  -- The same file imported twice into the same portfolio is one import.
  CONSTRAINT portfolio_imports_fingerprint_once UNIQUE
    (user_id, portfolio_id, statement_fingerprint)
);

-- Rows a statement contained that could not be resolved to an instrument.
-- These must never reach client_portfolio_holdings: a holding nobody can
-- identify is not a holding, and guessing at it silently mis-states a
-- portfolio. They sit here until a human resolves or dismisses them.
CREATE TABLE IF NOT EXISTS public.portfolio_import_review (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  import_id   uuid NOT NULL REFERENCES public.portfolio_imports(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL DEFAULT auth.uid()
                REFERENCES auth.users(id) ON DELETE CASCADE,
  reason      text NOT NULL,
  -- Redacted before it is written: a CAS line carries a PAN and a demat
  -- account number, and this column exists to be looked at.
  excerpt     text,
  payload     jsonb NOT NULL DEFAULT '{}'::jsonb,
  resolved_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.portfolio_imports       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_import_review ENABLE ROW LEVEL SECURITY;

CREATE POLICY portfolio_imports_own ON public.portfolio_imports
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id)
  WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY portfolio_import_review_own ON public.portfolio_import_review
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id)
  WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE INDEX IF NOT EXISTS portfolio_imports_user_idx
  ON public.portfolio_imports (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS portfolio_import_review_open_idx
  ON public.portfolio_import_review (user_id, import_id) WHERE resolved_at IS NULL;

COMMENT ON COLUMN public.portfolio_imports.statement_fingerprint IS
  'SHA-256 of the uploaded file. Makes a re-upload idempotent and identifies '
  'the document without retaining it.';

-- ============================================================
-- 20260903120000_import_plan_expiry.sql
-- ============================================================
-- An unconfirmed import plan is short-lived.
--
-- A plan is a computed view of a portfolio at a moment. Left open it goes
-- stale: the holdings it was computed against move, and confirming it later
-- would write changes the client never reviewed. The application checks the
-- basis digest as well, but an expiry means a forgotten tab stops being
-- confirmable at all rather than relying on that check alone.

ALTER TABLE public.portfolio_imports
  ADD COLUMN IF NOT EXISTS expires_at timestamptz
    NOT NULL DEFAULT (now() + interval '2 hours');

CREATE INDEX IF NOT EXISTS portfolio_imports_open_idx
  ON public.portfolio_imports (user_id, expires_at)
  WHERE status = 'parsed';

COMMENT ON COLUMN public.portfolio_imports.expires_at IS
  'Unconfirmed plans stop being confirmable after this. A plan describes a '
  'portfolio state; once that state can have moved, the plan is not safe to '
  'apply without re-review.';

-- Sweep expired plans. Nothing was written for them, so this discards a
-- computation and never a holding.
CREATE OR REPLACE FUNCTION public.expire_stale_import_plans()
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  affected integer;
BEGIN
  UPDATE public.portfolio_imports
     SET status = 'discarded'
   WHERE status = 'parsed' AND expires_at <= now();
  GET DIAGNOSTICS affected = ROW_COUNT;
  RETURN affected;
END;
$$;

REVOKE ALL ON FUNCTION public.expire_stale_import_plans() FROM public;
GRANT EXECUTE ON FUNCTION public.expire_stale_import_plans() TO service_role;

-- ============================================================
-- 20260903150000_portfolio_version.sql
-- ============================================================
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

-- ============================================================
-- 20260903180000_cas_import_rpcs.sql
-- ============================================================
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

-- ============================================================
-- 20260905060000_fix_holdings_delete_trigger.sql
-- ============================================================
-- Deletes on client_portfolio_holdings were being silently cancelled.
--
-- 20260903060000 attached broker_holdings_are_read_only as
--
--   BEFORE UPDATE OR DELETE ON public.client_portfolio_holdings
--
-- and the function ended with RETURN NEW. On UPDATE that is correct. On DELETE
-- there is no NEW row, so NEW is NULL, and returning NULL from a BEFORE trigger
-- tells Postgres to skip the operation for that row. Not to raise -- to skip.
--
-- The result is that every delete on this table succeeded loudly and did
-- nothing: no error, no rows affected, and a caller with no way to tell. It
-- applied to every row, not only broker-imported ones, because the cancellation
-- happens after the guard clause has decided the row is fine.
--
-- Two paths were affected, both in the manual-holdings feature, which is the
-- only part of the product currently in use:
--
--   * deleteClientHolding (src/lib/clientPortfolio.js) reported success while
--     the holding stayed in the portfolio.
--   * the full-exit SELL branch of record_client_portfolio_transaction booked
--     the trade and left the position in place, so exposure, returns and TWR
--     would have been computed over a holding the client had sold.
--
-- The fix returns OLD for DELETE and NEW for everything else. A BEFORE DELETE
-- trigger must return OLD to allow the delete to proceed.
--
-- CREATE OR REPLACE so this repairs the function whether or not 20260903060000
-- has already been applied.

CREATE OR REPLACE FUNCTION public.broker_holdings_are_read_only()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
  IF OLD.broker_connection_id IS NOT NULL AND auth.uid() IS NOT NULL THEN
    RAISE EXCEPTION
      'holding % was imported from a broker and cannot be edited directly; '
      'record a manual adjustment instead', OLD.id
      USING ERRCODE = 'check_violation';
  END IF;
  -- NEW is NULL on DELETE, and returning NULL from a BEFORE trigger cancels
  -- the row silently. OLD is what allows a delete to proceed.
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$;

COMMENT ON FUNCTION public.broker_holdings_are_read_only() IS
  'Blocks direct edits to broker-imported holdings. Returns OLD on DELETE: returning NEW there is NULL, which silently cancels the delete instead of allowing it.';

COMMIT;
