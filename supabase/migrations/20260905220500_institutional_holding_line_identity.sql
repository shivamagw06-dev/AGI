drop index if exists public.institutional_holdings_filing_security_uq;

create unique index institutional_holdings_filing_security_uq
  on public.institutional_holdings
  (
    filing_id,
    cusip,
    coalesce(title_of_class, ''),
    coalesce(put_call, ''),
    coalesce(investment_discretion, ''),
    coalesce(other_manager, '')
  );
