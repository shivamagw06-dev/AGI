alter table public.institutional_managers
  add column if not exists last_refresh_at timestamptz,
  add column if not exists last_successful_refresh_at timestamptz,
  add column if not exists last_refresh_status text,
  add column if not exists last_refresh_error text;

alter table public.institutional_managers
  drop constraint if exists institutional_managers_last_refresh_status_check;

alter table public.institutional_managers
  add constraint institutional_managers_last_refresh_status_check
  check (last_refresh_status is null or last_refresh_status in ('running', 'success', 'stale', 'error'));

-- Filings accepted from 3 January 2023 onward report fair value in dollars.
-- The first importer applied the historical x1000 convention to these rows.
update public.institutional_holdings
set value_usd = value_usd / 1000
where report_date >= date '2023-01-01';

update public.institutional_filings
set total_value_usd = total_value_usd / 1000
where report_date >= date '2023-01-01';

delete from public.institutional_signals where signal_type = 'consensus';

create or replace function public.propagate_security_ticker_mapping()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.ticker is not null and length(trim(new.ticker)) > 0 then
    update public.institutional_holdings set ticker = upper(trim(new.ticker)) where cusip = new.cusip;
    update public.holding_changes set ticker = upper(trim(new.ticker)) where cusip = new.cusip;
  end if;
  return new;
end;
$$;

drop trigger if exists security_identifier_ticker_propagation on public.security_identifier_history;
create trigger security_identifier_ticker_propagation
after insert or update of ticker on public.security_identifier_history
for each row execute function public.propagate_security_ticker_mapping();

grant execute on function public.propagate_security_ticker_mapping() to service_role;
