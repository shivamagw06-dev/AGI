-- AGI Macro Intelligence data repository
-- Third-party APIs are reference sources only. Frontend never calls them.
-- Backend stores successful responses for reuse, history, and graceful degradation.

create table if not exists public.macro_dataset_cache (
  dataset_key text primary key,
  payload jsonb not null default '{}'::jsonb,
  source text not null,
  fetched_at timestamptz not null default now(),
  expires_at timestamptz not null,
  refresh_policy text not null default 'scheduled',
  meta jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists macro_dataset_cache_expires_at_idx
  on public.macro_dataset_cache (expires_at);

create table if not exists public.macro_observation_history (
  id uuid primary key default gen_random_uuid(),
  dataset_key text not null,
  observed_at timestamptz not null default now(),
  label text,
  value_numeric numeric,
  value_text text,
  direction text,
  unit text,
  payload jsonb not null default '{}'::jsonb,
  source text not null,
  created_at timestamptz not null default now()
);

create index if not exists macro_observation_history_dataset_observed_idx
  on public.macro_observation_history (dataset_key, observed_at desc);

create table if not exists public.macro_briefing_cache (
  id text primary key default 'current',
  briefing jsonb not null,
  sources_used jsonb not null default '[]'::jsonb,
  generated_at timestamptz not null default now(),
  expires_at timestamptz not null,
  ai_generated boolean not null default false,
  stale boolean not null default false,
  updated_at timestamptz not null default now()
);

alter table public.macro_dataset_cache enable row level security;
alter table public.macro_observation_history enable row level security;
alter table public.macro_briefing_cache enable row level security;

-- Public read of derived cache is optional; service role bypasses RLS for writes.
-- No anon write policies. Backend uses service role.

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'macro_dataset_cache' and policyname = 'macro_dataset_cache_public_read'
  ) then
    create policy macro_dataset_cache_public_read
      on public.macro_dataset_cache
      for select
      to anon, authenticated
      using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'macro_observation_history' and policyname = 'macro_observation_history_public_read'
  ) then
    create policy macro_observation_history_public_read
      on public.macro_observation_history
      for select
      to anon, authenticated
      using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'macro_briefing_cache' and policyname = 'macro_briefing_cache_public_read'
  ) then
    create policy macro_briefing_cache_public_read
      on public.macro_briefing_cache
      for select
      to anon, authenticated
      using (true);
  end if;
end $$;
