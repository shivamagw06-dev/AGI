-- The dry run's numbers, computed in the database.
--
-- The first attempt read the oldest and newest observed_at through PostgREST
-- and hit `canceling statement due to statement timeout`. PostgREST runs under
-- a short per-role statement timeout, and an exact count over four million
-- rows does not fit inside it no matter how the query is shaped. So the
-- reporting moves here, where the timeout can be raised for the duration of
-- one function and the whole report is a single round trip.

create or replace function public.live_snapshot_retention_report(
  raw_days integer,
  row_days integer
)
returns jsonb
language plpgsql
security definer
set search_path = public
-- Raised only inside this function. It reads and returns counts; it writes
-- nothing, so a long-running one costs time and not consistency.
set statement_timeout = '180s'
as $$
declare
  raw_cutoff timestamptz := now() - make_interval(days => raw_days);
  row_cutoff timestamptz := now() - make_interval(days => row_days);
  result jsonb;
begin
  if raw_days is null or row_days is null or raw_days < 0 or row_days < 0 then
    raise exception 'live_snapshot_retention_report: day counts must be non-negative';
  end if;
  if raw_days >= row_days then
    raise exception 'live_snapshot_retention_report: raw_days (%) must be shorter than row_days (%)', raw_days, row_days;
  end if;

  select jsonb_build_object(
    'oldest', (select min(observed_at) from live_market_snapshots),
    'newest', (select max(observed_at) from live_market_snapshots),
    -- The planner's own estimate, free to read. The exact counts below are
    -- what the decision rests on; this is here to show how far apart they are.
    'estimated_rows', (select reltuples::bigint from pg_class where oid = 'public.live_market_snapshots'::regclass),
    'raw_cutoff', raw_cutoff,
    'row_cutoff', row_cutoff,
    -- Rows the delete step would remove.
    'deletable_rows', (select count(*) from live_market_snapshots where observed_at < row_cutoff),
    -- Rows the blanking step would rewrite: past the raw cutoff, surviving the
    -- delete, and not already emptied. Rows already at '{}' are excluded here
    -- for the same reason the update excludes them - a re-run should report
    -- nothing left to do rather than the same number twice.
    'blankable_rows', (
      select count(*) from live_market_snapshots
       where observed_at >= row_cutoff
         and observed_at < raw_cutoff
         and raw_factors <> '{}'::jsonb
    ),
    'table_bytes', pg_total_relation_size('public.live_market_snapshots')
  ) into result;

  return result;
end;
$$;

revoke all on function public.live_snapshot_retention_report(integer, integer) from public;
revoke all on function public.live_snapshot_retention_report(integer, integer) from anon;
revoke all on function public.live_snapshot_retention_report(integer, integer) from authenticated;
grant execute on function public.live_snapshot_retention_report(integer, integer) to service_role;

-- The pruning statements themselves scan by observed_at. The index for that
-- was added in 20260818130000; this repeats it defensively because the dry run
-- timing out on a bounds lookup is what a missing one would look like, and
-- `if not exists` makes the repeat free when it is already there.
create index if not exists live_market_snapshots_observed_at_idx
  on public.live_market_snapshots (observed_at);

-- The write statements get the same treatment. A day of rows is small, but the
-- default REST timeout is short enough that a busy day could brush it, and
-- being cancelled halfway through a batch wastes the work without saying so.
alter function public.prune_live_snapshot_factors(timestamptz, timestamptz)
  set statement_timeout = '300s';
alter function public.delete_live_snapshots(timestamptz, timestamptz)
  set statement_timeout = '300s';
