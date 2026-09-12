-- Founder Portfolio: private transaction ledger and deliberately separate public disclosure.
-- Public clients never receive quantities, prices, fees, or personal capital values.

create extension if not exists pgcrypto;

create or replace function public.is_founder_portfolio_admin()
returns boolean
language sql
stable
security invoker
set search_path = public
as $$
  select auth.uid() = 'c56e4d07-273c-49c9-86a5-a4445e687ece'::uuid
    or lower(coalesce(auth.jwt() ->> 'email', '')) = 'shivam.agw06@gmail.com';
$$;

create table if not exists public.founder_portfolio_settings (
  portfolio_id text primary key default 'founder',
  name text not null default 'Founder''s Portfolio',
  launch_date date,
  base_currency text not null default 'INR' check (base_currency in ('INR','USD')),
  benchmark text not null default 'Blended benchmark',
  benchmark_components text not null default '^NSEI:60,^GSPC:40',
  portfolio_return_pct numeric,
  benchmark_return_pct numeric,
  twr_pct numeric,
  xirr_pct numeric,
  volatility_pct numeric,
  max_drawdown_pct numeric,
  var_95_pct numeric,
  beta numeric,
  largest_position_pct numeric,
  top_five_pct numeric,
  hhi numeric,
  cash_weight_pct numeric check (cash_weight_pct is null or cash_weight_pct between 0 and 100),
  disclosure_delay text not null default 'After market close',
  status text not null default 'preparing' check (status in ('preparing','live','paused')),
  last_published_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.founder_portfolio_transactions (
  id uuid primary key default gen_random_uuid(),
  trade_date date not null,
  symbol text not null,
  asset_name text not null,
  asset_type text not null check (asset_type in ('indian_stock','us_stock','mutual_fund','etf','cash')),
  market text,
  provider_key text,
  currency text not null default 'INR' check (currency in ('INR','USD')),
  action text not null check (action in ('buy','sell','dividend','fee','deposit','withdrawal')),
  quantity numeric not null check (quantity >= 0),
  price numeric not null check (price >= 0),
  fees numeric not null default 0 check (fees >= 0),
  notes text,
  created_by uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.founder_portfolio_disclosures (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  asset_name text not null,
  asset_type text not null check (asset_type in ('indian_stock','us_stock','mutual_fund','etf','cash')),
  market text,
  provider_key text,
  country text,
  currency text not null default 'INR' check (currency in ('INR','USD')),
  public_weight numeric not null check (public_weight between 0 and 100),
  return_pct numeric,
  conviction text check (conviction is null or conviction in ('Core','High','Medium','Watch')),
  status text not null default 'Holding' check (status in ('Holding','Increased','Reduced','Exited','Watch')),
  sector text,
  entry_month date,
  thesis text,
  change_note text,
  source text not null default 'manual_disclosure',
  latest_price numeric,
  price_source text,
  price_as_of timestamptz,
  is_published boolean not null default false,
  updated_at timestamptz not null default now(),
  unique(symbol, asset_type, market)
);

create table if not exists public.founder_portfolio_snapshots (
  id uuid primary key default gen_random_uuid(), snapshot_date date not null unique,
  total_value_inr numeric not null, cash_value_inr numeric not null, net_external_flow_inr numeric not null default 0,
  daily_return_pct numeric, portfolio_index numeric not null default 100, benchmark_index numeric not null default 100,
  twr_pct numeric, xirr_pct numeric, holdings jsonb not null default '[]'::jsonb,
  allocation jsonb not null default '{}'::jsonb, risk jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.founder_portfolio_performance (
  snapshot_date date primary key, portfolio_index numeric not null, benchmark_index numeric not null,
  daily_return_pct numeric, benchmark_daily_return_pct numeric, twr_pct numeric, drawdown_pct numeric,
  updated_at timestamptz not null default now()
);

create table if not exists public.founder_portfolio_validation_reports (
  id uuid primary key default gen_random_uuid(), run_at timestamptz not null default now(),
  status text not null check (status in ('OK','FAILED','PARTIAL')), asset_count integer not null default 0,
  priced_count integer not null default 0, snapshot_written boolean not null default false,
  missing_assets jsonb not null default '[]'::jsonb, sources jsonb not null default '{}'::jsonb,
  metrics jsonb not null default '{}'::jsonb, message text not null
);

create table if not exists public.founder_portfolio_attribution (
  valuation_date date not null,
  symbol text not null,
  asset_name text not null,
  asset_type text not null,
  market text not null default '',
  contribution_pct numeric not null,
  asset_contribution_pct numeric not null,
  fx_contribution_pct numeric not null default 0,
  weight_pct numeric,
  updated_at timestamptz not null default now(),
  primary key (valuation_date, symbol, asset_type, market)
);

alter table public.founder_portfolio_settings enable row level security;
alter table public.founder_portfolio_transactions enable row level security;
alter table public.founder_portfolio_disclosures enable row level security;
alter table public.founder_portfolio_snapshots enable row level security;
alter table public.founder_portfolio_performance enable row level security;
alter table public.founder_portfolio_validation_reports enable row level security;
alter table public.founder_portfolio_attribution enable row level security;

create policy "Founder settings are publicly readable"
on public.founder_portfolio_settings for select using (true);
create policy "Founder settings are admin managed"
on public.founder_portfolio_settings for all using (public.is_founder_portfolio_admin())
with check (public.is_founder_portfolio_admin());

create policy "Founder transactions are private"
on public.founder_portfolio_transactions for all using (public.is_founder_portfolio_admin())
with check (public.is_founder_portfolio_admin());

create policy "Published founder disclosures are public"
on public.founder_portfolio_disclosures for select using (is_published or public.is_founder_portfolio_admin());
create policy "Founder disclosures are admin managed"
on public.founder_portfolio_disclosures for all using (public.is_founder_portfolio_admin())
with check (public.is_founder_portfolio_admin());

create policy "Founder snapshots are private" on public.founder_portfolio_snapshots for all
using (public.is_founder_portfolio_admin()) with check (public.is_founder_portfolio_admin());
create policy "Founder performance is public" on public.founder_portfolio_performance for select using (true);
create policy "Founder performance is admin managed" on public.founder_portfolio_performance for all
using (public.is_founder_portfolio_admin()) with check (public.is_founder_portfolio_admin());
create policy "Founder validation reports are private" on public.founder_portfolio_validation_reports for all
using (public.is_founder_portfolio_admin()) with check (public.is_founder_portfolio_admin());
create policy "Founder attribution is public" on public.founder_portfolio_attribution for select using (true);
create policy "Founder attribution is admin managed" on public.founder_portfolio_attribution for all
using (public.is_founder_portfolio_admin()) with check (public.is_founder_portfolio_admin());

grant execute on function public.is_founder_portfolio_admin() to anon, authenticated;
grant select on public.founder_portfolio_settings to anon, authenticated;
grant select on public.founder_portfolio_disclosures to anon, authenticated;
grant select on public.founder_portfolio_performance to anon, authenticated;
grant select on public.founder_portfolio_attribution to anon, authenticated;
grant select, insert, update, delete on public.founder_portfolio_settings to authenticated;
grant select, insert, update, delete on public.founder_portfolio_transactions to authenticated;
grant select, insert, update, delete on public.founder_portfolio_disclosures to authenticated;
grant select, insert, update, delete on public.founder_portfolio_snapshots to authenticated;
grant select, insert, update, delete on public.founder_portfolio_performance to authenticated;
grant select, insert, update, delete on public.founder_portfolio_validation_reports to authenticated;
grant select, insert, update, delete on public.founder_portfolio_attribution to authenticated;

insert into public.founder_portfolio_settings (portfolio_id)
values ('founder')
on conflict (portfolio_id) do nothing;
