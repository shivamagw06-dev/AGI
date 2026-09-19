-- Valuation Intelligence — Institutional Consensus Dashboard
-- Capital IQ Excel is an import source only. Live reads come from these tables.
-- File-backed store remains the default runtime; this migration enables Postgres.

create table if not exists public.valuation_consensus (
  ticker text primary key,
  security_name text,
  company_name text,
  exchange text,
  primary_exchange text,
  all_listings text,
  indices text,
  trading_status text,
  cmp numeric,
  currency text,
  sector text,
  industry text,
  industry_classification text,
  parent text,
  investors text,
  competitors text,
  subsidiaries text,
  company_type text,
  country text,
  website text,
  products text,
  description text,
  market_cap numeric,
  enterprise_value numeric,
  revenue numeric,
  ebitda numeric,
  target_price numeric,
  target_high numeric,
  target_low numeric,
  target_std_dev numeric,
  upside numeric,
  buy_count numeric,
  outperform_count numeric,
  hold_count numeric,
  sell_count numeric,
  no_opinion_count numeric,
  coverage numeric,
  avg_volume numeric,
  return_ytd numeric,
  return_1d numeric,
  return_1w numeric,
  return_1m numeric,
  return_3m numeric,
  return_6m numeric,
  return_9m numeric,
  return_1y numeric,
  return_3y numeric,
  return_5y numeric,
  returns jsonb not null default '{}'::jsonb,
  extras jsonb not null default '{}'::jsonb,
  source_file text,
  version_id text,
  updated_at timestamptz not null default now()
);

create index if not exists valuation_consensus_sector_idx
  on public.valuation_consensus (sector);
create index if not exists valuation_consensus_industry_idx
  on public.valuation_consensus (industry);
create index if not exists valuation_consensus_upside_idx
  on public.valuation_consensus (upside desc nulls last);
create index if not exists valuation_consensus_mcap_idx
  on public.valuation_consensus (market_cap desc nulls last);
create index if not exists valuation_consensus_coverage_idx
  on public.valuation_consensus (coverage desc nulls last);
create index if not exists valuation_consensus_company_fts_idx
  on public.valuation_consensus
  using gin (to_tsvector('simple', coalesce(company_name, '') || ' ' || coalesce(products, '') || ' ' || coalesce(description, '')));

create table if not exists public.valuation_consensus_versions (
  version_id text primary key,
  source_file text,
  imported_by text,
  import_id text,
  previous_version_id text,
  row_count integer not null default 0,
  diff jsonb not null default '{}'::jsonb,
  snapshot jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.valuation_consensus_imports (
  import_id text primary key,
  filename text,
  imported_by text,
  status text not null default 'preview'
    check (status in ('preview', 'validated', 'invalid', 'published')),
  row_count integer not null default 0,
  unresolved_count integer not null default 0,
  columns_mapped jsonb not null default '[]'::jsonb,
  columns_unmapped jsonb not null default '[]'::jsonb,
  diff jsonb not null default '{}'::jsonb,
  validation_errors jsonb not null default '[]'::jsonb,
  published_version_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.valuation_consensus_audit (
  id bigserial primary key,
  event text not null,
  version_id text,
  import_id text,
  imported_by text,
  source_file text,
  rows_added integer,
  rows_removed integer,
  rows_changed integer,
  row_count integer,
  rollback_version text,
  detail jsonb not null default '{}'::jsonb,
  at timestamptz not null default now()
);

alter table public.valuation_consensus enable row level security;
alter table public.valuation_consensus_versions enable row level security;
alter table public.valuation_consensus_imports enable row level security;
alter table public.valuation_consensus_audit enable row level security;

-- Public / authenticated read of published consensus rows
drop policy if exists valuation_consensus_read on public.valuation_consensus;
create policy valuation_consensus_read on public.valuation_consensus
  for select to anon, authenticated
  using (true);

-- Writes via service role only (admin import pipeline)
drop policy if exists valuation_consensus_versions_read on public.valuation_consensus_versions;
create policy valuation_consensus_versions_read on public.valuation_consensus_versions
  for select to authenticated
  using (true);

drop policy if exists valuation_consensus_audit_read on public.valuation_consensus_audit;
create policy valuation_consensus_audit_read on public.valuation_consensus_audit
  for select to authenticated
  using (true);
