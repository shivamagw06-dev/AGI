-- A manager's filings can live under more than one CIK.
--
-- BlackRock is the case that forced this. Its 13F reporting has moved between
-- entities twice, and the roster can only point at one CIK, so it holds 11
-- quarters while its peers hold 42:
--
--   BLACKROCK ADVISORS LLC   0001086364  13F-HR 2006-03-30 .. 2016-12-31
--   BlackRock Finance, Inc.  0001364742  13F-HR 2006-03-30 .. 2024-06-30  (72 periods)
--   BlackRock, Inc.          0002012383  13F-HR 2024-09-30 .. present
--
-- Repointing the roster at the current entity in #1007 was right - the old one
-- had gone silent and the manager showed a two-year-old book - but it made the
-- history unreachable. This keeps both, with an explicit window for each.
--
-- Windows are declared, not inferred. A "prefer the newest CIK" rule would be
-- wrong in exactly the cases that matter: entities overlap while a transition
-- completes, and picking by recency silently drops the filing that has the
-- holdings in it. A human decides the boundary and it is auditable afterwards.

create table if not exists public.institutional_manager_ciks (
  id uuid primary key default gen_random_uuid(),
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  cik text not null,
  -- The entity's own name at EDGAR, kept so a boundary can be checked against
  -- the filer rather than against this table's own opinion of it.
  label text,
  role text not null default 'predecessor' check (role in ('primary', 'predecessor')),

  -- Inclusive bounds on report_date. Null means open: no effective_from is
  -- "from the beginning of this filer's record", no effective_to is "still
  -- current". Null is a real bound here, never an absent one.
  effective_from date,
  effective_to date,

  notes text,
  created_at timestamptz not null default now(),
  unique (manager_id, cik)
);

create index if not exists institutional_manager_ciks_manager_idx
  on public.institutional_manager_ciks (manager_id);

alter table public.institutional_manager_ciks enable row level security;

comment on table public.institutional_manager_ciks is
  'Additional CIKs a manager has filed 13F under. Windows are inclusive on report_date; null bounds are open-ended.';

-- BlackRock's predecessor. Its window closes at the last period it filed a
-- holdings report for; BlackRock, Inc. picks up at 2024-09-30 with no overlap,
-- so no filing can be claimed by both.
insert into public.institutional_manager_ciks (manager_id, cik, label, role, effective_to, notes)
select id, '0001364742', 'BlackRock Finance, Inc.', 'predecessor', '2024-06-30',
       'Filed 72 13F-HR periods from 2006-03-30 to 2024-06-30. The roster moved to BlackRock, Inc. (0002012383) in #1007 because this entity went silent; the history stayed here.'
  from public.institutional_managers
 where slug = 'blackrock'
on conflict (manager_id, cik) do nothing;
