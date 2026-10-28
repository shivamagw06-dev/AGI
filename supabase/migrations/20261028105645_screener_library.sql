-- Only the backend service role may read or write these tables. Membership and
-- admin permissions are checked by the API using a verified Supabase identity.
create table public.screener_library (
 slug text primary key check(slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and length(slug) between 3 and 80),
 display_name text not null check(length(display_name) between 3 and 120),
 category text not null, description text not null default '' check(length(description)<=1000),
 rule_notes text not null default '' check(length(rule_notes)<=3000), default_source_url text,
 archived boolean not null default false, created_by uuid references auth.users(id) on delete set null,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table public.screener_library_snapshots (
 id bigint generated always as identity primary key,
 screener_slug text not null references public.screener_library(slug),
 as_of date not null, created_at timestamptz not null default now(),
 columns jsonb not null check(jsonb_typeof(columns)='array' and jsonb_array_length(columns) between 2 and 120),
 rows jsonb not null check(jsonb_typeof(rows)='array'),
 identity_column integer not null check(identity_column>=0 and identity_column<jsonb_array_length(columns)),
 row_count integer not null check(row_count between 1 and 5000 and row_count=jsonb_array_length(rows)),
 source_url text, content_hash text not null check(content_hash ~ '^[a-f0-9]{64}$'),
 definition jsonb not null, published_by uuid not null,
 unique(screener_slug,as_of,content_hash)
);
create index screener_library_latest on public.screener_library_snapshots(screener_slug,id desc);
alter table public.screener_library enable row level security;
alter table public.screener_library_snapshots enable row level security;
revoke all on public.screener_library,public.screener_library_snapshots from public,anon,authenticated;
grant select,insert,update on public.screener_library to service_role;
grant select,insert on public.screener_library_snapshots to service_role;
revoke all on sequence public.screener_library_snapshots_id_seq from public,anon,authenticated;
grant usage,select on sequence public.screener_library_snapshots_id_seq to service_role;
create view public.screener_library_catalogue with(security_invoker=true) as
 select s.slug,s.display_name,s.category,s.description,s.rule_notes,s.default_source_url,s.archived,
 latest.id as snapshot_id,latest.as_of,latest.row_count,latest.created_at as published_at
 from public.screener_library s left join lateral (
   select id,as_of,row_count,created_at from public.screener_library_snapshots
   where screener_slug=s.slug order by id desc limit 1
 ) latest on true;
revoke all on public.screener_library_catalogue from public,anon,authenticated;
grant select on public.screener_library_catalogue to service_role;
create function public.publish_screener_library_snapshot(p_slug text,p_as_of date,p_columns jsonb,p_rows jsonb,p_identity_column integer,p_source_url text,p_hash text,p_actor uuid)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare s public.screener_library%rowtype; saved public.screener_library_snapshots%rowtype; latest_date date; count_rows integer;
begin
 select * into s from public.screener_library where slug=p_slug and not archived for update;
 if not found then raise exception 'Screener not found.'; end if;
 if p_actor is null or p_as_of is null or jsonb_typeof(p_rows) is distinct from 'array' or jsonb_typeof(p_columns) is distinct from 'array' then raise exception 'Invalid snapshot.'; end if;
 count_rows=jsonb_array_length(p_rows);
 if count_rows<1 or count_rows>5000 or jsonb_array_length(p_columns)<2 or jsonb_array_length(p_columns)>120 or p_identity_column is null or p_identity_column<0 or p_identity_column>=jsonb_array_length(p_columns) then raise exception 'Invalid table dimensions.'; end if;
 if exists(select 1 from jsonb_array_elements(p_rows) r where jsonb_typeof(r)<>'array' or jsonb_array_length(r)<>jsonb_array_length(p_columns)) then raise exception 'Table rows must match the header width.'; end if;
 select as_of into latest_date from public.screener_library_snapshots where screener_slug=p_slug order by id desc limit 1;
 if p_as_of<latest_date then raise exception 'The data date is earlier than the latest publication. Choose the correct date; saved history is unchanged.'; end if;
 select * into saved from public.screener_library_snapshots where screener_slug=p_slug and as_of=p_as_of and content_hash=p_hash;
 if found then return jsonb_build_object('id',saved.id,'as_of',saved.as_of,'row_count',saved.row_count,'already_saved',true); end if;
 insert into public.screener_library_snapshots(screener_slug,as_of,columns,rows,identity_column,row_count,source_url,content_hash,definition,published_by)
 values(p_slug,p_as_of,p_columns,p_rows,p_identity_column,count_rows,p_source_url,p_hash,jsonb_build_object('display_name',s.display_name,'category',s.category,'description',s.description,'rule_notes',s.rule_notes),p_actor) returning * into saved;
 return jsonb_build_object('id',saved.id,'as_of',saved.as_of,'row_count',saved.row_count,'already_saved',false);
end; $$;
revoke all on function public.publish_screener_library_snapshot(text,date,jsonb,jsonb,integer,text,text,uuid) from public,anon,authenticated;
grant execute on function public.publish_screener_library_snapshot(text,date,jsonb,jsonb,integer,text,text,uuid) to service_role;

-- Empty, editable starter definitions; no third-party result lists are seeded.
insert into public.screener_library(slug,display_name,category,description,rule_notes) values
('agi-momentum-candidates','AGI Momentum candidates','Momentum','Price and earnings-momentum candidate tables.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('agi-value-candidates','AGI Value candidates','Value','Valuation and earnings-yield candidate tables.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('agi-growth-candidates','AGI Growth candidates','Growth','Revenue and earnings-growth candidate tables.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('agi-quality-candidates','AGI Quality candidates','Quality','Profitability, balance-sheet and earnings-quality candidates.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('agi-all-weather-candidates','AGI All-Weather candidates','Multi-factor','Combined factor candidates; final ranks and weights need separate review.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('golden-cross','Golden cross','Moving averages','Tables of bullish moving-average conditions.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('death-cross','Death cross','Moving averages','Tables of bearish moving-average conditions.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('volume-breakouts','Volume breakouts','Technicals','Price and traded-volume breakout candidates.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('relative-strength','Relative strength','Momentum','Stock performance compared with an index, sector or industry.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('fii-holding-increases','FII holding increases','Shareholding','Foreign-institution shareholding changes, using the reported quarter.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('dii-holding-increases','DII holding increases','Shareholding','Domestic-institution shareholding changes, using the reported quarter.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('candlestick-patterns','Candlestick patterns','Candlesticks','Dated pattern tables with their observation timeframe.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('dividend-quality','Dividend quality','Dividends','Dividend and cash-flow candidate tables.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('earnings-growth','Earnings growth','Growth','Quarterly or annual earnings-growth candidates.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('financial-red-flags','Financial red flags','Risk flags','Financial risk indicators for further research.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.'),
('analyst-estimate-candidates','Analyst estimate candidates','Analyst estimates','Imported consensus or forecast tables with a dated source.','Imported candidate table. The importer checks structure and security identifiers; it does not independently calculate or verify this screen’s financial rules.');
