-- Give the price targets a stable order, because the caller pages them.
--
-- PostgREST caps a response at a thousand rows and a set-returning function is
-- no exception, so the backfill reads these in pages. A GROUP BY makes no
-- promise about the order its rows come back in, and two calls are free to
-- differ - which turns paging into a lottery where some symbols appear twice
-- and others never appear at all.
--
-- Nothing about that failure is visible from outside. The run reports a symbol
-- count, fetches that many, and finishes successfully having skipped a slice of
-- the universe it never knew existed.
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
  select
    coalesce(chain.security_key, holdings.cusip) as security_key,
    holdings.ticker,
    min(holdings.report_date) as first_report_date,
    max(holdings.report_date) as last_report_date,
    count(*) as positions
  from public.institutional_holdings holdings
  left join public.sec_13f_identity_chain chain on chain.cusip = holdings.cusip
  where holdings.ticker is not null
    and holdings.put_call is null
  group by 1, 2
  -- Both columns, because the pair is what identifies a target. Ordering on
  -- security_key alone leaves the tickers under a reassigned CUSIP free to
  -- swap places between pages.
  order by 1, 2
$$;

revoke all on function public.institutional_price_targets() from public;
revoke all on function public.institutional_price_targets() from anon;
revoke all on function public.institutional_price_targets() from authenticated;
grant execute on function public.institutional_price_targets() to service_role;
