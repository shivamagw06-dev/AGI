-- The benchmarks must be priced over the whole span, not over whoever held them.
--
-- The backtester derives its trading calendar from the benchmark's own prints -
-- correct for every year, including half-days and unscheduled closures, with no
-- holiday table to maintain. But the price backfill fetches each symbol from
-- the date it was first held, and SPY is only held incidentally, so its history
-- began in 2021 and the calendar had no sessions before then.
--
-- The result was an eleven-year backtest that could evaluate nothing:
--
--   status: not_calculable
--   "No period could be priced. The benchmark is missing prices in at least
--    one period." 39 period(s) could not be evaluated.
--
-- Every skipped period read "no tradable session after acceptance within the
-- price history", which is true and says nothing about which price history was
-- missing. The holdings were priced; the ruler was not.
--
-- So the benchmarks are added to the target list with the earliest date any
-- position is held, and a last-held date of today. The second part matters as
-- much as the first: the backfill treats a symbol held recently as one that
-- should resolve, and reports it loudly when it does not. A benchmark that
-- fails is not a delisted holding, it is a broken backtester.
create or replace function public.institutional_price_targets()
returns table (
  security_key text,
  ticker text,
  first_report_date date,
  last_report_date date,
  positions bigint
)
language sql
stable
security definer
set search_path = public
set statement_timeout = '180s'
as $$
  with base as (
    select
      coalesce(chain.security_key, holdings.cusip) as security_key,
      holdings.ticker,
      holdings.report_date
    from public.institutional_holdings holdings
    left join public.sec_13f_identity_chain chain on chain.cusip = holdings.cusip
    where holdings.ticker is not null
      and holdings.put_call is null
  ),
  span as (select min(report_date) as earliest from base),
  combined as (
    select security_key, ticker, report_date, 1::bigint as counts from base
    union all
    -- Unioned rather than filtered in by `not exists`, so a benchmark that is
    -- also genuinely held still has its start pulled back to the earliest
    -- date. Held incidentally from 2021 is exactly the case that broke this.
    select benchmark.symbol, benchmark.symbol, (select earliest from span), 0::bigint
      from (values ('SPY'), ('QQQ')) as benchmark(symbol)
     where (select earliest from span) is not null
    union all
    select benchmark.symbol, benchmark.symbol, current_date, 0::bigint
      from (values ('SPY'), ('QQQ')) as benchmark(symbol)
  )
  select
    security_key,
    ticker,
    min(report_date) as first_report_date,
    max(report_date) as last_report_date,
    sum(counts) as positions
  from combined
  group by 1, 2
  order by 1, 2
$$;

revoke all on function public.institutional_price_targets() from public;
revoke all on function public.institutional_price_targets() from anon;
revoke all on function public.institutional_price_targets() from authenticated;
grant execute on function public.institutional_price_targets() to service_role;
