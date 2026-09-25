-- Does a delete on client_portfolio_holdings actually delete?
--
-- Everything here happens inside a transaction that ends in ROLLBACK. No row
-- is created, and no row is really removed - the delete is attempted, the
-- result inspected, and the whole thing undone.
--
-- It deletes an EXISTING row rather than inserting a probe. An earlier version
-- inserted one and hit a NOT NULL on asset_name, which is the wrong problem to
-- be solving: satisfying the insert contract says nothing about deletes, and
-- deleting a real row is a more faithful test anyway.
--
-- This is the assertion 34 green tests never made. The suite had no case that
-- deleted anything, so a trigger returning NEW on DELETE - NULL there, which
-- silently cancels the row - passed all of them.

BEGIN;

DO $$
DECLARE
  v_id       uuid;
  v_source   text;
  v_survived boolean;
BEGIN
  -- Prefer a manual holding: those are the ones the app deletes, and the
  -- trigger is meant to let them through.
  SELECT id, COALESCE(source, 'MANUAL')
    INTO v_id, v_source
    FROM public.client_portfolio_holdings
   WHERE broker_connection_id IS NULL
   ORDER BY COALESCE(source, 'MANUAL') = 'MANUAL' DESC
   LIMIT 1;

  IF v_id IS NULL THEN
    RAISE NOTICE 'INCONCLUSIVE - no holdings to test against. Add one holding and re-run.';
    RETURN;
  END IF;

  DELETE FROM public.client_portfolio_holdings WHERE id = v_id;

  SELECT EXISTS (SELECT 1 FROM public.client_portfolio_holdings WHERE id = v_id)
    INTO v_survived;

  IF v_survived THEN
    RAISE NOTICE 'FAIL - holding % (source %) survived its own DELETE. The broken trigger is live; apply 20260905060000.', v_id, v_source;
  ELSE
    RAISE NOTICE 'PASS - deletes work. Holding % (source %) was removed, and this transaction now rolls back.', v_id, v_source;
  END IF;
END;
$$;

-- Nothing above is kept.
ROLLBACK;
