-- A canonical identity for a security, and mappings that know when they applied.
--
-- Identity was the CUSIP. A CUSIP is not permanently stable: it is reassigned
-- after corporate actions, a company can carry several across share classes and
-- depositary lines, and the same issuer appears under different ones over time.
-- Keying identity to it means the same company is several securities, and a
-- reassigned CUSIP silently becomes a different company's holding.
--
-- security_key is that canonical identity. It starts as the CUSIP - every
-- security is its own key until something is known to merge - and moves to a
-- stable issuer-level value as mappings are resolved. Holdings keep their
-- CUSIP, which is what the filing said; the key is what the product aggregates
-- and prices on.
--
-- The point-in-time half already existed as valid_from / valid_to and was not
-- being used: resolution took the newest mapping for a CUSIP whatever the date
-- of the filing being resolved, so a 2025 reassignment relabelled a 2023
-- holding. The index below is what makes asking the right question cheap.

alter table public.security_identifier_history
  add column if not exists security_key text;

-- Bootstrap: a security is its own key until a mapping says otherwise. Done in
-- one statement rather than a backfill script because the table is small and
-- the value is derivable.
update public.security_identifier_history
   set security_key = upper(trim(cusip))
 where security_key is null;

alter table public.security_identifier_history
  alter column security_key set default null;

-- The resolution query: given a CUSIP and a date, find the mapping that was in
-- force then. Without this it is a sequential scan per filing ingested.
create index if not exists security_identifier_asof_idx
  on public.security_identifier_history (cusip, valid_from desc);

create index if not exists security_identifier_key_idx
  on public.security_identifier_history (security_key)
  where security_key is not null;

-- A mapping cannot stop applying before it started.
alter table public.security_identifier_history
  drop constraint if exists security_identifier_validity_ordered;
alter table public.security_identifier_history
  add constraint security_identifier_validity_ordered
  check (valid_to is null or valid_to > valid_from) not valid;

comment on column public.security_identifier_history.security_key is
  'Canonical identity for the security, stable across CUSIP reassignment. Defaults to the CUSIP; several CUSIPs may share one key once merged.';
comment on column public.security_identifier_history.valid_from is
  'First date this mapping applied. Resolution must ask what was in force on the filing date, not what is in force now.';
comment on column public.security_identifier_history.valid_to is
  'Exclusive end of the interval, or null while current.';
