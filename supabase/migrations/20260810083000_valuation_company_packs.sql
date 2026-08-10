-- Valuation company-pack read model.
-- Python calculates; Supabase stores one latest pack per (symbol, window);
-- Node serves instantly and keeps the previous pack if Python is unavailable.

create table if not exists public.valuation_company_packs (
  id uuid primary key default gen_random_uuid(),
  symbol text not null check (symbol = upper(symbol)),
  window text not null default '5Y'
    check (window in ('1Y', '3Y', '5Y', '10Y', 'MAX')),
  peer_limit integer not null default 12
    check (peer_limit > 0 and peer_limit <= 40),
  generated_at timestamptz not null default now(),
  source_as_of text,
  status text not null default 'ready'
    check (status in ('ready', 'stale', 'failed', 'computing')),
  freshness text not null default 'fresh'
    check (freshness in ('fresh', 'aging', 'stale')),
  schema_version text not null default '1.0',
  calculation_version text not null default 'valuation_company_pack_v1',
  engine text not null default 'unified_valuation_engine',
  engine_version text not null default '3.0',
  data_quality jsonb not null default '{}'::jsonb
    check (jsonb_typeof(data_quality) = 'object'),
  health_score numeric(6,2),
  health_band text,
  coverage_pct numeric(6,2),
  price_age_hours numeric(10,2),
  ratio_age_hours numeric(10,2),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  created_at timestamptz not null default now()
);

create index if not exists valuation_company_packs_symbol_generated_idx
  on public.valuation_company_packs (symbol, generated_at desc);

create index if not exists valuation_company_packs_symbol_window_generated_idx
  on public.valuation_company_packs (symbol, window, generated_at desc);

create index if not exists valuation_company_packs_status_generated_idx
  on public.valuation_company_packs (status, generated_at desc);

-- Fast latest lookup: one row per (symbol, window).
create table if not exists public.valuation_company_packs_latest (
  symbol text not null check (symbol = upper(symbol)),
  window text not null default '5Y'
    check (window in ('1Y', '3Y', '5Y', '10Y', 'MAX')),
  pack_id uuid not null references public.valuation_company_packs(id) on delete cascade,
  generated_at timestamptz not null,
  source_as_of text,
  status text not null default 'ready'
    check (status in ('ready', 'stale', 'failed', 'computing')),
  freshness text not null default 'fresh'
    check (freshness in ('fresh', 'aging', 'stale')),
  schema_version text not null default '1.0',
  calculation_version text not null default 'valuation_company_pack_v1',
  data_quality jsonb not null default '{}'::jsonb
    check (jsonb_typeof(data_quality) = 'object'),
  health_score numeric(6,2),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  updated_at timestamptz not null default now(),
  primary key (symbol, window)
);

create index if not exists valuation_company_packs_latest_generated_idx
  on public.valuation_company_packs_latest (generated_at desc);

alter table public.valuation_company_packs enable row level security;
alter table public.valuation_company_packs_latest enable row level security;

comment on table public.valuation_company_packs is
  'Historical valuation company packs for audit and validation.';
comment on table public.valuation_company_packs_latest is
  'Latest valuation company pack per symbol/window. Node serves these so page loads do not recompute.';

create or replace function public.cleanup_valuation_company_packs(retention_days integer default 30)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  deleted integer;
begin
  delete from public.valuation_company_packs
  where generated_at < now() - make_interval(days => greatest(1, retention_days));
  get diagnostics deleted = row_count;
  return deleted;
end;
$$;

revoke all on function public.cleanup_valuation_company_packs(integer) from public;
grant execute on function public.cleanup_valuation_company_packs(integer) to service_role;
