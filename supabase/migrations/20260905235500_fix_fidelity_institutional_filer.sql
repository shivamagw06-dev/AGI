update public.institutional_managers
set
  legal_name = 'FMR LLC',
  cik = '0000315066',
  last_refresh_status = null,
  last_refresh_error = null,
  updated_at = now()
where slug = 'fidelity-investments-money-management';
