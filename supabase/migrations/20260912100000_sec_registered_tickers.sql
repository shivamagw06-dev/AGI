-- The SEC's current ticker register, as a third witness to a real ticker.
--
-- The venue-candidate test asks two tables whether a shape-valid symbol is a
-- real ticker: sec_issuer_tickers, built from a decade of Form 3/4/5
-- submissions, and institutional_security_prices, which says whether anything
-- ever priced it.
--
-- Neither can see a foreign private issuer. Section 16 does not apply to them,
-- so they file no Forms 3, 4 or 5 and cannot appear in the insider registry -
-- and being flagged as a venue code is precisely what makes the price backfill
-- skip them, so the second test stays true for ever too. CyberArk is US-listed
-- on Nasdaq as CYBR, files 20-F, and carries $26.7bn of holdings that have been
-- refused on both counts in a loop that cannot break itself. Carnival plc,
-- Bancolombia, WNS Holdings and Golden Ocean are the same shape, and over
-- $32bn between them.
--
-- company_tickers.json and company_tickers_exchange.json do list them, because
-- registration is not Section 16. That is the witness this table stores: not
-- who filed what when - sec_issuer_tickers answers that, and its date windows
-- are the reason a 2019 holding of PARA resolves to Paramount and not to
-- Banzai - but simply whether the SEC lists this symbol today.
--
-- Deliberately dateless. Inventing a window for a register that publishes none
-- would corrupt the one table whose windows mean something.

create table if not exists public.sec_registered_tickers (
  ticker text primary key,
  cik text not null,
  issuer_name text,
  -- 'company' or 'fund', from which SEC file listed it. Kept because an ETF
  -- absent from the insider registry is honest - nobody files a Form 4 on a
  -- trust - and knowing which kind a symbol is explains the absence.
  kind text not null default 'company',
  refreshed_at timestamptz not null default now()
);

comment on table public.sec_registered_tickers is
  'Tickers the SEC lists today, from company_tickers.json and company_tickers_exchange.json. Answers "is this a real US symbol" for issuers that file no Form 4 - foreign private issuers are exempt from Section 16 and so are invisible to sec_issuer_tickers.';

alter table public.sec_registered_tickers enable row level security;
revoke all on table public.sec_registered_tickers from public, anon, authenticated;
grant select, insert, update, delete on table public.sec_registered_tickers to service_role;

-- The candidate test, with the third witness added.
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
  select grouped.cusip, grouped.ticker, grouped.issuer_name, grouped.rows,
         grouped.value, grouped.earliest, grouped.latest
  from grouped
  where
    -- Not a US ticker by shape.
    grouped.ticker !~ '^[A-Z]{1,5}(-[A-Z])?$'
    -- Or shaped like one, and unknown to all three records of a real ticker.
    or (
      not exists (
        select 1 from public.sec_issuer_tickers registry
        where registry.ticker = grouped.ticker
      )
      and not exists (
        select 1 from public.sec_registered_tickers listed
        where listed.ticker = grouped.ticker
      )
      and not exists (
        select 1 from public.institutional_security_prices prices
        where prices.ticker = grouped.ticker
      )
    )
  order by 1, 2
$$;

revoke all on function public.institutional_venue_ticker_candidates() from public, anon, authenticated;
grant execute on function public.institutional_venue_ticker_candidates() to service_role;
