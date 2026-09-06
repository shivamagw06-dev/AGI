-- A record of every 13F collection run.
--
-- Collection used to happen inside the API server with no record at all: it
-- either worked or it did not, and the only evidence was a console line on a
-- host nobody was reading. There was no way to answer "when did this last
-- succeed", "is the data stale", or "did we get throttled" - which is how a
-- 26-day collector outage went unnoticed on the hedge fund desk earlier.
--
-- Every column here is something the collector already observes. Nothing is
-- derived or estimated: if a number cannot be measured it stays null rather
-- than being filled with a plausible value.

create table if not exists public.institutional_collection_runs (
  id uuid primary key default gen_random_uuid(),

  -- Lifecycle. The row is written when the run starts, so a run that dies
  -- without ever finishing is still visible as one that never left 'running'.
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running'
    check (status in ('running', 'success', 'partial', 'failed', 'aborted')),

  -- What asked for this run, and what it was asked to do.
  trigger text not null default 'schedule'
    check (trigger in ('schedule', 'manual', 'backfill', 'test')),
  host text,
  manager_slug text,
  quarters integer,

  -- SEC traffic. Being throttled at all means the pace is set too high for
  -- this egress address, so it is recorded even when the run succeeds.
  sec_requests integer not null default 0,
  sec_throttled integer not null default 0,
  sec_throttle_pause_ms bigint not null default 0,
  sec_paced_wait_ms bigint not null default 0,
  sec_circuit_trips integer not null default 0,

  -- Work completed.
  managers_attempted integer not null default 0,
  managers_succeeded integer not null default 0,
  filings_ingested integer not null default 0,
  holdings_rows integer not null default 0,
  amendments_detected integer not null default 0,

  -- Failures, kept per-manager rather than as one collapsed message, because
  -- "3 of 51 failed" and "48 of 51 failed" need different responses and a
  -- single error string cannot tell them apart.
  failures jsonb not null default '[]'::jsonb,
  retry_state jsonb,
  error text,

  -- Scheduling. Stored rather than computed at read time so the CMS can say
  -- when the next run is due without knowing the cron expression.
  next_scheduled_at timestamptz,
  schedule_expression text,

  created_at timestamptz not null default now(),

  -- A finished run must say when it finished; an unfinished one must not.
  constraint collection_run_finish_consistent check (
    (status = 'running' and finished_at is null)
    or (status <> 'running' and finished_at is not null)
  ),
  constraint collection_run_succeeded_within_attempted check (
    managers_succeeded <= managers_attempted
  )
);

create index if not exists institutional_collection_runs_recent_idx
  on public.institutional_collection_runs (started_at desc);
create index if not exists institutional_collection_runs_status_idx
  on public.institutional_collection_runs (status, started_at desc);

-- Freshness, as one row, for the CMS.
--
-- SECURITY INVOKER so the view cannot be used to read past the caller's own
-- permissions, and search_path pinned so it resolves the same way whoever
-- calls it.
create or replace view public.institutional_collection_health
with (security_invoker = true) as
select
  (select started_at from public.institutional_collection_runs
    order by started_at desc limit 1) as last_run_started_at,
  (select finished_at from public.institutional_collection_runs
    where status = 'success' order by finished_at desc nulls last limit 1) as last_success_at,
  (select status from public.institutional_collection_runs
    order by started_at desc limit 1) as last_status,
  (select next_scheduled_at from public.institutional_collection_runs
    order by started_at desc limit 1) as next_scheduled_at,
  (select extract(epoch from (now() - finished_at))/3600 from public.institutional_collection_runs
    where status = 'success' order by finished_at desc nulls last limit 1) as hours_since_success,
  (select count(*) from public.institutional_collection_runs
    where status = 'running' and started_at < now() - interval '2 hours') as stalled_runs,
  (select max(report_date) from public.institutional_filings) as latest_report_date,
  (select max(accepted_at) from public.institutional_filings) as latest_accepted_at;

alter table public.institutional_collection_runs enable row level security;

-- Operational telemetry. Only the collector writes it and only an admin reads
-- it, so no anon or authenticated grant is issued at all.
revoke all on table public.institutional_collection_runs from anon, authenticated;
grant all on table public.institutional_collection_runs to service_role;
revoke all on public.institutional_collection_health from anon, authenticated;
grant select on public.institutional_collection_health to service_role;
