-- Include the locked definition in duplicate detection, preserving same-day rule edits.
create or replace function public.publish_screener_library_snapshot(p_slug text,p_as_of date,p_columns jsonb,p_rows jsonb,p_identity_column integer,p_source_url text,p_hash text,p_actor uuid)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare s public.screener_library%rowtype; saved public.screener_library_snapshots%rowtype; latest_date date; count_rows integer; saved_definition jsonb; effective_hash text;
begin
 select * into s from public.screener_library where slug=p_slug and not archived for update;
 if not found then raise exception 'Screener not found.'; end if;
 if p_actor is null or p_as_of is null or jsonb_typeof(p_rows) is distinct from 'array' or jsonb_typeof(p_columns) is distinct from 'array' then raise exception 'Invalid snapshot.'; end if;
 count_rows=jsonb_array_length(p_rows);
 if count_rows<1 or count_rows>5000 or jsonb_array_length(p_columns)<2 or jsonb_array_length(p_columns)>120 or p_identity_column is null or p_identity_column<0 or p_identity_column>=jsonb_array_length(p_columns) then raise exception 'Invalid table dimensions.'; end if;
 if exists(select 1 from jsonb_array_elements(p_rows) r where jsonb_typeof(r)<>'array' or jsonb_array_length(r)<>jsonb_array_length(p_columns)) then raise exception 'Table rows must match the header width.'; end if;
 select as_of into latest_date from public.screener_library_snapshots where screener_slug=p_slug order by id desc limit 1;
 if p_as_of<latest_date then raise exception 'The data date is earlier than the latest publication. Choose the correct date; saved history is unchanged.'; end if;
 saved_definition=jsonb_build_object('display_name',s.display_name,'category',s.category,'description',s.description,'rule_notes',s.rule_notes);
 if p_hash is null or p_hash !~ '^[a-f0-9]{64}$' then raise exception 'Invalid content hash.'; end if;
 effective_hash=pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_hash || saved_definition::text,'UTF8')),'hex');
 select * into saved from public.screener_library_snapshots where screener_slug=p_slug and as_of=p_as_of and content_hash=effective_hash;
 if found then return jsonb_build_object('id',saved.id,'as_of',saved.as_of,'row_count',saved.row_count,'already_saved',true); end if;
 insert into public.screener_library_snapshots(screener_slug,as_of,columns,rows,identity_column,row_count,source_url,content_hash,definition,published_by)
 values(p_slug,p_as_of,p_columns,p_rows,p_identity_column,count_rows,p_source_url,effective_hash,saved_definition,p_actor) returning * into saved;
 return jsonb_build_object('id',saved.id,'as_of',saved.as_of,'row_count',saved.row_count,'already_saved',false);
end; $$;
revoke all on function public.publish_screener_library_snapshot(text,date,jsonb,jsonb,integer,text,text,uuid) from public,anon,authenticated;
grant execute on function public.publish_screener_library_snapshot(text,date,jsonb,jsonb,integer,text,text,uuid) to service_role;

