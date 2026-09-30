-- Holdings wearing a symbol that is not a US ticker, found in the database.
--
-- The recovery script paged every holdings row - 2.6 million of them, about
-- two thousand six hundred requests - to find the two hundred pairs whose
-- ticker is not US-shaped. That is the same read that stopped working in the
-- price backfill:
--
--   Error: canceling statement due to statement timeout
--
-- The shape it is looking for is a regular expression the database can apply
-- while it scans, so the answer arrives as two hundred rows instead of as two
-- and a half million to be filtered in Node.
--
-- The pattern is the script's own, unchanged: one to five capitals, with an
-- optional single-letter class suffix. Anything else is a venue code -
-- HONGBP for Honeywell, LRCXEUR for Lam Research - because OpenFIGI preferred
-- a US listing without requiring one, and European venues name their lines by
-- currency.
create or replace function public.institutional_venue_ticker_candidates()
returns table (
  cusip text,
  ticker text,
  issuer_name text,
  rows bigint,
  value numeric,
  earliest date,
  latest date
)
language sql
stable
security definer
set search_path = public
set statement_timeout = '180s'
as $$
  select
    holdings.cusip,
    upper(holdings.ticker) as ticker,
    -- Deterministic rather than whichever row arrived first. The same CUSIP
    -- can carry slightly different issuer spellings across a decade of
    -- filings, and the name is matched against SEC's own, so it must not
    -- change between runs.
    min(holdings.issuer_name) as issuer_name,
    count(*) as rows,
    sum(coalesce(holdings.value_usd, 0)) as value,
    min(holdings.report_date) as earliest,
    max(holdings.report_date) as latest
  from public.institutional_holdings holdings
  where holdings.ticker is not null
    and holdings.put_call is null
    and upper(holdings.ticker) !~ '^[A-Z]{1,5}(-[A-Z])?$'
  group by holdings.cusip, upper(holdings.ticker)
  -- Paging needs a total order, and a cusip can appear under more than one
  -- venue symbol.
  order by 1, 2
$$;

revoke all on function public.institutional_venue_ticker_candidates() from public;
revoke all on function public.institutional_venue_ticker_candidates() from anon;
revoke all on function public.institutional_venue_ticker_candidates() from authenticated;
grant execute on function public.institutional_venue_ticker_candidates() to service_role;
