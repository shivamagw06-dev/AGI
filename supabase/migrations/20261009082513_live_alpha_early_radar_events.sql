-- Research-only observations. Browser clients never receive direct write access.
create table if not exists public.live_alpha_radar_events (
  event_key text primary key,
  version text not null,
  symbol text not null,
  session_date date not null,
  event_at timestamptz not null,
  stage text not null check (stage in ('watch','triggered','confirmed','failed','expired','extended')),
  observation jsonb not null,
  recorded_at timestamptz not null default now()
);
create index if not exists live_alpha_radar_events_session_time on public.live_alpha_radar_events(session_date, event_at desc);
create table if not exists public.live_alpha_radar_state (
  state_key text primary key,
  version text not null,
  symbol text not null,
  session_date date not null,
  event_at timestamptz not null,
  observation jsonb not null
);
alter table public.live_alpha_radar_events enable row level security;
alter table public.live_alpha_radar_state enable row level security;
revoke all on public.live_alpha_radar_events, public.live_alpha_radar_state from public, anon, authenticated;
grant select, insert on public.live_alpha_radar_events to service_role;
grant select, insert, update on public.live_alpha_radar_state to service_role;
