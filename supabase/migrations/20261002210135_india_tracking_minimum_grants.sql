revoke all on public.agi_india_portfolio_tracking, public.agi_india_portfolio_marks from service_role;
grant select, insert on public.agi_india_portfolio_tracking to service_role;
grant select, insert, update on public.agi_india_portfolio_marks to service_role;
