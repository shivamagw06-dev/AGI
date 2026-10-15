-- Service-role-only durable scheduler. No browser session or token is stored here.
create table public.agi_research_refresh_state (
 id boolean primary key default true check(id), enabled boolean not null default false,
 next_due_at timestamptz not null default now(), lease_until timestamptz,
 lease_token uuid, last_report jsonb, updated_at timestamptz not null default now()
);
insert into public.agi_research_refresh_state(id) values(true);
create table public.agi_research_refresh_runs (
 id uuid primary key, started_at timestamptz not null default now(), finished_at timestamptz,
 status text not null default 'running', report jsonb not null default '{}'::jsonb
);
alter table public.agi_research_refresh_state enable row level security;
alter table public.agi_research_refresh_runs enable row level security;
revoke all on public.agi_research_refresh_state,public.agi_research_refresh_runs from anon,authenticated;
grant all on public.agi_research_refresh_state,public.agi_research_refresh_runs to service_role;
create function public.claim_research_refresh(p_token uuid, p_force boolean default false)
returns boolean language plpgsql security invoker set search_path = public as $$
begin
 update agi_research_refresh_state set lease_token=p_token,lease_until=now()+interval '1 hour',updated_at=now()
 where id and (lease_until is null or lease_until<now()) and (p_force or (enabled and next_due_at<=now()));
 if not found then return false; end if;
 update agi_research_refresh_runs set status='interrupted',finished_at=now()
 where status='running';
 insert into agi_research_refresh_runs(id) values(p_token);
 return true;
end $$;
create function public.finish_research_refresh(p_token uuid,p_status text,p_report jsonb)
returns boolean language plpgsql security invoker set search_path = public as $$
begin
 update agi_research_refresh_state set lease_token=null,lease_until=null,last_report=p_report,
 next_due_at=(((now() at time zone 'Asia/Kolkata')::date + case when p_status='complete' then 15 else 1 end) + time '17:00') at time zone 'Asia/Kolkata',updated_at=now()
 where id and lease_token=p_token;
 if not found then return false; end if;
 update agi_research_refresh_runs set status=p_status,report=p_report,finished_at=now() where id=p_token;
 return true;
end $$;
revoke all on function public.claim_research_refresh(uuid,boolean),public.finish_research_refresh(uuid,text,jsonb) from public,anon,authenticated;
grant execute on function public.claim_research_refresh(uuid,boolean),public.finish_research_refresh(uuid,text,jsonb) to service_role;
