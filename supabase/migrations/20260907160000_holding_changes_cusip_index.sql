-- holding_changes had one index: (filing_id, change_type).
--
-- Every query that reaches it by CUSIP therefore sequentially scanned the whole
-- table. That includes the ticker propagation trigger dropped in
-- 20260907140000, which ran one such scan per mapping row - 209 scans inside a
-- single statement, which is what actually consumed the two-minute
-- statement_timeout that killed the identifier backfill three times. The
-- companion update on institutional_holdings was never the cost: it had
-- institutional_holdings_cusip_idx and measured 67ms.
--
-- The trigger is gone, but two application paths still reach holding_changes by
-- CUSIP and deserve the index on their own merits:
--
--   saveSecurityMapping - scoped update when an admin corrects a mapping
--   securityDetail      - select ... in (filing_ids) and eq('cusip', ...)
--
-- report_date is included because both callers bound the CUSIP by date; without
-- it the index finds the CUSIP and then filters the rows by hand.

create index if not exists holding_changes_cusip_report_idx
  on public.holding_changes (cusip, report_date desc);
