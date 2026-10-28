create table public.agi_usa_history_snapshot (
 id text primary key check (id = 'daily'),
 document jsonb not null,
 updated_at timestamptz not null default now(),
 check (document->>'schemaVersion' = '1' and document->>'asOf' ~ '^\d{4}-\d{2}-\d{2}$')
);
alter table public.agi_usa_history_snapshot enable row level security;
revoke all on public.agi_usa_history_snapshot from public, anon, authenticated;
grant select, insert, update on public.agi_usa_history_snapshot to service_role;
create function public.agi_usa_history_no_regression() returns trigger language plpgsql set search_path=public as $$
begin
 if new.document->>'asOf' < old.document->>'asOf' then raise exception 'USA history cannot move backwards'; end if;
 return new;
end $$;
revoke all on function public.agi_usa_history_no_regression() from public,anon,authenticated;
create trigger agi_usa_history_no_regression before update on public.agi_usa_history_snapshot for each row execute function public.agi_usa_history_no_regression();
