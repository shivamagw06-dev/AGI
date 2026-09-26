-- Point-in-time-safe feature snapshots and probabilistic research forecasts.
create table if not exists public.research_feature_snapshots (
  id uuid primary key default gen_random_uuid(),
  confluence_event_id uuid not null unique references public.research_confluence_events(id) on delete cascade,
  symbol text not null, captured_at timestamptz not null, feature_version text not null,
  market_regime text, sector text,
  features jsonb not null check (jsonb_typeof(features) = 'object'),
  completeness numeric not null check (completeness between 0 and 1),
  point_in_time_safe boolean not null default true check (point_in_time_safe),
  research_only boolean not null default true check (research_only),
  created_at timestamptz not null default now()
);

create table if not exists public.research_forecasts (
  id uuid primary key default gen_random_uuid(),
  feature_snapshot_id uuid not null references public.research_feature_snapshots(id) on delete cascade,
  confluence_event_id uuid not null references public.research_confluence_events(id) on delete cascade,
  symbol text not null, forecast_time timestamptz not null,
  horizon text not null check (horizon in ('1d','5d','20d')),
  expected_alpha_pct numeric not null, probability_positive numeric not null check (probability_positive between 0 and 1),
  p10 numeric not null, p25 numeric not null, p50 numeric not null, p75 numeric not null, p90 numeric not null,
  confidence numeric not null check (confidence between 0 and 100),
  model_agreement numeric not null check (model_agreement between 0 and 1),
  model_version text not null, feature_version text not null, market_regime text,
  component_forecasts jsonb not null check (jsonb_typeof(component_forecasts) = 'object'),
  explanation jsonb not null default '{}'::jsonb check (jsonb_typeof(explanation) = 'object'),
  research_only boolean not null default true check (research_only),
  created_at timestamptz not null default now(),
  unique (confluence_event_id, horizon)
);

create table if not exists public.research_forecast_outcomes (
  id uuid primary key default gen_random_uuid(),
  forecast_id uuid not null unique references public.research_forecasts(id) on delete cascade,
  observed_at timestamptz not null, actual_alpha_pct numeric not null,
  forecast_error numeric not null, direction_correct boolean not null,
  brier_score numeric not null check (brier_score between 0 and 1),
  created_at timestamptz not null default now()
);

create index if not exists research_feature_symbol_time_idx on public.research_feature_snapshots (symbol, captured_at desc);
create index if not exists research_forecast_symbol_time_idx on public.research_forecasts (symbol, forecast_time desc);
create index if not exists research_forecast_horizon_time_idx on public.research_forecasts (horizon, forecast_time desc);
alter table public.research_feature_snapshots enable row level security;
alter table public.research_forecasts enable row level security;
alter table public.research_forecast_outcomes enable row level security;
comment on table public.research_feature_snapshots is 'Immutable point-in-time features; no observation after captured_at is permitted.';
comment on table public.research_forecasts is 'Research-only probabilistic excess-return forecasts, separate by horizon.';
comment on table public.research_forecast_outcomes is 'Realized forecast errors and probability calibration observations.';
