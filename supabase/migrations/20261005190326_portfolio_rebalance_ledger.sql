create table if not exists public.agi_portfolio_ledger (
 portfolio_id text primary key references public.agi_portfolio_catalog(id),
 revision integer not null default 1 check (revision > 0),
 document jsonb not null,
 updated_at timestamptz not null default now()
);
alter table public.agi_portfolio_ledger enable row level security;
revoke all on public.agi_portfolio_ledger from public, anon, authenticated;
grant select, insert, update on public.agi_portfolio_ledger to service_role;
-- Historical marks and execution events are append-only, even for service writes.
create or replace function public.agi_preserve_portfolio_ledger() returns trigger
language plpgsql set search_path = public as $$
begin
 if new.revision <> old.revision + 1 then raise exception 'Ledger revision conflict'; end if;
 if jsonb_array_length(new.document->'history') < jsonb_array_length(old.document->'history')
 or exists(select 1 from jsonb_array_elements(old.document->'history') with ordinality x(v,n) where new.document->'history'->(n::int-1) is distinct from v)
 or jsonb_array_length(new.document->'events') < jsonb_array_length(old.document->'events')
 or exists(select 1 from jsonb_array_elements(old.document->'events') with ordinality x(v,n) where new.document->'events'->(n::int-1) is distinct from v)
 then raise exception 'Published ledger history is immutable'; end if;
 return new;
end $$;
revoke all on function public.agi_preserve_portfolio_ledger() from public,anon,authenticated;
create trigger agi_preserve_portfolio_ledger before update on public.agi_portfolio_ledger for each row execute function public.agi_preserve_portfolio_ledger();
