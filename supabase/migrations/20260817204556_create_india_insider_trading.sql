create table if not exists public.insider_trading_imports (
  id uuid primary key,
  country text not null default 'IN' check (country in ('IN', 'US')),
  source_file text not null,
  file_sha256 text not null,
  status text not null default 'processing' check (status in ('processing', 'completed', 'failed')),
  date_from date,
  date_to date,
  records_seen integer not null default 0,
  records_accepted integer not null default 0,
  records_rejected integer not null default 0,
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (country, file_sha256)
);

create table if not exists public.insider_trades (
  id uuid primary key,
  natural_key text not null unique,
  country text not null default 'IN' check (country in ('IN', 'US')),
  stock_name text not null,
  insider_name text not null,
  insider_category text,
  action text not null,
  reported_date date not null,
  period_from date,
  period_to date,
  quantity numeric,
  post_transaction_holding numeric,
  traded_percent numeric,
  average_price numeric,
  transaction_value numeric,
  regulation text,
  security_type text,
  transaction_mode text,
  signal_type text not null default 'other',
  source_file text not null,
  source_sheet text,
  source_row integer,
  import_id uuid not null references public.insider_trading_imports(id) on delete cascade,
  is_public boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists insider_trades_country_date_idx on public.insider_trades(country, reported_date desc);
create index if not exists insider_trades_stock_idx on public.insider_trades(country, stock_name, reported_date desc);
create index if not exists insider_trades_signal_idx on public.insider_trades(country, signal_type, reported_date desc);
create index if not exists insider_trading_imports_created_idx on public.insider_trading_imports(created_at desc);

alter table public.insider_trading_imports enable row level security;
alter table public.insider_trades enable row level security;
revoke all on public.insider_trading_imports from anon, authenticated;
revoke all on public.insider_trades from anon, authenticated;

comment on table public.insider_trades is 'Server-curated insider disclosures imported through the AGI data administration workflow.';
