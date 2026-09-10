-- Venue-ticker candidates, including symbols that look like US tickers.
--
-- The rule was shape alone: anything not matching ^[A-Z]{1,5}(-[A-Z])?$ was
-- suspect. That catches DWDPEUR, 8L8C and 22941EUR and misses every impostor
-- wearing a plausible shape - EXMOC, AZNN, AKX, SKAA. EXMOC is five letters,
-- so it has never been a candidate, and it carries $147.9bn of Exxon Mobil
-- under a symbol no price lookup will ever resolve.
--
-- A shape-valid symbol needs a different signal, and two tables already hold
-- one between them.
--
--   sec_issuer_tickers is every ticker an insider has filed under across a
--   decade - 16,070 issuer/ticker pairs. A real US ticker is in it. A symbol
--   a filer invented is not.
--
--   institutional_security_prices says whether anything ever priced it. This
--   separates the impostors from ETFs, which are absent from the registry for
--   an honest reason - nobody files a Form 4 on a trust - and which price
--   perfectly well.
--
-- So a shape-valid symbol is suspect when the registry has never seen it and
-- nothing has ever priced it. Activision is in the registry and stays out of
-- this set: ATVI is a real ticker whose company was acquired, which is a
-- different problem with a different answer.
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
  with grouped as (
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
    group by holdings.cusip, upper(holdings.ticker)
  )
  -- Grouped first, then tested. The two existence checks are index probes, and
  -- running them per holding would be five million probes over 2.6m rows to
  -- answer a question about a few thousand distinct symbols.
  select grouped.cusip, grouped.ticker, grouped.issuer_name, grouped.rows,
         grouped.value, grouped.earliest, grouped.latest
  from grouped
  where
    -- Not a US ticker by shape.
    grouped.ticker !~ '^[A-Z]{1,5}(-[A-Z])?$'
    -- Or shaped like one, but unknown to every record of a real ticker.
    or (
      not exists (
        select 1 from public.sec_issuer_tickers registry
        where registry.ticker = grouped.ticker
      )
      and not exists (
        select 1 from public.institutional_security_prices prices
        where prices.ticker = grouped.ticker
      )
    )
  -- Paging needs a total order, and a cusip can appear under more than one
  -- venue symbol.
  order by 1, 2
$$;

revoke all on function public.institutional_venue_ticker_candidates() from public;
revoke all on function public.institutional_venue_ticker_candidates() from anon;
revoke all on function public.institutional_venue_ticker_candidates() from authenticated;
grant execute on function public.institutional_venue_ticker_candidates() to service_role;
