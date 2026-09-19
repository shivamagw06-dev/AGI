-- Portfolio intelligence integrity: canonical instruments and durable market refreshes.
-- Applied to production before the client release.

insert into public.portfolio_instruments (canonical_key, symbol, asset_name, asset_type, exchange, country, currency, isin, provider_keys)
select distinct on (lower((case when upper(coalesce(h.country, '')) in ('US','USA','UNITED STATES','UNITED STATES OF AMERICA') or h.currency='USD' then 'US' when upper(coalesce(h.country,''))='INDIA' or h.currency='INR' then 'India' else coalesce(h.country,'Other') end)||':'||coalesce(h.market,'')||':'||h.symbol||':'||h.asset_type))
  lower((case when upper(coalesce(h.country, '')) in ('US','USA','UNITED STATES','UNITED STATES OF AMERICA') or h.currency='USD' then 'US' when upper(coalesce(h.country,''))='INDIA' or h.currency='INR' then 'India' else coalesce(h.country,'Other') end)||':'||coalesce(h.market,'')||':'||h.symbol||':'||h.asset_type),
  h.symbol, h.asset_name, h.asset_type, coalesce(h.market,''),
  case when upper(coalesce(h.country,'')) in ('US','USA','UNITED STATES','UNITED STATES OF AMERICA') or h.currency='USD' then 'US' when upper(coalesce(h.country,''))='INDIA' or h.currency='INR' then 'India' else h.country end,
  h.currency, h.isin,
  case when h.provider_key is null then '{}'::jsonb else jsonb_build_object(coalesce(h.price_source,'stored'),h.provider_key) end
from public.client_portfolio_holdings h
order by lower((case when upper(coalesce(h.country, '')) in ('US','USA','UNITED STATES','UNITED STATES OF AMERICA') or h.currency='USD' then 'US' when upper(coalesce(h.country,''))='INDIA' or h.currency='INR' then 'India' else coalesce(h.country,'Other') end)||':'||coalesce(h.market,'')||':'||h.symbol||':'||h.asset_type), h.updated_at desc
on conflict (canonical_key) do update set asset_name=excluded.asset_name, isin=coalesce(excluded.isin,public.portfolio_instruments.isin), provider_keys=public.portfolio_instruments.provider_keys||excluded.provider_keys, updated_at=now();

update public.client_portfolio_holdings h set instrument_id=i.id, country=i.country, updated_at=now()
from public.portfolio_instruments i
where i.canonical_key=lower((case when upper(coalesce(h.country, '')) in ('US','USA','UNITED STATES','UNITED STATES OF AMERICA') or h.currency='USD' then 'US' when upper(coalesce(h.country,''))='INDIA' or h.currency='INR' then 'India' else coalesce(h.country,'Other') end)||':'||coalesce(h.market,'')||':'||h.symbol||':'||h.asset_type)
and (h.instrument_id is distinct from i.id or h.country is distinct from i.country);

update public.client_portfolio_transactions t set instrument_id=i.id
from public.portfolio_instruments i
where i.canonical_key=lower((case when upper(coalesce(t.country, '')) in ('US','USA','UNITED STATES','UNITED STATES OF AMERICA') or t.currency='USD' then 'US' when upper(coalesce(t.country,''))='INDIA' or t.currency='INR' then 'India' else coalesce(t.country,'Other') end)||':'||coalesce(t.market,'')||':'||t.symbol||':'||t.asset_type)
and t.instrument_id is distinct from i.id;

