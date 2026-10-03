-- Live Alpha outcome settlement and the conviction ranking universe.
-- Constraint and index changes only: no row is updated or deleted.

-- The conviction ranking has covered the Nifty 500 since the live universe
-- moved to it, but its tables still only accepted Nifty 200, so every save
-- failed with 23514 and no ranking was ever stored.
alter table public.evidence_conviction_runs
  drop constraint if exists evidence_conviction_runs_universe_check,
  add constraint evidence_conviction_runs_universe_check check (universe in ('nifty200', 'nifty500'));
alter table public.evidence_conviction_runs
  drop constraint if exists evidence_conviction_runs_universe_size_check,
  add constraint evidence_conviction_runs_universe_size_check check (universe_size between 0 and 500);
alter table public.evidence_conviction_rankings
  drop constraint if exists evidence_conviction_rankings_rank_check,
  add constraint evidence_conviction_rankings_rank_check check (rank between 1 and 500);

-- Settlement reads pending rows by attempt count, then due time, so rows that
-- could not be priced yet queue behind fresh ones.
create index if not exists live_alpha_outcomes_pending_attempt_due_idx
  on public.live_alpha_signal_outcomes (attempt_count, due_at)
  where status = 'pending';
create index if not exists research_confluence_outcomes_pending_attempt_due_idx
  on public.research_confluence_outcomes (attempt_count, due_at)
  where status = 'pending';
