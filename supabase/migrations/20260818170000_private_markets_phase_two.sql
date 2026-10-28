create unique index if not exists private_market_investor_transaction_unique_idx on public.private_market_investor_transactions(investor_id,observed_date,company_name,transaction_description);
create index if not exists private_market_investor_transaction_date_idx on public.private_market_investor_transactions(investor_id,observed_date desc);
update public.private_market_investors i set headquarters=s.original_values->>'Geographic Locations' from public.private_market_sources s where s.id=i.source_id;
insert into public.private_market_investor_transactions(id,investor_id,company_name,observed_date,transaction_description,source_id)
select md5(i.id::text||'|'||m[1]||'|'||m[3]||'|'||m[2])::uuid,i.id,btrim(m[3]),to_date(m[1],'MM/DD/YYYY'),btrim(m[2]),i.source_id
from public.private_market_investors i join public.private_market_sources s on s.id=i.source_id
cross join lateral regexp_matches(coalesce(s.original_values->>'Transaction Types [Buyers/Investors]',''),'([0-9]{2}/[0-9]{2}/[0-9]{4})[[:space:]]+([^\n]+)\n\(Target/Issuer: ([^)]+)\)[[:space:]]+-[[:space:]]+([^\n]+)','g') m
on conflict(investor_id,observed_date,company_name,transaction_description) do nothing;
