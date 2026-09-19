-- Keep Live Alpha startup restores and run-health lookups index-backed.
-- Historical orphaned runs are deliberately preserved for auditability; the
-- workspace naturally supersedes them when the engine stores its next run.

create index if not exists live_market_snapshots_observed_at_idx
  on public.live_market_snapshots (observed_at desc);

create index if not exists live_alpha_signals_run_id_idx
  on public.live_alpha_signals (run_id);
