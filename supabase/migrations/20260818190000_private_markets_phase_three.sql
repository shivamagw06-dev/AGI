create table if not exists public.private_market_change_events(
 id uuid primary key default gen_random_uuid(),
 entity_type text not null check(entity_type in('deal','company','investor','opportunity')),
 entity_id uuid not null,
 change_type text not null,
 previous_values jsonb not null default '{}',
 current_values jsonb not null default '{}',
 source_id uuid references public.private_market_sources(id),
 detected_at timestamptz not null default now(),
 acknowledged_at timestamptz
);
create index if not exists private_market_change_events_entity_idx on public.private_market_change_events(entity_type,entity_id,detected_at desc);
alter table public.private_market_change_events enable row level security;
comment on table public.private_market_change_events is 'Canonical Private Markets change log; no outside collection worker is required.';
