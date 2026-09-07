-- Validation & Backtesting P0 persistence (WBS BT-001–005)
-- Replay schema only. Never clobbers production engine current tables.

create table if not exists public.bt_replay_run (
  run_id text primary key,
  dataset_id text not null,
  dataset_version text not null,
  universe_id text not null,
  status text not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  n_days integer not null default 0,
  n_symbols integer not null default 0,
  engine_versions jsonb not null default '{}'::jsonb,
  formula_versions jsonb not null default '{}'::jsonb,
  flags jsonb not null default '{"BACKTEST": true, "LIVE": false}'::jsonb,
  production_influence boolean not null default false,
  live boolean not null default false,
  error text,
  created_at timestamptz not null default now()
);

create table if not exists public.bt_replay_result (
  run_id text primary key references public.bt_replay_run(run_id) on delete cascade,
  days jsonb not null,
  summary jsonb,
  dashboard jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists bt_replay_run_started_idx
  on public.bt_replay_run (started_at desc);
