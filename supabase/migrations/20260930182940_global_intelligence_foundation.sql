-- Private storage: all access goes through authenticated server endpoints.
create table public.gi_sources (
 id text primary key, name text not null, status text not null default 'not_connected',
 last_attempt_at timestamptz, last_success_at timestamptz, last_count integer, last_error text
);
create table public.gi_events (
 id text primary key, provider text not null references public.gi_sources(id), external_id text not null,
 title text not null, category text not null, latitude double precision not null check(latitude between -90 and 90),
 longitude double precision not null check(longitude between -180 and 180), observed_at timestamptz not null,
 published_at timestamptz, source_updated_at timestamptz, source_url text not null, source_status text not null,
 magnitude double precision, content_hash text not null, first_seen_at timestamptz not null default now(), last_seen_at timestamptz not null default now(),
 unique(provider, external_id)
);
create index gi_events_observed on public.gi_events(observed_at desc);
create table public.gi_assets (
 id uuid primary key default gen_random_uuid(), symbol text not null, company text not null, name text not null,
 sector text not null, relationship text not null, evidence_note text not null, source_url text not null,
 confidence text not null check(confidence in ('confirmed','estimated')),
 latitude double precision not null check(latitude between -90 and 90), longitude double precision not null check(longitude between -180 and 180),
 location_precision text not null, verified_at timestamptz not null default now(), verified_by uuid,
 active boolean not null default true, unique(symbol,name)
);
create table public.gi_reviews (
 event_id text primary key references public.gi_events(id), status text not null check(status in ('published','rejected')),
 assessment text not null, uncertainty text, next_check text, evidence_url text, content_hash text not null,
 reviewed_at timestamptz not null default now(), reviewer uuid not null
);
create table public.gi_review_history (
 id bigint generated always as identity primary key, event_id text not null references public.gi_events(id),
 review jsonb not null, actor uuid not null, created_at timestamptz not null default now()
);
create table public.gi_watchlists (
 user_id uuid primary key references auth.users(id) on delete cascade,
 symbols text[] not null default '{}' check(cardinality(symbols)<=100), updated_at timestamptz not null default now()
);
create table public.gi_collection_lease (id boolean primary key default true check(id), expires_at timestamptz not null);
insert into public.gi_collection_lease values(true, '-infinity');
insert into public.gi_sources(id,name) values ('usgs','USGS earthquakes'),('eonet','NASA EONET');

alter table public.gi_sources enable row level security;
alter table public.gi_events enable row level security;
alter table public.gi_assets enable row level security;
alter table public.gi_reviews enable row level security;
alter table public.gi_review_history enable row level security;
alter table public.gi_watchlists enable row level security;
alter table public.gi_collection_lease enable row level security;
revoke all on public.gi_sources,public.gi_events,public.gi_assets,public.gi_reviews,public.gi_review_history,public.gi_watchlists,public.gi_collection_lease from anon,authenticated;
grant all on public.gi_sources,public.gi_events,public.gi_assets,public.gi_reviews,public.gi_review_history,public.gi_watchlists,public.gi_collection_lease to service_role;
grant usage,select on sequence public.gi_review_history_id_seq to service_role;

create function public.gi_preserve_first_seen() returns trigger language plpgsql set search_path='' as $$
begin new.first_seen_at := old.first_seen_at; return new; end; $$;
create trigger gi_preserve_first_seen before update on public.gi_events for each row execute function public.gi_preserve_first_seen();
revoke all on function public.gi_preserve_first_seen() from public,anon,authenticated;

create function public.gi_acquire_collection_lease() returns boolean language plpgsql set search_path='' as $$
begin
 update public.gi_collection_lease set expires_at=now()+interval '3 minutes' where id=true and expires_at<now();
 return found;
end; $$;
revoke all on function public.gi_acquire_collection_lease() from public,anon,authenticated;
grant execute on function public.gi_acquire_collection_lease() to service_role;

