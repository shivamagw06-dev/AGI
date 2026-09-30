-- Additive workflow storage. Existing observations are baseline captures, not historic revisions.
create table public.gi_event_versions (
 id bigint generated always as identity primary key,
 event_id text not null references public.gi_events(id),
 captured_at timestamptz not null default now(), baseline boolean not null default false,
 facts jsonb not null
);
create index gi_event_versions_event_time on public.gi_event_versions(event_id,id desc);
insert into public.gi_event_versions(event_id,baseline,facts) select id,true,to_jsonb(e) from public.gi_events e;
create function public.gi_archive_event() returns trigger language plpgsql set search_path='' as $$
begin
 if tg_op='INSERT' or new.content_hash is distinct from old.content_hash then
  insert into public.gi_event_versions(event_id,facts) values(new.id,to_jsonb(new));
 end if;
 return new;
end; $$;
create trigger gi_archive_event after insert or update on public.gi_events for each row execute function public.gi_archive_event();
revoke all on function public.gi_archive_event() from public,anon,authenticated;

alter table public.gi_reviews add column impact_type text not null default 'unconfirmed' check(impact_type in ('unconfirmed','operational','supply_chain','demand','regulatory','none')),
 add column direction text not null default 'unknown' check(direction in ('unknown','positive','negative','mixed','neutral')),
 add column horizon text not null default 'unknown' check(horizon in ('unknown','days','weeks','months')),
 add column company_symbols text[] not null default '{}' check(cardinality(company_symbols)<=20);
create function public.gi_review_event_v2(p_event_id text,p_hash text,p_status text,p_assessment text,p_uncertainty text,p_next_check text,p_evidence_url text,p_actor uuid,p_context jsonb)
returns jsonb language plpgsql set search_path='' as $$
declare saved public.gi_reviews; symbols text[];
begin
 select coalesce(array_agg(distinct value),'{}') into symbols from jsonb_array_elements_text(coalesce(p_context->'company_symbols','[]'));
 if cardinality(symbols)>20 or exists(select 1 from unnest(symbols) s where not exists(select 1 from public.gi_assets a where a.symbol=s and a.active)) then raise exception 'Unknown company or too many companies'; end if;
 perform public.gi_review_event(p_event_id,p_hash,p_status,p_assessment,p_uncertainty,p_next_check,p_evidence_url,p_actor);
 update public.gi_reviews set impact_type=coalesce(p_context->>'impact_type','unconfirmed'),direction=coalesce(p_context->>'direction','unknown'),horizon=coalesce(p_context->>'horizon','unknown'),company_symbols=symbols where event_id=p_event_id returning * into saved;
 update public.gi_review_history set review=to_jsonb(saved) where id=(select max(id) from public.gi_review_history where event_id=p_event_id);
 return to_jsonb(saved);
end; $$;
revoke all on function public.gi_review_event_v2(text,text,text,text,text,text,text,uuid,jsonb) from public,anon,authenticated;
grant execute on function public.gi_review_event_v2(text,text,text,text,text,text,text,uuid,jsonb) to service_role;

create table public.gi_document_monitors (
 id text primary key, symbol text not null, title text not null, url text not null,
 status text not null default 'pending' check(status in ('pending','checking','ok','error')),
 last_attempt_at timestamptz,last_success_at timestamptz,last_error text,
 content_hash text, normalized_text text check(length(normalized_text)<=150000),
 last_changed_at timestamptz, revision_count integer not null default 0
);
create table public.gi_document_versions (
 id bigint generated always as identity primary key,
 monitor_id text not null references public.gi_document_monitors(id),
 captured_at timestamptz not null default now(),baseline boolean not null,
 content_hash text not null,added_lines integer not null,removed_lines integer not null,
 added_excerpt text,removed_excerpt text
);
create index gi_document_versions_monitor_time on public.gi_document_versions(monitor_id,id desc);
create table public.gi_document_lease(id boolean primary key default true check(id),expires_at timestamptz not null default now());
insert into public.gi_document_lease(id) values(true);
create function public.gi_acquire_document_lease() returns boolean language plpgsql set search_path='' as $$
begin update public.gi_document_lease set expires_at=now()+interval '10 minutes' where id=true and expires_at<now(); return found; end; $$;
revoke all on function public.gi_acquire_document_lease() from public,anon,authenticated;
grant execute on function public.gi_acquire_document_lease() to service_role;
create function public.gi_save_document(p_id text,p_hash text,p_text text,p_expected_hash text,p_added integer,p_removed integer,p_added_excerpt text,p_removed_excerpt text)
returns boolean language plpgsql set search_path='' as $$
declare previous_hash text;
begin
 select content_hash into previous_hash from public.gi_document_monitors where id=p_id for update;
 if not found then raise exception 'Unknown monitor'; end if;
 if previous_hash is distinct from p_expected_hash then raise exception 'Document changed concurrently' using errcode='40001'; end if;
 if previous_hash is distinct from p_hash then
  insert into public.gi_document_versions(monitor_id,baseline,content_hash,added_lines,removed_lines,added_excerpt,removed_excerpt)
  values(p_id,previous_hash is null,p_hash,p_added,p_removed,left(p_added_excerpt,1000),left(p_removed_excerpt,1000));
 end if;
 update public.gi_document_monitors set content_hash=p_hash,normalized_text=p_text,status='ok',last_success_at=now(),last_error=null,
 last_changed_at=case when previous_hash is not null and previous_hash is distinct from p_hash then now() else last_changed_at end,
 revision_count=revision_count+case when previous_hash is distinct from p_hash then 1 else 0 end where id=p_id;
 return previous_hash is distinct from p_hash;
