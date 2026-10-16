-- Server-owned end-of-day evidence, one dated batch with individually verified prices.
create table public.agi_india_daily_prices (
 session_date date primary key,
 prices jsonb not null default '{}'::jsonb check (jsonb_typeof(prices) = 'object'),
 collected_at timestamptz not null default now()
);
alter table public.agi_india_daily_prices enable row level security;
revoke all on public.agi_india_daily_prices from public, anon, authenticated, service_role;
grant select, insert, update on public.agi_india_daily_prices to service_role;
alter table public.agi_india_portfolio_marks add column valuation_method text not null default 'legacy_intraday';
