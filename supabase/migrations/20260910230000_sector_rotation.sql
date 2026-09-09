-- Sector rotation, aggregated in the database.
--
-- The research layer page computed this in Node from every holding in the two
-- newest filings of every manager - about a hundred and thirty thousand rows,
-- to produce a dozen. It used to be fast because it was wrong: the read was
-- unpaged, so PostgREST returned a thousand rows per batch and the weights
-- were computed from roughly one per cent of the book. Paging it in #1041 made
-- it correct and made the page hang.
--
-- The right amount of data to send a browser for this is the answer, not the
-- input. A dozen rows.
--
-- dense_rank on report_date, not row_number: an amendment and its original can
-- both be active for one period, and row_number would then hand a manager's
-- "previous" quarter to a second copy of its current one - a rotation of zero,
-- averaged into everyone else's.
create or replace function public.institutional_sector_rotation()
returns table (
  sector text,
  current_weight numeric,
  previous_weight numeric,
  weight_change numeric
)
language sql
stable
security definer
set search_path = public
set statement_timeout = '120s'
as $$
  -- One filing per manager per period, newest acceptance wins. The schema is
  -- meant to leave a single active filing per period, but the Node version
  -- collapsed defensively and so does this: were an amendment and its original
  -- both left active, that manager's current quarter would be counted twice
  -- and its weights would carry double into everyone else's.
  one_per_period as (
    select distinct on (filings.manager_id, filings.report_date)
      filings.id,
      filings.manager_id,
      filings.report_date
    from public.institutional_filings filings
    where filings.is_active
    order by filings.manager_id, filings.report_date, filings.filed_at desc
  ),
  ranked as (
    select
      id,
      dense_rank() over (partition by manager_id order by report_date desc) as rk
    from one_per_period
  ),
  sides as (
    select id, case when rk = 1 then 'current' else 'previous' end as side
    from ranked
    where rk <= 2
  ),
  -- One classification per security: the newest by valid_from, which is how
  -- the caller read them too.
  latest_class as (
    select distinct on (upper(security_key))
      upper(security_key) as security_key,
      sector
    from public.institutional_security_classifications
    order by upper(security_key), valid_from desc
  ),
  valued as (
    select
      sides.side,
      coalesce(latest_class.sector, 'Unclassified') as sector,
      coalesce(holdings.value_usd, 0) as value_usd
    from public.institutional_holdings holdings
    join sides on sides.id = holdings.filing_id
    -- The classification's security_key is whichever of these the holding had
    -- when it was written, in this order. Mirrored exactly rather than joining
    -- on the CUSIP alone, so a holding filed without one classifies here the
    -- same way it did in Node. Left, because an unclassified security is still
    -- part of the book and dropping it would inflate every other weight.
    left join latest_class on latest_class.security_key = coalesce(
      nullif(upper(btrim(holdings.cusip)), ''),
      nullif(upper(btrim(holdings.ticker)), ''),
      upper(btrim(holdings.issuer_name))
    )
  ),
  by_sector as (
    select
      sector,
      sum(value_usd) filter (where side = 'current') as current_value,
      sum(value_usd) filter (where side = 'previous') as previous_value
    from valued
    group by sector
  ),
  totals as (
    select
      sum(value_usd) filter (where side = 'current') as current_total,
      sum(value_usd) filter (where side = 'previous') as previous_total
    from valued
  )
  select
    by_sector.sector,
    coalesce(coalesce(by_sector.current_value, 0) / nullif(totals.current_total, 0), 0) as current_weight,
    coalesce(coalesce(by_sector.previous_value, 0) / nullif(totals.previous_total, 0), 0) as previous_weight,
    coalesce(coalesce(by_sector.current_value, 0) / nullif(totals.current_total, 0), 0)
      - coalesce(coalesce(by_sector.previous_value, 0) / nullif(totals.previous_total, 0), 0) as weight_change
  from by_sector
  cross join totals
  order by weight_change desc
$$;

revoke all on function public.institutional_sector_rotation() from public;
revoke all on function public.institutional_sector_rotation() from anon;
revoke all on function public.institutional_sector_rotation() from authenticated;
grant execute on function public.institutional_sector_rotation() to service_role;
