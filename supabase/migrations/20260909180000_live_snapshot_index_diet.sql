-- Two indexes on live_market_snapshots that cost 726 MB and earn nothing, and
-- an autovacuum setting that makes the nightly prune actually reclaim space.
--
-- Measured on production, not assumed:
--
--   index                                idx_scan     size
--   instrument_time_idx                 5,245,891   387 MB
--   instrument_minute_uidx              4,924,875   393 MB
--   instrument_key_observed_at_key            373   393 MB
--   minute_idx                                  0   333 MB
--   pkey                                        0   174 MB
--   observed_at_idx                           540    72 MB

-- Never scanned once. Dropping an index is an unlink, so this returns its
-- space immediately - unlike vacuum full, which needs free space equal to the
-- data it is compacting before it can give any of it back.
drop index if exists public.live_market_snapshots_minute_idx;

-- unique (instrument_key, observed_at) is redundant twice over. The only
-- writer, liveAlphaPersistence, upserts on (instrument_key, minute_bucket), so
-- nothing names this as a conflict target. And because minute_bucket is
-- date_trunc('minute', observed_at), one row per instrument per minute already
-- forbids two rows sharing an observed_at. Its 373 scans fall through to
-- instrument_time_idx, which leads with the same two columns.
--
-- The one way that reasoning fails: unique indexes treat nulls as distinct, so
-- a row with a null minute_bucket is not covered by the minute constraint, and
-- this one is doing real work. The trigger populates it on every insert, but
-- the check is cheap and the cost of being wrong is duplicate market data.
--
-- A notice rather than an exception, because the two changes around it are
-- worth keeping even in the case where this one has to be skipped - and an
-- exception here would roll all three back.
do $$
declare unguarded bigint;
begin
  select count(*) into unguarded
    from public.live_market_snapshots
   where minute_bucket is null;

  if unguarded > 0 then
    raise notice
      'Keeping live_market_snapshots_instrument_key_observed_at_key: % rows have a null minute_bucket, so the minute constraint does not cover them. That is a gap in the trigger - fix it before reclaiming this index.',
      unguarded;
  else
    alter table public.live_market_snapshots
      drop constraint if exists live_market_snapshots_instrument_key_observed_at_key;
  end if;
end;
$$;

-- The nightly prune leaves about 360,000 dead tuples a night: a day of rows
-- blanked at three days, and a day deleted at twenty-five. The default
-- autovacuum trigger is 20% of the table, roughly 876,000 rows here, so it
-- would fire every second or third night and the space would not be reusable
-- in between. At 2% it fires after each night's run, which is what makes the
-- retention arithmetic close.
--
-- Deleting rows does not free space; only a vacuum does. That is the whole
-- mechanism, and leaving this on the default is how a table that is pruned
-- every single night still runs out of room.
alter table public.live_market_snapshots set (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_vacuum_threshold = 50000,
  autovacuum_analyze_scale_factor = 0.05
);
