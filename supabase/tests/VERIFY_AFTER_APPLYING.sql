-- Run after applying. Read-only, changes nothing.
-- Every row should say PASS.

WITH checks AS (
  -- "check" is a reserved word in Postgres, so the column is "item".
  SELECT 'broker_connections table' AS item,
         to_regclass('public.broker_connections') IS NOT NULL AS ok
  UNION ALL SELECT 'broker_connection_secrets table',
         to_regclass('public.broker_connection_secrets') IS NOT NULL
  UNION ALL SELECT 'portfolio_imports table',
         to_regclass('public.portfolio_imports') IS NOT NULL
  UNION ALL SELECT 'portfolio_import_review table',
         to_regclass('public.portfolio_import_review') IS NOT NULL

  UNION ALL SELECT 'create_cas_import_plan()',
         EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'create_cas_import_plan')
  UNION ALL SELECT 'confirm_cas_import()',
         EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'confirm_cas_import')
  UNION ALL SELECT 'discard_cas_import()',
         EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'discard_cas_import')

  UNION ALL SELECT 'client_portfolios.portfolio_version',
         EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'client_portfolios'
                    AND column_name = 'portfolio_version')
  UNION ALL SELECT 'portfolio_imports.expires_at',
         EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name = 'portfolio_imports'
                    AND column_name = 'expires_at')

  -- The one that matters most. The trigger must return OLD on DELETE; the
  -- original returned NEW, which is NULL there and silently cancelled the row.
  UNION ALL SELECT 'delete trigger returns OLD (not the broken version)',
         COALESCE(pg_get_functiondef(
           (SELECT oid FROM pg_proc WHERE proname = 'broker_holdings_are_read_only')
         ) LIKE '%TG_OP%', false)

  -- No asset_type CHECK: it would have rejected every value the app writes.
  UNION ALL SELECT 'no asset_type CHECK constraint (correct)',
         NOT EXISTS (SELECT 1 FROM pg_constraint
                      WHERE conname = 'client_portfolio_holdings_asset_type_known')

  -- Secrets must not be reachable by the browser role.
  UNION ALL SELECT 'broker_connection_secrets hidden from authenticated',
         NOT EXISTS (SELECT 1 FROM pg_policies
                      WHERE tablename = 'broker_connection_secrets'
                        AND 'authenticated' = ANY (roles))

  UNION ALL SELECT 'RLS on portfolio_imports',
         COALESCE((SELECT relrowsecurity FROM pg_class
                    WHERE oid = to_regclass('public.portfolio_imports')), false)
)
SELECT item, CASE WHEN ok THEN 'PASS' ELSE 'FAIL' END AS result
  FROM checks
 ORDER BY (CASE WHEN ok THEN 1 ELSE 0 END), item;
