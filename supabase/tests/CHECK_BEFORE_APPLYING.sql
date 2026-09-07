-- Run this in the Supabase SQL editor BEFORE applying any CAS migration.
-- Read-only. It changes nothing.
--
-- Question 1: has 20260903060000 already been applied, and is the broken
-- delete trigger live?

SELECT
  CASE
    WHEN NOT EXISTS (
      SELECT 1 FROM pg_trigger
       WHERE tgname = 'client_portfolio_holdings_broker_readonly'
    )
      THEN 'NOT APPLIED — deletes are fine. Apply 20260905060000 together with 20260903060000 and nothing breaks.'
    WHEN pg_get_functiondef(
           (SELECT oid FROM pg_proc WHERE proname = 'broker_holdings_are_read_only')
         ) LIKE '%TG_OP%'
      THEN 'APPLIED AND ALREADY FIXED — the trigger returns OLD on DELETE.'
    ELSE 'APPLIED AND BROKEN — every DELETE on client_portfolio_holdings is being silently cancelled right now. Apply 20260905060000 immediately.'
  END AS delete_trigger_status;


-- Question 2: which CAS objects already exist. Anything false has not been
-- applied yet.

SELECT
  to_regclass('public.broker_connections')        IS NOT NULL AS broker_connections,
  to_regclass('public.broker_connection_secrets') IS NOT NULL AS broker_secrets,
  to_regclass('public.portfolio_imports')         IS NOT NULL AS portfolio_imports,
  to_regclass('public.portfolio_import_review')   IS NOT NULL AS import_review,
  EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'confirm_cas_import') AS confirm_rpc,
  EXISTS (SELECT 1 FROM information_schema.columns
           WHERE table_name = 'client_portfolios'
             AND column_name = 'portfolio_version')               AS portfolio_version;


-- Question 3: the asset_type audit, still worth running.
-- The CHECK constraint that would have rejected these was removed before
-- merge, so nothing here blocks a deploy. It tells you what the column holds.

SELECT COALESCE(asset_type, '<NULL>') AS asset_type, count(*) AS rows
  FROM public.client_portfolio_holdings
 GROUP BY asset_type
 ORDER BY rows DESC;