create function public.gi_review_event(p_event_id text,p_hash text,p_status text,p_assessment text,p_uncertainty text,p_next_check text,p_evidence_url text,p_actor uuid)
returns jsonb language plpgsql set search_path='' as $$
declare actual_hash text; saved public.gi_reviews;
begin
 select content_hash into actual_hash from public.gi_events where id=p_event_id for update;
 if actual_hash is null then raise exception 'Event not found' using errcode='P0002'; end if;
 if actual_hash<>p_hash then raise exception 'Source changed. Reload and review the updated event.' using errcode='40001'; end if;
 if p_actor is null or p_status not in ('published','rejected') or length(trim(p_assessment))=0 or length(p_assessment)>3000 then raise exception 'Invalid review'; end if;
 if p_status='published' and (coalesce(length(trim(p_uncertainty)),0)=0 or coalesce(length(trim(p_next_check)),0)=0 or coalesce(p_evidence_url,'') not like 'https://%') then raise exception 'Published reviews need uncertainty, next check and evidence'; end if;
 insert into public.gi_reviews(event_id,status,assessment,uncertainty,next_check,evidence_url,content_hash,reviewer)
 values(p_event_id,p_status,p_assessment,p_uncertainty,p_next_check,p_evidence_url,p_hash,p_actor)
 on conflict(event_id) do update set status=excluded.status,assessment=excluded.assessment,uncertainty=excluded.uncertainty,next_check=excluded.next_check,evidence_url=excluded.evidence_url,content_hash=excluded.content_hash,reviewer=excluded.reviewer,reviewed_at=now()
 returning * into saved;
 insert into public.gi_review_history(event_id,review,actor) values(p_event_id,to_jsonb(saved),p_actor);
 return to_jsonb(saved);
end; $$;
revoke all on function public.gi_review_event(text,text,text,text,text,text,text,uuid) from public,anon,authenticated;
grant execute on function public.gi_review_event(text,text,text,text,text,text,text,uuid) to service_role;

-- Company documents establish the relationship; markers are approximate geographic areas.
insert into public.gi_assets(symbol,company,name,sector,relationship,evidence_note,source_url,confidence,latitude,longitude,location_precision) values
('RELIANCE','Reliance Industries','Jamnagar manufacturing area','Oil & gas','Company-listed manufacturing location','Reliance lists its Jamnagar manufacturing division. Marker approximates the area; it does not establish current operations or hazard exposure.','https://www.ril.com/about/manufacturing-locations','confirmed',22.35,69.86,'Approximate area marker; not a facility boundary'),
('RELIANCE','Reliance Industries','Hazira manufacturing area','Oil & gas','Company-listed manufacturing location','Reliance lists Hazira in its manufacturing locations. Marker approximates the area.','https://www.ril.com/about/manufacturing-locations','confirmed',21.11,72.65,'Approximate area marker; not a facility boundary'),
('RELIANCE','Reliance Industries','Dahej manufacturing area','Oil & gas','Company-listed manufacturing location','Reliance lists Dahej in its manufacturing locations. Marker approximates the area.','https://www.ril.com/about/manufacturing-locations','confirmed',21.70,72.58,'Approximate area marker; not a facility boundary'),
('TATASTEEL','Tata Steel','Jamshedpur steelworks area','Steel','Facility listed in group annual report','FY2024–25 manufactured-capital report lists this facility. Current operating status requires fresh confirmation.','https://www.tatasteel.com/investors/integrated-report-2024-25/manufactured-capital.html','confirmed',22.80,86.20,'Approximate city/area marker; not a facility boundary'),
('TATASTEEL','Tata Steel','Kalinganagar steelworks area','Steel','Facility listed in group annual report','FY2024–25 manufactured-capital report lists this facility. Current operating status requires fresh confirmation.','https://www.tatasteel.com/investors/integrated-report-2024-25/manufactured-capital.html','confirmed',20.99,86.03,'Approximate area marker; not a facility boundary'),
('TATASTEEL','Tata Steel','Meramandali steelworks area','Steel','Facility listed in group annual report','FY2024–25 manufactured-capital report lists this facility. Current operating status requires fresh confirmation.','https://www.tatasteel.com/investors/integrated-report-2024-25/manufactured-capital.html','confirmed',20.82,85.24,'Approximate area marker; not a facility boundary'),
('TATASTEEL','Tata Steel','IJmuiden steelworks area','Steel','Group facility through Tata Steel Nederland','FY2024–25 manufactured-capital report lists the Netherlands facility. Current operating status requires fresh confirmation.','https://www.tatasteel.com/investors/integrated-report-2024-25/manufactured-capital.html','confirmed',52.46,4.60,'Approximate city/area marker; not a facility boundary'),
('ADANIPORTS','Adani Ports and SEZ','Mundra port area','Ports & logistics','Company-listed port','Adani Ports describes Mundra as its flagship port in Gujarat. Marker is approximate.','https://www.adaniports.com/Ports-and-Terminals/Mundra-Port','confirmed',22.74,69.70,'Approximate port-area marker; not a facility boundary'),
('NTPC','NTPC','Vindhyachal power station area','Power','Station listed as NTPC owned','NTPC coal-stations page lists Vindhyachal in Madhya Pradesh as an owned station. Marker is approximate.','https://ntpc.co.in/power-generation/coal-stations','confirmed',24.10,82.67,'Approximate area marker; not a facility boundary');
