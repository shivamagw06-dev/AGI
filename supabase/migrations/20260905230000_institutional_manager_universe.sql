alter table public.institutional_managers
  add column if not exists manager_type text,
  add column if not exists earliest_report_date date,
  add column if not exists city text,
  add column if not exists state text,
  add column if not exists country text,
  add column if not exists postal_code text,
  add column if not exists value_scale_override numeric;

-- Greenlight remains in historical tables but is no longer part of the selected live universe.
update public.institutional_managers
set active = false, updated_at = now()
where cik = '0001079114';

-- Baupost's current XML continues to express position values in thousands.
-- Restore already-imported modern filings once; future imports use the manager override.
update public.institutional_holdings h
set value_usd = h.value_usd * 1000
from public.institutional_filings f, public.institutional_managers m
where h.filing_id = f.id
  and f.manager_id = m.id
  and m.cik = '0001061768'
  and f.report_date >= date '2023-01-01'
  and f.total_value_usd < 100000000;

update public.institutional_filings f
set total_value_usd = f.total_value_usd * 1000
from public.institutional_managers m
where f.manager_id = m.id
  and m.cik = '0001061768'
  and f.report_date >= date '2023-01-01'
  and f.total_value_usd < 100000000;

update public.institutional_managers
set value_scale_override = 1000, updated_at = now()
where cik = '0001061768';

comment on column public.institutional_managers.earliest_report_date is 'Display-only start of known 13F coverage; filing history remains authoritative.';
comment on column public.institutional_managers.value_scale_override is 'Per-filer SEC value multiplier for legacy thousand-dollar reporters.';
