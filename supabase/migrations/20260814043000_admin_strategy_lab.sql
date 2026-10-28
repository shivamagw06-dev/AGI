-- AGI Strategy Lab: private, governed systematic-research records.
-- No anonymous policies are created. Server-side service-role access only.

create table if not exists public.strategy_lab_strategies (
  id uuid primary key default gen_random_uuid(),
  strategy_key text not null unique,
  name text not null,
  family text not null,
  lifecycle text not null default 'DRAFT'
    check (lifecycle in ('DRAFT','BACKTESTING','VALIDATING','PAPER','OPERATIONAL','SUSPENDED','RETIRED')),
  overlap_strategy text,
  description text not null,
  owner_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.strategy_lab_versions (
  id uuid primary key default gen_random_uuid(),
  strategy_id uuid not null references public.strategy_lab_strategies(id),
  version text not null,
  formula jsonb not null,
  parameters jsonb not null,
  universe jsonb not null,
  data_requirements jsonb not null,
  risk_policy jsonb not null default '{}'::jsonb,
  cost_policy jsonb not null default '{}'::jsonb,
  pit_status text not null default 'PIT_LIMITED',
  created_by uuid,
  created_at timestamptz not null default now(),
  unique(strategy_id, version)
);

create table if not exists public.strategy_lab_runs (
  id uuid primary key default gen_random_uuid(),
  strategy_version_id uuid not null references public.strategy_lab_versions(id),
  run_type text not null check (run_type in ('CURRENT','BACKTEST','VALIDATION','PAPER')),
  status text not null check (status in ('QUEUED','RUNNING','COMPLETE','COMPLETE_WITH_WARNINGS','FAILED')),
  data_snapshot jsonb not null,
  parameters jsonb not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  error jsonb
);

create table if not exists public.strategy_lab_signals (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.strategy_lab_runs(id),
  company_id text,
  ticker text not null,
  signal text not null check (signal in ('BUY','SELL','HOLD','EXIT','PAIR_LONG','PAIR_SHORT')),
  eligibility text not null default 'RESEARCH_ONLY'
    check (eligibility in ('RESEARCH_ONLY','BACKTESTED','VALIDATED','PAPER','TRADE_ELIGIBLE','SUSPENDED')),
  score numeric,
  confidence text,
  entry numeric,
  stop numeric,
  target numeric,
  expected_holding_period text,
  factor_contributions jsonb not null,
  explanation jsonb not null,
  data_quality jsonb not null,
  pit_status text not null,
  reason_codes text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists public.strategy_lab_backtests (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null unique references public.strategy_lab_runs(id),
  train_period daterange,
  validation_period daterange,
  test_period daterange,
  benchmark text,
  metrics jsonb not null,
  costs jsonb not null,
  coverage jsonb not null,
  limitations jsonb not null,
  survivorship_status text not null default 'SURVIVORSHIP_BIAS_RISK',
  lookahead_check boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.strategy_lab_validations (
  id uuid primary key default gen_random_uuid(),
  strategy_version_id uuid not null references public.strategy_lab_versions(id),
  run_id uuid references public.strategy_lab_runs(id),
  gates jsonb not null,
  passed boolean not null default false,
  overfit_risk text not null default 'UNASSESSED',
  decision text not null default 'DO_NOT_DEPLOY',
  validated_by uuid,
  created_at timestamptz not null default now()
);

create table if not exists public.strategy_lab_paper_positions (
  id uuid primary key default gen_random_uuid(),
  strategy_version_id uuid not null references public.strategy_lab_versions(id),
  signal_id uuid references public.strategy_lab_signals(id),
  ticker text not null,
  side text not null check (side in ('LONG','SHORT')),
  opened_at timestamptz not null,
  closed_at timestamptz,
  entry numeric not null,
  exit numeric,
  quantity numeric not null,
  costs numeric not null default 0,
  pnl numeric,
  status text not null default 'OPEN' check (status in ('OPEN','CLOSED','SUSPENDED'))
);

create table if not exists public.strategy_lab_health (
  strategy_version_id uuid primary key references public.strategy_lab_versions(id),
  data_health jsonb not null default '{}'::jsonb,
  signal_health jsonb not null default '{}'::jsonb,
  performance_health jsonb not null default '{}'::jsonb,
  execution_health jsonb not null default '{}'::jsonb,
  automatic_suspension_reason text,
  checked_at timestamptz not null default now()
);

create table if not exists public.strategy_lab_audit_log (
  id bigint generated always as identity primary key,
  actor_id uuid,
  action text not null,
  entity_type text not null,
  entity_id text not null,
  before_state jsonb,
  after_state jsonb,
  created_at timestamptz not null default now()
);

alter table public.strategy_lab_strategies enable row level security;
alter table public.strategy_lab_versions enable row level security;
alter table public.strategy_lab_runs enable row level security;
alter table public.strategy_lab_signals enable row level security;
alter table public.strategy_lab_backtests enable row level security;
alter table public.strategy_lab_validations enable row level security;
alter table public.strategy_lab_paper_positions enable row level security;
alter table public.strategy_lab_health enable row level security;
alter table public.strategy_lab_audit_log enable row level security;

create index if not exists strategy_lab_runs_version_started_idx
  on public.strategy_lab_runs(strategy_version_id, started_at desc);
create index if not exists strategy_lab_signals_run_score_idx
  on public.strategy_lab_signals(run_id, score desc);
create index if not exists strategy_lab_audit_entity_idx
  on public.strategy_lab_audit_log(entity_type, entity_id, created_at desc);
