-- A holding's identity includes whether it is shares or principal.
--
-- The uniqueness rule and the code that deduplicates against it disagreed.
-- collapseDuplicateRows keys a line by (cusip, title_of_class, share_type,
-- put_call); the index left share_type out. So a manager reporting the same
-- CUSIP and class both as SH and as PRN - an equity position and a convertible
-- note, which is a normal thing to hold - produced two rows the code
-- considered distinct and the index considered identical.
--
-- Postgres then refused the whole batch:
--
--   duplicate key value violates unique constraint
--   institutional_holdings_filing_security_uq
--   ON CONFLICT DO UPDATE command cannot affect row a second time
--
-- and the manager was not ingested at all. Two of fifty failed this way in the
-- run of 2026-09-08, and the signal rebuild that follows ingestion failed with
-- them.
--
-- The index is the side that was wrong. A thousand shares and a thousand
-- dollars of principal are different holdings with different values and
-- different prices; merging them would understate one and invent the other.
drop index if exists public.institutional_holdings_filing_security_uq;

create unique index institutional_holdings_filing_security_uq
  on public.institutional_holdings
  (
    filing_id,
    cusip,
    coalesce(title_of_class, ''),
    coalesce(share_type, ''),
    coalesce(put_call, ''),
    coalesce(investment_discretion, ''),
    coalesce(other_manager, '')
  );
