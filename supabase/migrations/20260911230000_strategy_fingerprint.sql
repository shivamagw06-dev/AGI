-- What each manager's book says about how it is run.
--
-- institutional_managers already carries a `strategy` column, hand-written at
-- seed time on ten of the fifty-one managers: "Concentrated activist",
-- "Fundamental growth". Those are assertions. Nothing checks them against a
-- filing and forty-one managers have none at all.
--
-- This measures the same claim from the holdings. Everything below is
-- arithmetic over rows we already store - counts, value shares, quarter-over-
-- quarter differences - and nothing is fetched or asserted. The measuring is
-- here in SQL rather than in the service because it scans every holding of
-- every manager, and pulling ~90,000 rows through PostgREST to count them in
-- JavaScript is the mistake this codebase has already made a dozen times.
--
-- The one subtlety worth stating: turnover is null, not zero, when there is no
-- prior quarter to compare against. Norges Bank measured 100% new positions in
-- the first sweep. That is not a strategy, it is a manager with one stored
-- filing, and a zero would have read as "changed nothing" - the exact opposite
-- of the truth. prior_positions is returned alongside so the null is
-- explainable rather than mysterious.

create table if not exists public.institutional_manager_strategy_profiles (
  id uuid primary key default gen_random_uuid(),
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  -- The archetype key and its human label, both from strategyFingerprint.js.
  -- Stored rather than derived on read so the page does not re-scan every
  -- holding to draw one line of text.
  archetype text not null,
  label text not null,
  -- What a book of this shape is characteristic of. Deliberately not a motive:
  -- 13F is evidence of what a manager holds, never of why.
  characteristic_of text not null,
  confidence text not null check (confidence in ('low', 'medium', 'high')),
  -- The measured numbers the label rests on, so a reader who disagrees with
  -- the label can still use the evidence.
  evidence jsonb not null default '[]'::jsonb,
  traits jsonb not null default '[]'::jsonb,
  -- Why this might be wrong, carried with the claim rather than left in a
  -- code comment where nobody reading the page will ever see it.
  caveats jsonb not null default '[]'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  as_of_date date not null,
  quarters_observed integer not null default 0,
  computed_at timestamptz not null default now(),
  unique (manager_id)
);

create index if not exists institutional_manager_strategy_archetype_idx
  on public.institutional_manager_strategy_profiles (archetype);

alter table public.institutional_manager_strategy_profiles enable row level security;

-- Not exposed to the anon key, exactly like the holdings it is derived from.
-- The page reads this through the server the same way it reads everything
-- else in this family; there is no reason for a second, wider path to it.
revoke all on table public.institutional_manager_strategy_profiles from public, anon, authenticated;
grant select, insert, update, delete
  on table public.institutional_manager_strategy_profiles to service_role;

