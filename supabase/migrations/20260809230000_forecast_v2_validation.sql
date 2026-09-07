-- Cross-sectional forecast rankings and out-of-sample validation metrics.
create table if not exists public.research_forecast_rankings (
  id uuid primary key default gen_random_uuid(),
  forecast_id uuid not null unique references public.research_forecasts(id) on delete cascade,
  forecast_date date not null, horizon text not null check (horizon in ('1d','5d','20d')),
  symbol text not null, universe_size integer not null check (universe_size > 0),
  forecast_rank integer not null check (forecast_rank > 0),
  percentile numeric not null check (percentile between 0 and 1),
  decile integer not null check (decile between 1 and 10),
  created_at timestamptz not null default now()
);

create table if not exists public.research_forecast_cross_section_metrics (
  id uuid primary key default gen_random_uuid(),
  forecast_date date not null, horizon text not null check (horizon in ('1d','5d','20d')),
  observations integer not null, rank_ic numeric,
  decile_returns jsonb not null default '{}'::jsonb check (jsonb_typeof(decile_returns) = 'object'),
  top_bottom_spread numeric, point_in_time_safe boolean not null default true check (point_in_time_safe),
  created_at timestamptz not null default now(),
  unique (forecast_date, horizon)
);

create index if not exists forecast_rankings_date_horizon_idx on public.research_forecast_rankings (forecast_date desc, horizon, forecast_rank);
create index if not exists forecast_cross_section_horizon_date_idx on public.research_forecast_cross_section_metrics (horizon, forecast_date desc);
alter table public.research_forecast_rankings enable row level security;
alter table public.research_forecast_cross_section_metrics enable row level security;
comment on table public.research_forecast_rankings is 'Daily cross-sectional forecast ranks; D10 is the highest expected-alpha decile.';
comment on table public.research_forecast_cross_section_metrics is 'Out-of-sample Rank IC and realized decile returns by forecast date and horizon.';
