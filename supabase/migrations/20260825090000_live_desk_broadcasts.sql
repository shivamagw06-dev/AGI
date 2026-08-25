-- Admin-managed publisher links for Live Desk.
-- No anonymous or authenticated policies: public reads and admin writes both
-- pass through the Node API, whose service-role client bypasses RLS.

create table if not exists public.live_desk_broadcasts (
  id text primary key check (id in ('global', 'india')),
  video_id text not null check (video_id ~ '^[A-Za-z0-9_-]{11}$'),
  youtube_url text not null,
  updated_by uuid,
  updated_at timestamptz not null default now()
);

alter table public.live_desk_broadcasts enable row level security;

insert into public.live_desk_broadcasts (id, video_id, youtube_url)
values
  ('global', 'QB5BNdBFujE', 'https://www.youtube.com/watch?v=QB5BNdBFujE'),
  ('india', 'EN-N1xhtBqU', 'https://www.youtube.com/watch?v=EN-N1xhtBqU')
on conflict (id) do nothing;