-- The measurement itself. One row per manager with a book.
create or replace function public.institutional_strategy_metrics()
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
set statement_timeout = '180s'
as $$
  -- One filing per reporting period. A manager that amends a quarter has two
  -- rows for it; the later one is the book that stands.
  with one_per_period as (
    select distinct on (f.manager_id, f.report_date)
           f.id, f.manager_id, f.report_date
    from public.institutional_filings f
    where f.is_active
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
  cur as (select r.id, r.manager_id, r.report_date from ranked r where r.rk = 1),
  prev as (select r.id, r.manager_id from ranked r where r.rk = 2),
  -- The current book, each line ranked by value so the largest ten can be
  -- summed without a second pass.
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
  prior as (
    select p.manager_id, h.cusip
    from public.institutional_holdings h
    join prev p on p.id = h.filing_id
  ),
  -- How many stored quarters each currently held name appears in. Appearances,
  -- not an unbroken run: a position sold and rebought counts twice, which is
  -- the honest reading of "how long has this been in the book".
  --
  -- Counted over every name rather than filtered to the current book first.
  -- An EXISTS against the current book would re-scan it once per candidate
  -- row, which for a thirteen-thousand-position filer is a billion
  -- comparisons; one grouped pass and a hash join is the same answer.
  appearances as (
    select h.manager_id, h.cusip, count(distinct r.report_date) as quarters
    from public.institutional_holdings h
    join ranked r on r.id = h.filing_id
    group by h.manager_id, h.cusip
  ),
  -- The median is over the names held now, not over every name ever held: the
  -- question is how long the current book has been in place.
  persistence as (
    select b.manager_id,
           percentile_cont(0.5) within group (order by ap.quarters) as median_quarters
    from book b
    join appearances ap on ap.manager_id = b.manager_id and ap.cusip = b.cusip
    group by b.manager_id
  ),
  -- Sector of each held name, from the classifications already built. The
  -- newest classification for the name wins. A name with none is left out of
  -- the denominator rather than counted as a sector of its own, so the share
  -- reported is a share of what is classified and says so on the page.
  classified as (
    select b.manager_id, b.value_usd, k.sector
    from book b
    join lateral (
      select c.sector
      from public.institutional_security_classifications c
      where coalesce(c.cusip, c.security_key) = b.cusip
        and c.sector is not null
        and c.sector <> 'Unclassified'
      order by c.valid_from desc, c.updated_at desc
      limit 1
    ) k on true
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
  -- 13D says the holder intends to influence the company; 13G says it does
  -- not. Both are the filer's own declaration and the cleanest statement of
  -- intent anywhere in the record.
  schedules as (
    select e.manager_id,
           count(*) filter (where e.form_type ilike '%13D%')::integer as activist,
           count(*) filter (where e.form_type ilike '%13G%')::integer as passive
    from public.institutional_external_filings e
    where e.manager_id is not null
    group by e.manager_id
  ),
  aggregated as (
    select b.manager_id,
           count(*)::integer as positions,
           max(b.total) as total_value,
           sum(b.value_usd) filter (where b.rn <= 10) as top10_value,
           count(*) filter (where b.put_call is not null and btrim(b.put_call) <> '')::integer as option_lines,
           count(*) filter (where b.voting_sole > 0)::integer as voting_lines,
           count(*) filter (
             where not exists (select 1 from prior p
                               where p.manager_id = b.manager_id and p.cusip = b.cusip)
           )::integer as new_lines,
           (select count(*)::integer from prior p where p.manager_id = b.manager_id) as prior_lines
    from book b
    group by b.manager_id
  )
  select
    m.id,
    m.slug,
    m.display_name,
    o.as_of,
    o.quarters,
    a.positions,
    a.prior_lines,
    a.total_value,
    case when a.total_value > 0
         then round(100.0 * a.top10_value / a.total_value, 2) end,
    round(100.0 * a.option_lines / a.positions, 2),
    round(100.0 * a.voting_lines / a.positions, 2),
    -- Null, not zero, when there is nothing to compare against.
    case when a.prior_lines > 0
         then round(100.0 * a.new_lines / a.positions, 2) end,
    p.median_quarters::numeric,
    t.sector,
    round(t.share, 2),
    coalesce(s.activist, 0),
    coalesce(s.passive, 0)
  from aggregated a
  join public.institutional_managers m on m.id = a.manager_id
  join observed o on o.manager_id = a.manager_id
  left join persistence p on p.manager_id = a.manager_id
  left join dominant_sector t on t.manager_id = a.manager_id
  left join schedules s on s.manager_id = a.manager_id
  order by a.positions desc;
$$;

revoke all on function public.institutional_strategy_metrics() from public, anon, authenticated;
grant execute on function public.institutional_strategy_metrics() to service_role;

comment on function public.institutional_strategy_metrics is
  'Per-manager 13F book shape: breadth, concentration, turnover, persistence, voting and 13D/13G counts. Turnover is null when no prior quarter is stored.';
comment on table public.institutional_manager_strategy_profiles is
  'Strategy archetype derived from the measured book, with the evidence and the caveats it rests on. No motive is attributed.';
