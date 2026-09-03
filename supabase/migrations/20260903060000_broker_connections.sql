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

-- NOT VALID on purpose. asset_type already exists in production, so this
-- constraint meets rows written long before the vocabulary was defined. A
-- validated constraint would scan them all and fail on the first unknown
-- value with an error naming no row, turning a deploy into a hunt.
--
-- NOT VALID constrains every insert and update from now on while leaving
-- existing rows alone, which is what makes this safe to ship before the data
-- is audited. Nothing is silently converted: legacy values stay exactly as
-- they are until somebody looks at them and decides.
--
-- Once the audit below returns nothing, run:
--
--   ALTER TABLE public.client_portfolio_holdings
--     VALIDATE CONSTRAINT client_portfolio_holdings_asset_type_known;
--
--   SELECT id, user_id, symbol, isin, asset_type
--     FROM public.client_portfolio_holdings
--    WHERE asset_type IS NOT NULL
--      AND asset_type NOT IN ('EQUITY','ETF','MUTUAL_FUND','BOND','REIT',
--                             'INVIT','CASH','OTHER');
--
-- NULL is not listed there because a CHECK passes on NULL: an untyped holding
-- is permitted and is a separate question from a wrongly typed one. Count them
-- separately and do not add NOT NULL until they are resolved and every writer
-- supplies a value:
--
--   SELECT count(*) AS untyped_holdings
--     FROM public.client_portfolio_holdings
--    WHERE asset_type IS NULL;
--
-- NOT VALID is a reprieve, not a permanent exemption. An untouched legacy row
-- stays as it is, but the first UPDATE to one is checked like any other write
-- and will fail. So a bad value sits quietly until somebody edits that
-- holding, and then surfaces as an error in front of a client. Audit soon
-- rather than eventually.
ALTER TABLE public.client_portfolio_holdings
  DROP CONSTRAINT IF EXISTS client_portfolio_holdings_asset_type_known;
ALTER TABLE public.client_portfolio_holdings
  ADD CONSTRAINT client_portfolio_holdings_asset_type_known CHECK (
    asset_type IN ('EQUITY','ETF','MUTUAL_FUND','BOND','REIT','INVIT','CASH','OTHER'))
  NOT VALID;

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
