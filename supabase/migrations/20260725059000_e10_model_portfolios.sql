-- E10 Portfolio Construction P0 persistence (WBS E10-001–005)
-- Model portfolios only. No execution / OMS / broker tables.

create table if not exists public.e10_portfolio (
  id uuid primary key default gen_random_uuid(),
  as_of date not null,
  universe_id text not null,
  mandate_id text not null,
  book_id text not null,
  cash_allocation double precision not null,
  expected_volatility double precision not null,
  vol_target double precision not null,
  portfolio_confidence double precision not null,
  gross double precision not null,
  net double precision not null,
  weights jsonb not null,
  validation jsonb not null,
  portfolio jsonb not null,
  state jsonb not null,
  model_version text not null,
  research_only boolean not null default true,
  execution boolean not null default false,
  created_at timestamptz not null default now(),
  unique (as_of, universe_id, mandate_id, book_id)
);

create index if not exists e10_portfolio_asof_idx
  on public.e10_portfolio (as_of desc);
