create table if not exists public.agi_india_portfolio_tracking (
 portfolio_id text primary key references public.agi_portfolio_catalog(id),
 baseline jsonb not null,
 created_at timestamptz not null default now()
);
alter table public.agi_india_portfolio_tracking enable row level security;
revoke all on public.agi_india_portfolio_tracking from anon, authenticated;
grant select, insert on public.agi_india_portfolio_tracking to service_role;
revoke update, delete on public.agi_india_portfolio_tracking from service_role;
create table if not exists public.agi_india_portfolio_marks (
 portfolio_id text not null references public.agi_india_portfolio_tracking(portfolio_id),
 session_date date not null,
 marked_at timestamptz not null,
 nav double precision not null check(nav>0),
 primary key(portfolio_id,session_date)
);
alter table public.agi_india_portfolio_marks enable row level security;
revoke all on public.agi_india_portfolio_marks from anon, authenticated;
grant select, insert, update on public.agi_india_portfolio_marks to service_role;
