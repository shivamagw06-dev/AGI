-- Extend the public macro warehouse with explicit point-in-time and revision controls.
-- Existing observations remain PIT limited until an official release timestamp is known.

alter table public.macro_public_series_registry
  add column if not exists source_tier text not null default 'C',
  add column if not exists minimum_history_periods integer not null default 24,
  add column if not exists calculation_eligible boolean not null default false;

alter table public.macro_public_observations
  add column if not exists effective_date timestamptz,
  add column if not exists first_seen_at timestamptz,
  add column if not exists retrieved_at timestamptz,
  add column if not exists is_initial_release boolean not null default true,
  add column if not exists is_revised boolean not null default false,
  add column if not exists previous_value numeric,
  add column if not exists revision_amount numeric,
  add column if not exists pit_status text not null default 'PIT_LIMITED';

update public.macro_public_observations
set effective_date = coalesce(effective_date, release_date),
    first_seen_at = coalesce(first_seen_at, available_at, ingested_at),
    retrieved_at = coalesce(retrieved_at, ingested_at),
    pit_status = case
      when release_date is not null and release_date < available_at then 'RELEASE_TIMESTAMP_RECORDED'
      else 'FETCH_VINTAGE_ONLY'
    end
where effective_date is null
   or first_seen_at is null
   or retrieved_at is null
   or pit_status = 'PIT_LIMITED';

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'macro_public_registry_source_tier_check'
  ) then
    alter table public.macro_public_series_registry
      add constraint macro_public_registry_source_tier_check
      check (source_tier in ('A', 'B', 'C', 'D'));
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'macro_public_observations_pit_status_check'
  ) then
    alter table public.macro_public_observations
      add constraint macro_public_observations_pit_status_check
      check (pit_status in ('OFFICIAL_VINTAGE', 'RELEASE_TIMESTAMP_RECORDED', 'FETCH_VINTAGE_ONLY', 'PIT_LIMITED'));
  end if;
end $$;

create index if not exists macro_public_observations_revision_idx
  on public.macro_public_observations (series_id, country_code, period_date, revision_number desc);

create index if not exists macro_public_registry_calculation_gate_idx
  on public.macro_public_series_registry (calculation_eligible, source_tier, frequency);
