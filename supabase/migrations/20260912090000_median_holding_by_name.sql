-- Count the median holding period by name, not by line.
--
-- A cusip appears twice in one filing when it is held both as shares and as an
-- option, and the median was taken over lines, so those names counted twice.
-- It changed the answer: run against distinct names, Goldman's median position
-- has appeared in 23 of 42 quarters and Millennium's in 22 of 42, both below
-- the threshold that marks a book whose names survive; run against lines, both
-- cleared it and Akre - which does clear it on names, at 27 of 42 - did not.
-- Three managers labelled wrongly by a duplicate row.
--
-- "The median position" has to mean a position. Only the persistence CTE
-- changes; every other measurement is per line and correctly so.
create or replace function public.institutional_strategy_metrics(p_manager_id uuid default null)
returns table (
  manager_id uuid,
  manager_slug text,
  display_name text,
  as_of_date date,
  quarters_observed integer,
  positions integer,
  prior_positions integer,
  reported_value_usd numeric,
  top10_pct numeric,
  options_pct numeric,
  votes_pct numeric,
  turnover_pct numeric,
  median_quarters_held numeric,
  top_sector text,
  top_sector_pct numeric,
  activist_filings integer,
  passive_filings integer
)
language sql
stable
security definer
set search_path = public
set statement_timeout = '120s'
as $$
  with one_per_period as (
    select distinct on (f.manager_id, f.report_date)
           f.id, f.manager_id, f.report_date
    from public.institutional_filings f
    where f.is_active
      and (p_manager_id is null or f.manager_id = p_manager_id)
    order by f.manager_id, f.report_date, f.filed_at desc
  ),
  ranked as (
    select o.id, o.manager_id, o.report_date,
           dense_rank() over (partition by o.manager_id order by o.report_date desc) as rk
    from one_per_period o
  ),
  observed as (
    select r.manager_id, count(*)::integer as quarters, max(r.report_date) as as_of
    from ranked r group by r.manager_id
  ),
  cur as (select r.id, r.manager_id from ranked r where r.rk = 1),
  prev as (select r.id, r.manager_id from ranked r where r.rk = 2),
  book as (
    select c.manager_id,
           h.cusip,
           h.value_usd,
           h.put_call,
           coalesce(h.voting_sole, 0) as voting_sole,
           row_number() over (partition by c.manager_id order by h.value_usd desc) as rn,
           sum(h.value_usd) over (partition by c.manager_id) as total
    from public.institutional_holdings h
    join cur c on c.id = h.filing_id
  ),
  -- The names held now, each once. Everything measured per position rather
  -- than per reported line reads from here.
  book_names as (
    select distinct b.manager_id, b.cusip from book b
  ),
  prior_keys as (
    select distinct p.manager_id, h.cusip
    from public.institutional_holdings h
    join prev p on p.id = h.filing_id
  ),
  prior_counts as (
    select pk.manager_id, count(*)::integer as prior_lines
    from prior_keys pk group by pk.manager_id
  ),
  book_marked as (
    select b.manager_id, b.cusip, b.value_usd, b.put_call, b.voting_sole, b.rn, b.total,
           (pk.cusip is null) as is_new
    from book b
    left join prior_keys pk
      on pk.manager_id = b.manager_id and pk.cusip = b.cusip
  ),
  appearances as (
    select h.manager_id, h.cusip, count(distinct r.report_date) as quarters
    from public.institutional_holdings h
    join ranked r on r.id = h.filing_id
    group by h.manager_id, h.cusip
  ),
  -- One vote per name. A name held as both shares and a put used to vote twice.
  persistence as (
    select bn.manager_id,
           percentile_cont(0.5) within group (order by ap.quarters) as median_quarters
    from book_names bn
    join appearances ap on ap.manager_id = bn.manager_id and ap.cusip = bn.cusip
    group by bn.manager_id
  ),
  class_by_name as (
    select distinct on (coalesce(c.cusip, c.security_key))
           coalesce(c.cusip, c.security_key) as name_key,
           c.sector
    from public.institutional_security_classifications c
    where c.sector is not null and c.sector <> 'Unclassified'
    order by coalesce(c.cusip, c.security_key), c.valid_from desc, c.updated_at desc
  ),
  classified as (
    select b.manager_id, b.value_usd, k.sector
    from book b
    join class_by_name k on k.name_key = b.cusip
  ),
  sector_share as (
    select cl.manager_id, cl.sector,
           sum(cl.value_usd) as sector_value,
           sum(sum(cl.value_usd)) over (partition by cl.manager_id) as classified_value,
           row_number() over (partition by cl.manager_id order by sum(cl.value_usd) desc) as rn
    from classified cl group by cl.manager_id, cl.sector
  ),
  dominant_sector as (
    select ss.manager_id, ss.sector,
           case when ss.classified_value > 0
                then 100.0 * ss.sector_value / ss.classified_value end as share
    from sector_share ss where ss.rn = 1
  ),
  schedules as (
    select e.manager_id,
           count(*) filter (where e.form_type ilike '%13D%')::integer as activist,
           count(*) filter (where e.form_type ilike '%13G%')::integer as passive
    from public.institutional_external_filings e
    where e.manager_id is not null
      and (p_manager_id is null or e.manager_id = p_manager_id)
    group by e.manager_id
  ),
  aggregated as (
    select bm.manager_id,
           count(*)::integer as positions,
           max(bm.total) as total_value,
           sum(bm.value_usd) filter (where bm.rn <= 10) as top10_value,
           count(*) filter (where bm.put_call is not null and btrim(bm.put_call) <> '')::integer as option_lines,
           count(*) filter (where bm.voting_sole > 0)::integer as voting_lines,
           count(*) filter (where bm.is_new)::integer as new_lines
    from book_marked bm
    group by bm.manager_id
  )
  select
    m.id,
    m.slug,
    m.display_name,
    o.as_of,
    o.quarters,
    a.positions,
    coalesce(pc.prior_lines, 0),
    a.total_value,
    case when a.total_value > 0
         then round(100.0 * a.top10_value / a.total_value, 2) end,
    round(100.0 * a.option_lines / a.positions, 2),
    round(100.0 * a.voting_lines / a.positions, 2),
    case when coalesce(pc.prior_lines, 0) > 0
         then round(100.0 * a.new_lines / a.positions, 2) end,
    p.median_quarters::numeric,
    t.sector,
    round(t.share, 2),
    coalesce(s.activist, 0),
    coalesce(s.passive, 0)
  from aggregated a
  join public.institutional_managers m on m.id = a.manager_id
  join observed o on o.manager_id = a.manager_id
  left join prior_counts pc on pc.manager_id = a.manager_id
  left join persistence p on p.manager_id = a.manager_id
  left join dominant_sector t on t.manager_id = a.manager_id
  left join schedules s on s.manager_id = a.manager_id
  order by a.positions desc;
$$;

comment on function public.institutional_strategy_metrics(uuid) is
  'Per-manager 13F book shape: breadth, concentration, turnover, persistence, voting and 13D/13G counts. Holding period is per name; everything else is per reported line. Pass a manager id; null measures every manager and is only safe from a direct connection.';
