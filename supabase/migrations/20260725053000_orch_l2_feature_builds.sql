-- ORCH Layer 2 Feature Build ledger (WBS ORCH-003–005)
-- Schedules Feature Registry recalculation; research engines do not trigger builds.

create table if not exists public.orch_feature_builds (
  build_id uuid primary key,
  batch_id uuid,
  orch_run_id uuid references public.orch_runs (run_id),
  feature_id text not null,
  formula_version text not null,
  symbol text not null default '',
  as_of date not null,
  input_snapshot jsonb not null default '{}'::jsonb,
  timestamp timestamptz not null default now(),
  duration_ms double precision,
  status text not null,
  error text,
  attempt int not null default 1
);

create index if not exists orch_feature_builds_feature_asof_idx
  on public.orch_feature_builds (feature_id, as_of desc);

create index if not exists orch_feature_builds_batch_idx
  on public.orch_feature_builds (batch_id);

create table if not exists public.orch_feature_dirty (
  symbol text not null default '',
  as_of date not null,
  feature_id text not null,
  marked_at timestamptz not null default now(),
  primary key (symbol, as_of, feature_id)
);

create table if not exists public.orch_feature_ready_events (
  batch_id uuid primary key,
  as_of date not null,
  symbol text,
  snapshot_id text,
  succeeded jsonb not null default '[]'::jsonb,
  failed jsonb not null default '[]'::jsonb,
  skipped jsonb not null default '[]'::jsonb,
  emitted_at timestamptz not null default now()
);
