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
