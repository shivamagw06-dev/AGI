-- Where each symbol's stored price history begins and ends.
--
-- The backfill decides what to fetch from a freshness log that records when a
-- symbol was last asked for, not how far back the answer reached. So a symbol
-- fetched yesterday looks current even when its history starts two years after
-- the date it is first held, and nothing ever repairs it: TSM has prices from
-- 2022-12-01 and is held from 2021-09-30, which blocks twenty-two of the
-- fifty-one tracked managers from being backtested at all.
--
-- Answering that in the client means reading three and a half million rows to
-- learn two dates per symbol. Answered here it is an index-only scan of
-- institutional_price_ticker_date_idx.
create or replace function public.institutional_price_coverage()
returns table (
  ticker text,
  first_date date,
  last_date date,
  sessions bigint
)
language sql
stable
security definer
set search_path = public
set statement_timeout = '120s'
as $$
  select
    prices.ticker,
    min(prices.price_date) as first_date,
    max(prices.price_date) as last_date,
    count(*) as sessions
  from public.institutional_security_prices prices
  group by prices.ticker
$$;

revoke all on function public.institutional_price_coverage() from public;
revoke all on function public.institutional_price_coverage() from anon;
revoke all on function public.institutional_price_coverage() from authenticated;
grant execute on function public.institutional_price_coverage() to service_role;
