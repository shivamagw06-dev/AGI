-- AGI four-letter newsletter preferences on subscribers
-- Keys: agi_markets, agi_morning_brief, agi_evening_brief, agi_macro

alter table if exists public.subscribers
  add column if not exists preferences jsonb;

alter table if exists public.subscribers
  add column if not exists source text;

alter table if exists public.subscribers
  add column if not exists updated_at timestamptz default now();

update public.subscribers
set preferences = jsonb_build_object(
  'agi_markets', true,
  'agi_morning_brief', true,
  'agi_evening_brief', true,
  'agi_macro', true
)
where preferences is null;

alter table if exists public.subscribers
  alter column preferences set default jsonb_build_object(
    'agi_markets', true,
    'agi_morning_brief', false,
    'agi_evening_brief', false,
    'agi_macro', false
  );

comment on column public.subscribers.preferences is
  'AGI letter opt-ins: agi_markets, agi_morning_brief, agi_evening_brief, agi_macro';
