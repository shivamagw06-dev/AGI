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
