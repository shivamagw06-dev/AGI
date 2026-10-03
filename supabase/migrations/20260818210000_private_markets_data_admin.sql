alter table public.private_market_ingestion_runs add column if not exists completed_at timestamptz;
alter table public.private_market_entity_review add column if not exists reviewed_at timestamptz;
alter table public.private_market_entity_review add column if not exists reviewed_by uuid references auth.users(id);
create index if not exists private_market_ingestion_history_idx on public.private_market_ingestion_runs(created_at desc);
comment on table public.private_market_ingestion_runs is 'Idempotent licensed-workbook import history used by Private Markets Data Admin.';
