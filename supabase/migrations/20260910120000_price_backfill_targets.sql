-- What to fetch prices for, collapsed in the database.
--
-- The backfill paged every holdings row through PostgREST to work out which
-- symbols it needed and how far back each was held. That was two thousand six
-- hundred requests when the table held 924,000 rows; at 2.62M it stopped
-- working entirely:
--
--   Error: canceling statement due to statement timeout
--
-- The answer it wanted was never 2.62M rows. It is one row per security and
-- ticker with the first and last date held - a few thousand - and the database
-- can produce that in a single pass over an index instead of shipping the
-- whole table across the network to be reduced in Node.
--
-- The identity chain is joined here too. A CUSIP that has been reassigned or
-- has changed ticker resolves to one security_key, and doing that join in SQL
-- keeps the caller from holding a second full table in memory to do it.
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
-- Raised for this function only. It reads and aggregates; a long one costs
-- time and nothing else.
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
    -- Options are not priced from an equity history, and a put carries the
    -- underlying's ticker - fetching for them would spend a request per
    -- contract on a series that does not exist.
    and holdings.put_call is null
  group by 1, 2
$$;

revoke all on function public.institutional_price_targets() from public;
revoke all on function public.institutional_price_targets() from anon;
revoke all on function public.institutional_price_targets() from authenticated;
grant execute on function public.institutional_price_targets() to service_role;
