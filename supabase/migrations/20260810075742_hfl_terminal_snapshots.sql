-- Hedge Fund Lab terminal read model.
-- Python calculates; Supabase stores; Node serves the latest snapshot.

create table if not exists public.hfl_terminal_snapshots (
  id uuid primary key default gen_random_uuid(),
  generated_at timestamptz not null default now(),
  source_as_of text,
  status text not null default 'ready' check (status in ('ready', 'stale', 'failed', 'computing')),
  freshness text not null default 'fresh' check (freshness in ('fresh', 'aging', 'stale')),
  schema_version text not null default '1.0',
  calculation_version text not null default 'hfl_terminal_v1',
  data_quality jsonb not null default '{}'::jsonb
    check (jsonb_typeof(data_quality) = 'object'),
  limit_used integer not null default 12 check (limit_used > 0 and limit_used <= 50),
  universe_scanned integer not null default 0 check (universe_scanned >= 0),
  live_opportunities integer not null default 0 check (live_opportunities >= 0),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  created_at timestamptz not null default now()
);

create index if not exists hfl_terminal_snapshots_generated_at_idx
  on public.hfl_terminal_snapshots (generated_at desc);

create index if not exists hfl_terminal_snapshots_status_generated_idx
  on public.hfl_terminal_snapshots (status, generated_at desc);

create table if not exists public.hfl_terminal_opportunities (
  id uuid primary key default gen_random_uuid(),
  snapshot_id uuid not null references public.hfl_terminal_snapshots(id) on delete cascade,
  scan_id text not null,
  scan_label text,
  ticker text not null check (ticker = upper(ticker)),
  company_name text,
  sector text,
  rank integer not null check (rank > 0),
  confidence numeric(6,2),
  why text,
  row_payload jsonb not null default '{}'::jsonb
    check (jsonb_typeof(row_payload) = 'object'),
  created_at timestamptz not null default now(),
  unique (snapshot_id, scan_id, rank)
);

create index if not exists hfl_terminal_opportunities_snapshot_scan_idx
  on public.hfl_terminal_opportunities (snapshot_id, scan_id, rank);

create index if not exists hfl_terminal_opportunities_ticker_idx
  on public.hfl_terminal_opportunities (ticker, created_at desc);

alter table public.hfl_terminal_snapshots enable row level security;
alter table public.hfl_terminal_opportunities enable row level security;

comment on table public.hfl_terminal_snapshots is
  'Precomputed Hedge Fund Lab terminal payloads. Node serves these so page loads do not wake Python scanners.';
comment on table public.hfl_terminal_opportunities is
  'Flattened opportunity rows from each HFL terminal snapshot for audit and validation.';

-- Keep history for validation; prune rows older than 30 days.
create or replace function public.cleanup_hfl_terminal_snapshots(retention_days integer default 30)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  deleted integer;
begin
  delete from public.hfl_terminal_snapshots
  where generated_at < now() - make_interval(days => greatest(1, retention_days));
  get diagnostics deleted = row_count;
  return deleted;
end;
$$;

revoke all on function public.cleanup_hfl_terminal_snapshots(integer) from public;
grant execute on function public.cleanup_hfl_terminal_snapshots(integer) to service_role;
