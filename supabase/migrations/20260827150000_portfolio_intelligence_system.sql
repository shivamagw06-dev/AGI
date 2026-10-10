-- AGI Portfolio Intelligence System
-- Transaction-led client portfolios, market provenance, performance snapshots,
-- scenarios, corporate actions and fund look-through reference data.

alter table public.client_portfolios
  add column if not exists risk_free_rate numeric not null default 0.065,
  add column if not exists benchmark_components jsonb not null default '[{"symbol":"NIFTY","weight":0.6},{"symbol":"^GSPC","weight":0.4}]'::jsonb,
  add column if not exists settings jsonb not null default '{}'::jsonb;

alter table public.client_portfolio_holdings
  add column if not exists instrument_id uuid,
  add column if not exists country text,
  add column if not exists provider_key text,
  add column if not exists isin text,
  add column if not exists holding_since date,
  add column if not exists price_as_of timestamptz,
  add column if not exists price_source text,
  add column if not exists data_quality text not null default 'manual',
  add column if not exists tags text[] not null default '{}';

create table if not exists public.portfolio_instruments (
  id uuid primary key default gen_random_uuid(),
  canonical_key text not null unique,
  symbol text not null,
  asset_name text not null,
  asset_type text not null check (asset_type in ('indian_stock', 'us_stock', 'mutual_fund', 'etf', 'index', 'cash')),
  exchange text not null default '',
  country text,
  currency text not null check (currency in ('INR', 'USD')),
  isin text,
  provider_keys jsonb not null default '{}'::jsonb,
  sector text,
  industry text,
  theme_tags text[] not null default '{}',
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.portfolio_instrument_aliases (
  id bigint generated always as identity primary key,
  instrument_id uuid not null references public.portfolio_instruments(id) on delete cascade,
  provider text not null,
  alias text not null,
  unique (provider, alias)
);

alter table public.client_portfolio_holdings
  add constraint client_portfolio_holdings_instrument_fk
  foreign key (instrument_id) references public.portfolio_instruments(id) on delete set null;

create table if not exists public.client_portfolio_transactions (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  instrument_id uuid references public.portfolio_instruments(id) on delete set null,
  trade_date date not null,
  action text not null check (action in (
    'OPENING_BALANCE', 'BUY', 'SELL', 'DIVIDEND', 'INTEREST', 'DEPOSIT',
    'WITHDRAWAL', 'FEE', 'TAX', 'SPLIT', 'TRANSFER_IN', 'TRANSFER_OUT'
  )),
  symbol text not null,
  asset_name text not null,
  asset_type text not null check (asset_type in ('indian_stock', 'us_stock', 'mutual_fund', 'etf', 'cash')),
  market text not null default '',
  country text,
  currency text not null default 'INR' check (currency in ('INR', 'USD')),
  quantity numeric not null default 0 check (quantity >= 0),
  price numeric not null default 0 check (price >= 0),
  amount numeric not null default 0,
  fees numeric not null default 0 check (fees >= 0),
  fx_rate_to_inr numeric not null default 1 check (fx_rate_to_inr > 0),
  external_flow_inr numeric not null default 0,
  sector text,
  notes text,
  source text not null default 'manual',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_portfolio_snapshots (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  snapshot_date date not null,
  total_value_inr numeric not null,
  invested_value_inr numeric not null default 0,
  cash_value_inr numeric not null default 0,
  net_external_flow_inr numeric not null default 0,
  daily_return_pct numeric,
  portfolio_index numeric,
  benchmark_index numeric,
  twr_pct numeric,
  xirr_pct numeric,
  analytics jsonb not null default '{}'::jsonb,
  data_quality jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (portfolio_id, snapshot_date)
);

create table if not exists public.client_portfolio_position_snapshots (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  snapshot_date date not null,
  holding_id uuid references public.client_portfolio_holdings(id) on delete set null,
  instrument_id uuid references public.portfolio_instruments(id) on delete set null,
  symbol text not null,
  quantity numeric not null,
  price numeric not null,
  currency text not null,
  fx_rate_to_inr numeric not null,
  market_value_inr numeric not null,
  weight_pct numeric,
  price_source text,
  price_as_of timestamptz,
  created_at timestamptz not null default now(),
  unique (portfolio_id, snapshot_date, symbol, holding_id)
);

create table if not exists public.client_portfolio_scenarios (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null,
  assumptions jsonb not null default '{}'::jsonb,
  result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_portfolio_intelligence_events (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  event_key text not null,
  event_type text not null,
  symbol text,
  title text not null,
  summary text,
  impact_score numeric,
  severity text not null default 'info' check (severity in ('info', 'watch', 'high')),
  occurred_at timestamptz not null,
  source text,
  source_url text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (portfolio_id, event_key)
);

create table if not exists public.portfolio_market_prices (
  instrument_id uuid not null references public.portfolio_instruments(id) on delete cascade,
  price_date date not null,
  close_price numeric not null,
  currency text not null,
  source text not null,
  source_as_of timestamptz,
  quality text not null default 'observed',
  created_at timestamptz not null default now(),
  primary key (instrument_id, price_date, source)
);

create table if not exists public.portfolio_fx_rates (
  base_currency text not null,
  quote_currency text not null,
  rate_date date not null,
  rate numeric not null check (rate > 0),
  source text not null,
  source_as_of timestamptz,
  created_at timestamptz not null default now(),
  primary key (base_currency, quote_currency, rate_date, source)
);

create table if not exists public.portfolio_benchmark_prices (
  benchmark_symbol text not null,
  price_date date not null,
  close_price numeric not null,
  currency text not null,
  source text not null,
  source_as_of timestamptz,
  created_at timestamptz not null default now(),
  primary key (benchmark_symbol, price_date, source)
);

create table if not exists public.portfolio_corporate_actions (
  id uuid primary key default gen_random_uuid(),
  instrument_id uuid references public.portfolio_instruments(id) on delete cascade,
  isin text,
  action_type text not null,
  ex_date date,
  record_date date,
  payable_date date,
  ratio numeric,
  cash_amount numeric,
  currency text,
  source text not null,
  source_key text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (source, source_key)
);

create table if not exists public.portfolio_fund_constituents (
  fund_instrument_id uuid not null references public.portfolio_instruments(id) on delete cascade,
  constituent_instrument_id uuid not null references public.portfolio_instruments(id) on delete cascade,
  as_of_date date not null,
  weight_pct numeric not null check (weight_pct >= 0 and weight_pct <= 100),
  source text not null,
  created_at timestamptz not null default now(),
  primary key (fund_instrument_id, constituent_instrument_id, as_of_date, source)
);

create index if not exists client_portfolio_holdings_user_idx on public.client_portfolio_holdings (user_id, portfolio_id);
create index if not exists client_portfolio_holdings_instrument_idx on public.client_portfolio_holdings (instrument_id);
create index if not exists client_portfolio_transactions_user_idx on public.client_portfolio_transactions (user_id, portfolio_id, trade_date desc);
create index if not exists client_portfolio_transactions_instrument_idx on public.client_portfolio_transactions (instrument_id, trade_date desc);
create index if not exists client_portfolio_snapshots_user_idx on public.client_portfolio_snapshots (user_id, portfolio_id, snapshot_date desc);
create index if not exists client_portfolio_position_snapshots_user_idx on public.client_portfolio_position_snapshots (user_id, portfolio_id, snapshot_date desc);
create index if not exists client_portfolio_scenarios_user_idx on public.client_portfolio_scenarios (user_id, portfolio_id, updated_at desc);
create index if not exists client_portfolio_events_user_idx on public.client_portfolio_intelligence_events (user_id, portfolio_id, occurred_at desc);
create index if not exists portfolio_instrument_aliases_instrument_idx on public.portfolio_instrument_aliases (instrument_id);
create index if not exists portfolio_market_prices_date_idx on public.portfolio_market_prices (price_date desc, instrument_id);
create index if not exists portfolio_corporate_actions_instrument_idx on public.portfolio_corporate_actions (instrument_id, ex_date desc);
create index if not exists portfolio_fund_constituents_date_idx on public.portfolio_fund_constituents (fund_instrument_id, as_of_date desc);

alter table public.portfolio_instruments enable row level security;
alter table public.portfolio_instrument_aliases enable row level security;
alter table public.client_portfolio_transactions enable row level security;
alter table public.client_portfolio_snapshots enable row level security;
alter table public.client_portfolio_position_snapshots enable row level security;
alter table public.client_portfolio_scenarios enable row level security;
alter table public.client_portfolio_intelligence_events enable row level security;
alter table public.portfolio_market_prices enable row level security;
alter table public.portfolio_fx_rates enable row level security;
alter table public.portfolio_benchmark_prices enable row level security;
alter table public.portfolio_corporate_actions enable row level security;
alter table public.portfolio_fund_constituents enable row level security;

create policy "Authenticated clients read instruments" on public.portfolio_instruments
  for select to authenticated using (true);
create policy "Authenticated clients read aliases" on public.portfolio_instrument_aliases
  for select to authenticated using (true);
create policy "Authenticated clients read market prices" on public.portfolio_market_prices
  for select to authenticated using (true);
create policy "Authenticated clients read FX rates" on public.portfolio_fx_rates
  for select to authenticated using (true);
create policy "Authenticated clients read benchmarks" on public.portfolio_benchmark_prices
  for select to authenticated using (true);
create policy "Authenticated clients read corporate actions" on public.portfolio_corporate_actions
  for select to authenticated using (true);
create policy "Authenticated clients read fund constituents" on public.portfolio_fund_constituents
  for select to authenticated using (true);

create policy "Clients read their own transactions" on public.client_portfolio_transactions
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Clients create their own transactions" on public.client_portfolio_transactions
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Clients update their own transactions" on public.client_portfolio_transactions
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Clients delete their own transactions" on public.client_portfolio_transactions
  for delete to authenticated using ((select auth.uid()) = user_id);

create policy "Clients manage their own snapshots" on public.client_portfolio_snapshots
  for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Clients manage their own position snapshots" on public.client_portfolio_position_snapshots
  for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Clients manage their own scenarios" on public.client_portfolio_scenarios
  for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Clients read their own intelligence events" on public.client_portfolio_intelligence_events
  for select to authenticated using ((select auth.uid()) = user_id);

grant usage on schema public to authenticated;
grant select on public.portfolio_instruments, public.portfolio_instrument_aliases,
  public.portfolio_market_prices, public.portfolio_fx_rates,
  public.portfolio_benchmark_prices, public.portfolio_corporate_actions,
  public.portfolio_fund_constituents to authenticated;
grant select, insert, update, delete on public.client_portfolio_transactions,
  public.client_portfolio_snapshots, public.client_portfolio_position_snapshots,
  public.client_portfolio_scenarios to authenticated;
grant select on public.client_portfolio_intelligence_events to authenticated;

create or replace function public.record_client_portfolio_transaction(
  p_portfolio_id uuid,
  p_trade_date date,
  p_action text,
  p_symbol text,
  p_asset_name text,
  p_asset_type text,
  p_market text,
  p_currency text,
  p_quantity numeric default 0,
  p_price numeric default 0,
  p_amount numeric default null,
  p_fees numeric default 0,
  p_fx_rate_to_inr numeric default 1,
  p_country text default null,
  p_sector text default null,
  p_notes text default null
) returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_action text := upper(trim(p_action));
  v_symbol text := upper(trim(p_symbol));
  v_transaction_id uuid;
  v_existing public.client_portfolio_holdings%rowtype;
  v_amount numeric := coalesce(p_amount, p_quantity * p_price);
  v_external_flow numeric := 0;
  v_new_quantity numeric;
  v_average_cost numeric;
begin
  if v_user_id is null or not exists (
    select 1 from public.client_portfolios
    where id = p_portfolio_id and user_id = v_user_id
  ) then
    raise exception 'Portfolio access denied';
  end if;

  if v_action not in ('OPENING_BALANCE','BUY','SELL','DIVIDEND','INTEREST','DEPOSIT','WITHDRAWAL','FEE','TAX','SPLIT','TRANSFER_IN','TRANSFER_OUT') then
    raise exception 'Unsupported transaction action';
  end if;

  if v_action in ('DEPOSIT','TRANSFER_IN') then
    v_external_flow := abs(v_amount * p_fx_rate_to_inr);
  elsif v_action in ('WITHDRAWAL','TRANSFER_OUT') then
    v_external_flow := -abs(v_amount * p_fx_rate_to_inr);
  end if;

  insert into public.client_portfolio_transactions (
    portfolio_id, user_id, trade_date, action, symbol, asset_name,
    asset_type, market, country, currency, quantity, price, amount,
    fees, fx_rate_to_inr, external_flow_inr, sector, notes
  ) values (
    p_portfolio_id, v_user_id, p_trade_date, v_action, v_symbol, trim(p_asset_name),
    p_asset_type, upper(coalesce(trim(p_market), '')), p_country, upper(p_currency),
    coalesce(p_quantity, 0), coalesce(p_price, 0), v_amount, coalesce(p_fees, 0),
    p_fx_rate_to_inr, v_external_flow, p_sector, p_notes
  ) returning id into v_transaction_id;

  if v_action in ('OPENING_BALANCE','BUY','TRANSFER_IN') and p_quantity > 0 then
    select * into v_existing
    from public.client_portfolio_holdings
    where portfolio_id = p_portfolio_id
      and symbol = v_symbol
      and asset_type = p_asset_type
      and market = upper(coalesce(trim(p_market), ''))
    for update;

    if found then
      v_new_quantity := v_existing.quantity + p_quantity;
      v_average_cost := case when v_new_quantity > 0 then
        ((v_existing.quantity * v_existing.average_cost) + (p_quantity * p_price) + p_fees) / v_new_quantity
      else 0 end;
      update public.client_portfolio_holdings
      set quantity = v_new_quantity,
          average_cost = v_average_cost,
          current_price = coalesce(nullif(p_price, 0), current_price),
          fx_rate_to_inr = p_fx_rate_to_inr,
          country = coalesce(p_country, country),
          sector = coalesce(p_sector, sector),
          holding_since = least(coalesce(holding_since, p_trade_date), p_trade_date),
          updated_at = now()
      where id = v_existing.id;
    else
      insert into public.client_portfolio_holdings (
        portfolio_id, user_id, symbol, asset_name, asset_type, market, currency,
        quantity, average_cost, current_price, fx_rate_to_inr, country, sector,
        holding_since, data_quality
      ) values (
        p_portfolio_id, v_user_id, v_symbol, trim(p_asset_name), p_asset_type,
        upper(coalesce(trim(p_market), '')), upper(p_currency), p_quantity,
        case when p_quantity > 0 then (p_quantity * p_price + p_fees) / p_quantity else 0 end,
        nullif(p_price, 0), p_fx_rate_to_inr, p_country, p_sector, p_trade_date, 'transaction_ledger'
      );
    end if;
  elsif v_action in ('SELL','TRANSFER_OUT') and p_quantity > 0 then
    select * into v_existing
    from public.client_portfolio_holdings
    where portfolio_id = p_portfolio_id
      and symbol = v_symbol
      and asset_type = p_asset_type
      and market = upper(coalesce(trim(p_market), ''))
    for update;
    if not found or v_existing.quantity < p_quantity then
      raise exception 'Transaction exceeds the available holding';
    end if;
    if v_existing.quantity = p_quantity then
      delete from public.client_portfolio_holdings where id = v_existing.id;
    else
      update public.client_portfolio_holdings
      set quantity = quantity - p_quantity, updated_at = now()
      where id = v_existing.id;
    end if;
  end if;

  return v_transaction_id;
end;
$$;

revoke all on function public.record_client_portfolio_transaction(
  uuid,date,text,text,text,text,text,text,numeric,numeric,numeric,numeric,numeric,text,text,text
) from public, anon;
grant execute on function public.record_client_portfolio_transaction(
  uuid,date,text,text,text,text,text,text,numeric,numeric,numeric,numeric,numeric,text,text,text
) to authenticated;