end; $$;
revoke all on function public.gi_save_document(text,text,text,text,integer,integer,text,text) from public,anon,authenticated;
grant execute on function public.gi_save_document(text,text,text,text,integer,integer,text,text) to service_role;

create table public.gi_alert_preferences (
 user_id uuid primary key references auth.users(id) on delete cascade,
 enabled boolean not null default false,observations boolean not null default false,
 assessments boolean not null default true,documents boolean not null default true,
 enabled_at timestamptz,last_read_at timestamptz,updated_at timestamptz not null default now()
);
create function public.gi_set_alert_preferences(p_user uuid,p_enabled boolean,p_observations boolean,p_assessments boolean,p_documents boolean)
returns jsonb language plpgsql set search_path='' as $$
declare saved public.gi_alert_preferences;
begin
 insert into public.gi_alert_preferences(user_id,enabled,observations,assessments,documents,enabled_at)
 values(p_user,p_enabled,p_observations,p_assessments,p_documents,case when p_enabled then now() end)
 on conflict(user_id) do update set enabled=excluded.enabled,observations=excluded.observations,assessments=excluded.assessments,documents=excluded.documents,
 enabled_at=case when excluded.enabled and not gi_alert_preferences.enabled then now() else gi_alert_preferences.enabled_at end,updated_at=now()
 returning * into saved;
 return to_jsonb(saved)-'user_id';
end; $$;
revoke all on function public.gi_set_alert_preferences(uuid,boolean,boolean,boolean,boolean) from public,anon,authenticated;
grant execute on function public.gi_set_alert_preferences(uuid,boolean,boolean,boolean,boolean) to service_role;

alter table public.gi_event_versions enable row level security;
alter table public.gi_document_monitors enable row level security;
alter table public.gi_document_versions enable row level security;
alter table public.gi_document_lease enable row level security;
alter table public.gi_alert_preferences enable row level security;
revoke all on public.gi_event_versions,public.gi_document_monitors,public.gi_document_versions,public.gi_document_lease,public.gi_alert_preferences from anon,authenticated;
grant all on public.gi_event_versions,public.gi_document_monitors,public.gi_document_versions,public.gi_document_lease,public.gi_alert_preferences to service_role;
grant usage,select on sequence public.gi_event_versions_id_seq,public.gi_document_versions_id_seq to service_role;

insert into public.gi_document_monitors(id,symbol,title,url) values
('reliance-locations','RELIANCE','Reliance manufacturing locations','https://www.ril.com/about/manufacturing-locations'),
('tata-manufactured-capital','TATASTEEL','Tata Steel FY2024–25 manufactured capital','https://www.tatasteel.com/investors/integrated-report-2024-25/manufactured-capital.html'),
('adani-mundra','ADANIPORTS','Adani Ports Mundra profile','https://www.adaniports.com/Ports-and-Terminals/Mundra-Port'),
('ntpc-coal','NTPC','NTPC coal stations','https://ntpc.co.in/power-generation/coal-stations'),
('ioc-locations','IOC','Indian Oil locations','https://www.iocl.com/our-locations'),
('hindalco-locations','HINDALCO','Hindalco plant locations','https://www.hindalco.com/investors/shareholder-centre/listing-details/plant-locations'),
('jsw-vijayanagar','JSWSTEEL','JSW Steel Vijayanagar Works','https://www.jswsteel.in/facility/vijayanagar-works')
on conflict(id) do nothing;
