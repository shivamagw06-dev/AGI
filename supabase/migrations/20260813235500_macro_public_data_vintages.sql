-- AGI public macro data layer: point-in-time observations, release vintages and source registry.
-- Raw licensed vendor content must not be written here. This repository is for public/official data.

create table if not exists public.macro_public_series_registry (
  series_id text primary key,
  country_code text not null,
  domain text not null,
  label text not null,
  unit text,
  frequency text not null,
  primary_source text not null,
  source_url text,
  source_series_id text,
  license_class text not null default 'PUBLIC_OFFICIAL',
  refresh_policy text not null default 'ON_RELEASE',
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (country_code, source_series_id, primary_source)
);

create table if not exists public.macro_public_observations (
  id uuid primary key default gen_random_uuid(),
  series_id text not null references public.macro_public_series_registry(series_id),
  country_code text not null,
  period_date date not null,
  value_numeric numeric,
  value_text text,
  unit text,
  frequency text not null,
  release_date timestamptz not null,
  available_at timestamptz not null,
  vintage_date date not null,
  revision_number integer not null default 0,
  is_forecast boolean not null default false,
  source text not null,
  source_url text,
  source_payload_hash text,
  quality_status text not null default 'UNVERIFIED',
  metadata jsonb not null default '{}'::jsonb,
  ingested_at timestamptz not null default now(),
  unique (series_id, country_code, period_date, vintage_date, revision_number)
);

create index if not exists macro_public_observations_pit_idx
  on public.macro_public_observations (country_code, series_id, available_at desc, period_date desc);
create index if not exists macro_public_observations_release_idx
  on public.macro_public_observations (release_date desc);

create table if not exists public.macro_public_ingestion_runs (
  run_id uuid primary key default gen_random_uuid(),
  source text not null,
  status text not null default 'RUNNING',
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  rows_received integer not null default 0,
  rows_accepted integer not null default 0,
  rows_quarantined integer not null default 0,
  error text,
  receipt jsonb not null default '{}'::jsonb
);

alter table public.macro_public_series_registry enable row level security;
alter table public.macro_public_observations enable row level security;
alter table public.macro_public_ingestion_runs enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='macro_public_series_registry' and policyname='macro_public_registry_read') then
    create policy macro_public_registry_read on public.macro_public_series_registry for select to anon, authenticated using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='macro_public_observations' and policyname='macro_public_observations_read') then
    create policy macro_public_observations_read on public.macro_public_observations for select to anon, authenticated using (quality_status in ('VERIFIED','PROVISIONAL'));
  end if;
end $$;

