-- A manager can report through another filer, which is not the same as being
-- late.
--
-- Form 13F comes in two shapes. 13F-HR carries the information table; 13F-NT
-- is a notice, filed when the manager holds no section 13(f) securities of its
-- own because everything it would report is reported by a different filer.
--
-- The collector correctly ignores notices - there is no table in one - but it
-- had no way to say so. Vanguard filed 13F-NT for 2026-03-31 and 2026-06-30,
-- so its newest holdings report is 2025-12-31, and the fund page presented a
-- December book as current while the manager read as 'stale'. Stale means
-- late, and invites waiting for an update that will never arrive in that form.
--
-- 'reports_elsewhere' says the true thing, and it is a different instruction
-- to the reader: go and find the other filer.
alter table public.institutional_managers
  drop constraint if exists institutional_managers_last_refresh_status_check;

alter table public.institutional_managers
  add constraint institutional_managers_last_refresh_status_check
  check (
    last_refresh_status is null
    or last_refresh_status in ('running', 'success', 'stale', 'error', 'reports_elsewhere')
  );
