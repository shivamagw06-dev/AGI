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