create or replace function public.sync_client_portfolio_market_package(p_portfolio_id uuid,p_rows jsonb,p_events jsonb default '[]'::jsonb)
returns jsonb language plpgsql security definer set search_path='' as $$
declare v_row jsonb; v_event jsonb; v_user_id uuid; v_holding public.client_portfolio_holdings%rowtype; v_instrument_id uuid; v_country text; v_key text; v_price_count integer:=0; v_event_count integer:=0;
begin
  select user_id into v_user_id from public.client_portfolios where id=p_portfolio_id and user_id=auth.uid();
  if v_user_id is null then raise exception 'Portfolio not found or access denied'; end if;
  for v_row in select value from jsonb_array_elements(coalesce(p_rows,'[]'::jsonb)) loop
    select * into v_holding from public.client_portfolio_holdings where id=(v_row->>'holding_id')::uuid and portfolio_id=p_portfolio_id and user_id=v_user_id;
    if not found then continue; end if;
    v_country:=case when upper(coalesce(v_row->>'country',v_holding.country,'')) in ('US','USA','UNITED STATES','UNITED STATES OF AMERICA') or coalesce(v_row->>'currency',v_holding.currency)='USD' then 'US' when upper(coalesce(v_row->>'country',v_holding.country,''))='INDIA' or coalesce(v_row->>'currency',v_holding.currency)='INR' then 'India' else coalesce(v_row->>'country',v_holding.country,'Other') end;
    v_key:=lower(v_country||':'||coalesce(v_row->>'market',v_holding.market,'')||':'||coalesce(v_row->>'symbol',v_holding.symbol)||':'||coalesce(v_row->>'asset_type',v_holding.asset_type));
    insert into public.portfolio_instruments(canonical_key,symbol,asset_name,asset_type,exchange,country,currency,isin,provider_keys)
    values(v_key,coalesce(v_row->>'symbol',v_holding.symbol),coalesce(v_row->>'asset_name',v_holding.asset_name),coalesce(v_row->>'asset_type',v_holding.asset_type),coalesce(v_row->>'market',v_holding.market,''),v_country,coalesce(v_row->>'currency',v_holding.currency),coalesce(nullif(v_row->>'isin',''),v_holding.isin),case when nullif(v_row->>'provider_key','') is null then '{}'::jsonb else jsonb_build_object(coalesce(nullif(v_row->>'source',''),'market'),v_row->>'provider_key') end)
    on conflict(canonical_key) do update set asset_name=excluded.asset_name,isin=coalesce(excluded.isin,public.portfolio_instruments.isin),provider_keys=public.portfolio_instruments.provider_keys||excluded.provider_keys,updated_at=now() returning id into v_instrument_id;
    update public.client_portfolio_holdings set instrument_id=v_instrument_id,country=v_country,sector=coalesce(nullif(v_row->>'sector',''),sector),isin=coalesce(nullif(v_row->>'isin',''),isin),provider_key=coalesce(nullif(v_row->>'provider_key',''),provider_key),current_price=coalesce(nullif(v_row->>'price','')::numeric,current_price),price_source=coalesce(nullif(v_row->>'source',''),price_source,'manual'),price_as_of=coalesce(nullif(v_row->>'as_of','')::timestamptz,price_as_of),data_quality=coalesce(nullif(v_row->>'quality',''),data_quality,'manual'),updated_at=now() where id=v_holding.id;
    if nullif(v_row->>'price','') is not null and nullif(v_row->>'as_of','') is not null then
      insert into public.portfolio_market_prices(instrument_id,price_date,close_price,currency,source,source_as_of,quality)
      values(v_instrument_id,(v_row->>'as_of')::timestamptz::date,(v_row->>'price')::numeric,coalesce(v_row->>'currency',v_holding.currency),coalesce(nullif(v_row->>'source',''),'market_package'),(v_row->>'as_of')::timestamptz,coalesce(nullif(v_row->>'quality',''),'observed'))
      on conflict(instrument_id,price_date,source) do update set close_price=excluded.close_price,source_as_of=excluded.source_as_of,quality=excluded.quality;
      v_price_count:=v_price_count+1;
    end if;
  end loop;
  for v_event in select value from jsonb_array_elements(coalesce(p_events,'[]'::jsonb)) loop
    if nullif(v_event->>'title','') is null or nullif(v_event->>'occurred_at','') is null then continue; end if;
    insert into public.client_portfolio_intelligence_events(user_id,portfolio_id,event_key,symbol,event_type,title,summary,occurred_at,source,source_url,metadata)
    values(v_user_id,p_portfolio_id,coalesce(nullif(v_event->>'event_key',''),md5(coalesce(v_event->>'symbol','')||':'||v_event->>'title'||':'||v_event->>'occurred_at')),nullif(v_event->>'symbol',''),coalesce(nullif(v_event->>'event_type',''),'market_event'),v_event->>'title',nullif(v_event->>'summary',''),(v_event->>'occurred_at')::timestamptz,coalesce(nullif(v_event->>'source',''),'market_package'),nullif(v_event->>'source_url',''),coalesce(v_event->'payload',v_event))
    on conflict(portfolio_id,event_key) do update set summary=excluded.summary,occurred_at=excluded.occurred_at,source_url=excluded.source_url,metadata=excluded.metadata;
    v_event_count:=v_event_count+1;
  end loop;
  return jsonb_build_object('holdings',jsonb_array_length(coalesce(p_rows,'[]'::jsonb)),'prices',v_price_count,'events',v_event_count);
end; $$;
revoke all on function public.sync_client_portfolio_market_package(uuid,jsonb,jsonb) from public,anon;
grant execute on function public.sync_client_portfolio_market_package(uuid,jsonb,jsonb) to authenticated;
