-- Private licensed macro layer. Raw vendor values must never be exposed through
-- the public macro tables or anonymous API policies.

create table if not exists public.macro_licensed_observations (
  id uuid primary key default gen_random_uuid(),
  country_code text not null,
  series_id text not null,
  label text not null,
  as_of_date date not null,
  relative_period text not null,
  value_numeric numeric not null,
  unit text,
  frequency text not null,
  source text not null,
  source_file text not null,
  source_sheet text not null,
  source_hash text not null,
  licence_class text not null default 'LICENSED_INTERNAL_ONLY',
  pit_status text not null default 'FETCH_VINTAGE_ONLY',
  publish_allowed boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  ingested_at timestamptz not null default now(),
  unique (country_code, series_id, as_of_date, relative_period, source)
);

create table if not exists public.macro_licensed_forecasts (
  id uuid primary key default gen_random_uuid(),
  country_code text not null,
  series_id text not null,
  label text not null,
  vintage_date date not null,
  target_year integer not null,
  horizon_years integer not null,
  value_numeric numeric not null,
  unit text,
  source text not null,
  source_file text not null,
  source_sheet text not null,
  source_hash text not null,
  licence_class text not null default 'LICENSED_INTERNAL_ONLY',
  pit_status text not null default 'FETCH_VINTAGE_ONLY',
  publish_allowed boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  ingested_at timestamptz not null default now(),
  unique (country_code, series_id, vintage_date, target_year, source)
);

create table if not exists public.macro_licensed_quarantine (
  id uuid primary key default gen_random_uuid(),
  source_file text not null,
  source_sheet text not null,
  row_label text,
  period_label text,
  raw_value text,
  reason text not null,
  source_hash text not null,
  quarantined_at timestamptz not null default now(),
  unique (source_file, source_sheet, row_label, period_label, reason, source_hash)
);

alter table public.macro_licensed_observations enable row level security;
alter table public.macro_licensed_forecasts enable row level security;
alter table public.macro_licensed_quarantine enable row level security;

create index if not exists macro_licensed_observations_lookup_idx
  on public.macro_licensed_observations (country_code, series_id, as_of_date desc);
create index if not exists macro_licensed_forecasts_lookup_idx
  on public.macro_licensed_forecasts (country_code, series_id, vintage_date desc, target_year);
