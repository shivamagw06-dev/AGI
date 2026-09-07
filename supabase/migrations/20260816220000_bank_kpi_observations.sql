-- Point-in-time commercial-bank KPI observations used by the financials
-- valuation engine. AI extraction may only create PROPOSED rows; promotion is
-- a separate evidence-validation decision.
create table if not exists public.bank_kpi_observations (
  observation_id uuid primary key default gen_random_uuid(),
  symbol text not null,
  company_name text,
  metric_key text not null check (metric_key in (
    'loans','loan_growth','deposits','deposit_growth','casa',
    'cost_of_deposits','yield_on_advances','nim','nii_growth',
    'cost_to_income','gnpa','nnpa','slippage','credit_cost','pcr',
    'roa','roe','cet1','crar','rwa','lcr','nsfr','book_value',
    'book_value_per_share','tangible_book','tangible_book_value_per_share',
    'normalized_eps','fee_income','dividend_payout'
  )),
  value numeric not null,
  unit text not null,
  currency text,
  period text not null,
  period_end date not null,
  frequency text not null check (frequency in ('QUARTERLY','ANNUAL','TTM')),
  basis text not null default 'REPORTED',
  consolidation_scope text not null default 'STANDALONE',
  annualized boolean not null default false,
  source_id text not null,
  source_url text not null,
  source_title text,
  source_published_at timestamptz,
  available_at timestamptz not null,
  retrieved_at timestamptz not null default now(),
  source_excerpt text,
  source_hash text,
  extraction_method text not null default 'DETERMINISTIC',
  validation_status text not null default 'PROPOSED' check (
    validation_status in ('PROPOSED','VALIDATED','TRUSTED','QUARANTINED','REJECTED','SUPERSEDED')
  ),
  confidence numeric not null default 0 check (confidence between 0 and 1),
  validation_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (symbol, metric_key, period_end, basis, consolidation_scope, source_id, available_at)
);

create index if not exists idx_bank_kpi_symbol_period
  on public.bank_kpi_observations(symbol, period_end desc, metric_key);
create index if not exists idx_bank_kpi_pit
  on public.bank_kpi_observations(symbol, metric_key, available_at desc);
create index if not exists idx_bank_kpi_validation
  on public.bank_kpi_observations(validation_status, symbol, period_end desc);

alter table public.bank_kpi_observations enable row level security;

comment on table public.bank_kpi_observations is
  'Point-in-time bank operating KPIs with immutable source provenance. AI output remains PROPOSED or QUARANTINED until independently validated.';

