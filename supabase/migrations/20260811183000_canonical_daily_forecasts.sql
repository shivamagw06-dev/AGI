-- Preserve historical intraday forecasts, but designate exactly one immutable
-- point-in-time snapshot per NSE symbol and trading date for model validation.
alter table public.research_feature_snapshots
  add column if not exists snapshot_date date
    generated always as ((captured_at at time zone 'Asia/Kolkata')::date) stored,
  add column if not exists is_canonical boolean not null default true,
  add column if not exists snapshot_contract_version text not null default 'daily_post_close_v1';

alter table public.research_forecasts
  add column if not exists forecast_date date
    generated always as ((forecast_time at time zone 'Asia/Kolkata')::date) stored,
  add column if not exists is_canonical boolean not null default true,
  add column if not exists target_definition text not null default 'sector_adjusted_close_to_close';

with ranked as (
  select id, row_number() over (
    partition by upper(symbol), snapshot_date
    order by captured_at desc, created_at desc, id desc
  ) as canonical_rank
  from public.research_feature_snapshots
)
update public.research_feature_snapshots snapshot
set is_canonical = ranked.canonical_rank = 1
from ranked
where snapshot.id = ranked.id;

with ranked as (
  select id, row_number() over (
    partition by upper(symbol), forecast_date, horizon
    order by forecast_time desc, created_at desc, id desc
  ) as canonical_rank
  from public.research_forecasts
)
update public.research_forecasts forecast
set is_canonical = ranked.canonical_rank = 1
from ranked
where forecast.id = ranked.id;

create unique index if not exists research_feature_one_canonical_daily_idx
  on public.research_feature_snapshots (upper(symbol), snapshot_date)
  where is_canonical;

create unique index if not exists research_forecast_one_canonical_daily_horizon_idx
  on public.research_forecasts (upper(symbol), forecast_date, horizon)
  where is_canonical;

create index if not exists research_forecast_canonical_horizon_date_idx
  on public.research_forecasts (horizon, forecast_date desc)
  where is_canonical;

comment on column public.research_feature_snapshots.is_canonical is
  'True only for the single latest post-close feature snapshot used for a symbol/trading-date.';
comment on column public.research_forecasts.target_definition is
  'Forward target contract. v1 uses sector-adjusted close-to-close alpha at the stated trading-day horizon.';
