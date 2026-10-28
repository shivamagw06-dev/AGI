-- Retention for live_market_snapshots.
--
-- The table grows about 150 MB a day and nothing prunes it. At the current
-- fill the disk exhausts in roughly a month, and a full disk puts Postgres
-- into read-only, which takes the site down.
--
-- Both statements live here rather than in the client so the predicates that
-- decide what is destroyed are in one reviewable place, and so each returns
-- the number of rows it actually touched instead of the client inferring it.
--
-- Neither function touches live_alpha_signals. Its outcomes reference it with
-- `on delete cascade`, so pruning signals would silently destroy
-- live_alpha_signal_outcomes - the only record of whether the five strategy
-- engines worked.

-- Empties raw_factors on rows in [from_at, to_at). Nothing reads raw_factors
-- past ninety minutes; it is roughly seventy per cent of the table.
create or replace function public.prune_live_snapshot_factors(from_at timestamptz, to_at timestamptz)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare touched integer;
begin
  if from_at is null or to_at is null or from_at >= to_at then
    raise exception 'prune_live_snapshot_factors: empty or inverted window %..%', from_at, to_at;
  end if;

  update public.live_market_snapshots
     set raw_factors = '{}'::jsonb
   where observed_at >= from_at
     and observed_at < to_at
     -- Rows already emptied are skipped, so a re-run costs nothing and does
     -- not churn tuples that are already at their final size.
     and raw_factors <> '{}'::jsonb;

  get diagnostics touched = row_count;
  return touched;
end;
$$;

-- Deletes rows in [from_at, to_at). No foreign key references
-- live_market_snapshots, so nothing cascades from this.
create or replace function public.delete_live_snapshots(from_at timestamptz, to_at timestamptz)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare removed integer;
begin
  if from_at is null or to_at is null or from_at >= to_at then
    raise exception 'delete_live_snapshots: empty or inverted window %..%', from_at, to_at;
  end if;

  delete from public.live_market_snapshots
   where observed_at >= from_at
     and observed_at < to_at;

  get diagnostics removed = row_count;
  return removed;
end;
$$;

-- Postgres grants execute to PUBLIC by default. These are security definer and
-- one of them deletes market data, so the default is withdrawn explicitly and
-- only the service role - which never reaches the browser - is granted back.
revoke all on function public.prune_live_snapshot_factors(timestamptz, timestamptz) from public;
revoke all on function public.prune_live_snapshot_factors(timestamptz, timestamptz) from anon;
revoke all on function public.prune_live_snapshot_factors(timestamptz, timestamptz) from authenticated;
grant execute on function public.prune_live_snapshot_factors(timestamptz, timestamptz) to service_role;

revoke all on function public.delete_live_snapshots(timestamptz, timestamptz) from public;
revoke all on function public.delete_live_snapshots(timestamptz, timestamptz) from anon;
revoke all on function public.delete_live_snapshots(timestamptz, timestamptz) from authenticated;
grant execute on function public.delete_live_snapshots(timestamptz, timestamptz) to service_role;
