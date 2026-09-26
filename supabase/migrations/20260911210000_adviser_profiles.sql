-- Who each tracked manager is, as they register themselves with the SEC.
--
-- A manager on the site is currently a name and a list of positions. Form ADV
-- is where an investment adviser states what it is - when it registered, under
-- what legal name, from where, whether it has disclosure events against it -
-- and it is public, filed by the adviser itself, and carries no licence.
--
-- Facts only, and deliberately so. The narrative brochures an adviser files are
-- its own writing and its own copyright; the registration facts here are not,
-- and the page can state them in its own words. Nothing in this table is
-- someone else's prose.
--
-- Keyed on the manager, not on the CRD, because the point is to enrich a
-- manager we already track. A manager with no profile row is the normal case
-- rather than an error: Berkshire Hathaway is an operating company that files
-- 13F, and a family office has been exempt from registering since 2011.
create table if not exists public.institutional_adviser_profiles (
  id uuid primary key default gen_random_uuid(),
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  -- The adviser's own identifiers. CRD is the registry key; the 801 number is
  -- what appears on the filing itself.
  crd text not null,
  sec_number text,
  legal_name text not null,
  -- ACTIVE, INACTIVE. An inactive registration is a fact about the manager
  -- worth showing, not a reason to omit the row.
  registration_scope text,
  registered_since date,
  latest_adv_filed date,
  -- The adviser answers this on the form. Y means there is something in the
  -- disclosure section; it is not a judgement and is shown as filed.
  has_disclosure boolean not null default false,
  branch_count integer,
  city text,
  country text,
  other_names jsonb not null default '[]'::jsonb,
  -- How the manager was matched to the adviser, so a wrong link can be found
  -- and undone rather than argued about.
  matched_by text not null,
  source_url text not null,
  source_as_of timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (manager_id)
);

create index if not exists institutional_adviser_profiles_crd_idx
  on public.institutional_adviser_profiles (crd);

alter table public.institutional_adviser_profiles enable row level security;

-- Readable by anyone, like the holdings it sits beside: these are public
-- registration facts. Written only by the importer, which runs as service_role.
drop policy if exists institutional_adviser_profiles_read on public.institutional_adviser_profiles;
create policy institutional_adviser_profiles_read
  on public.institutional_adviser_profiles for select
  using (true);
