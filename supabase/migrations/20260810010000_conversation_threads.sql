-- Privacy-minimal Ask AGI conversation checkpoints. Raw research evidence is never stored here.
create table if not exists public.conversation_threads (
  thread_id text primary key check (char_length(thread_id) between 1 and 80),
  state jsonb not null default '{}'::jsonb check (jsonb_typeof(state) = 'object'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '30 days'),
  check (octet_length(state::text) <= 16384)
);

create index if not exists conversation_threads_expiry_idx
  on public.conversation_threads (expires_at);

alter table public.conversation_threads enable row level security;

comment on table public.conversation_threads is
  'Compact server-only Ask AGI dialogue state; excludes raw evidence, prompts, credentials and full documents.';

