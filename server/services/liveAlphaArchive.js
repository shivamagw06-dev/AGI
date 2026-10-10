import { rest } from './liveAlphaPersistence.js';
import { getLiveAlphaWorkspace } from './liveAlphaWorkspace.js';
import { sharedCandleBook } from './candlePriceBook.js';
import { latestLiveAlphaPrints } from './liveAlphaRuntime.js';
import { publicationRows,stockReturn,directionReturn,archiveStatus,chartRows,istDateKey,positive,COST_MODEL } from './liveAlphaPublicationModel.js';
import { nseSession,sessionState } from './liveAlphaSession.js';
const historicalCache=new Map();
const datePattern=/^\d{4}-\d{2}-\d{2}$/;
export function archiveFilters(query={},now=new Date()){
 const today=istDateKey(now),from=query.from||new Date(now.getTime()-30*86400000).toISOString().slice(0,10),to=query.to||today;
 if(!datePattern.test(from)||!datePattern.test(to)||!Number.isFinite(Date.parse(from))||!Number.isFinite(Date.parse(to))||new Date(from).toISOString().slice(0,10)!==from||new Date(to).toISOString().slice(0,10)!==to||from>to||to>today)throw Object.assign(new Error('Choose a valid past date range.'),{status:400});
 const symbol=String(query.symbol||'').trim().toUpperCase();if(!/^[A-Z0-9&.\-]{0,30}$/.test(symbol))throw Object.assign(new Error('Invalid stock search.'),{status:400});
 const direction=['positive','negative','conflicting'].includes(query.direction)?query.direction:'';
 const horizon=['15m','1h','close','1d','5d','20d','exit'].includes(query.horizon)?query.horizon:'1d';
 return {from,to,fromIso:new Date(`${from}T00:00:00+05:30`).toISOString(),toIso:new Date(Date.parse(`${to}T00:00:00+05:30`)+86400000).toISOString(),symbol,direction,horizon,page:Math.max(0,Math.min(10000,parseInt(query.page,10)||0))};
}
export async function readArchive(query={}, {request=rest,now=new Date()}={}){
 const f=archiveFilters(query,now);
 const params=new URLSearchParams({select:'*,events:alpha_publication_events(kind,event_at),followups:alpha_publication_followups(*)',published_at:`gte.${f.fromIso}`,and:`(published_at.lt.${f.toIso})`,order:'published_at.desc,id.desc',limit:'25',offset:String(f.page*25)});
 if(f.symbol)params.set('symbol',`ilike.*${f.symbol}*`);if(f.direction)params.set('direction',`eq.${f.direction}`);
 const prints=latestLiveAlphaPrints();
 const [rows,summary]=await Promise.all([request('alpha_publications',{method:'GET',query:params.toString()}),request('rpc/alpha_archive_summary',{body:{p_from:f.fromIso,p_to:f.toIso,p_symbol:f.symbol,p_direction:f.direction,p_horizon:f.horizon},prefer:'return=representation'})]);
 return {kind:'published',filters:f,rows:(rows||[]).map(r=>{const print=prints.get(r.instrument_key);const settled=(r.followups||[]).filter(x=>x.status==='completed').sort((a,b)=>Date.parse(b.observed_at)-Date.parse(a.observed_at))[0];const liveValid=positive(print?.ltp)&&print?.observed_at&&sessionState(print.observed_at).open&&!['previous_close_seed','upstox_ohlc_1m'].includes(print.source)&&Date.parse(print.observed_at)>Date.parse(r.published_at)&&Date.parse(print.observed_at)<=now.getTime();const current=liveValid&&(!settled||Date.parse(print.observed_at)>Date.parse(settled.observed_at))?{price:print.ltp,at:print.observed_at}:{price:settled?.price,at:settled?.observed_at};return {...r,latest_price:current.price??null,latest_price_at:current.at??null,stock_return_pct:stockReturn(r.reference_price,current.price),signal_status:archiveStatus(r.events),measurement:r.followups?.find(x=>x.horizon===f.horizon)||null};}),summary,cost_model:COST_MODEL,generated_at:now.toISOString(),note:'All matching publications are included in the summary. Signal outcomes overlap and are not portfolio returns. Raw prices; corporate actions and dividends are not reconciled.'};
}
export async function historicalSnapshot(date,{now=new Date(),request=rest}={}){
 archiveFilters({from:date,to:date},now);
 const cached=historicalCache.get(date);if(cached&&Date.now()-cached.at<300000)return cached.rows;
 const workspace=await getLiveAlphaWorkspace({now:new Date(`${date}T15:31:00+05:30`)});
 const signals=workspace.signals.filter(s=>istDateKey(s.as_of)===date);
 const rows=publicationRows(signals,new Date(`${date}T15:29:00+05:30`)).filter(r=>r.direction).map(r=>({...r,id:`h:${date}:${r.symbol}`,kind:'historical_engine_record',published_at:null,quote_at:null,signal_status:'historical snapshot',quality:{publication_time_verified:false,liquidity_verified:r.quality.liquidity_verified},events:[],followups:[]}));
 historicalCache.set(date,{at:Date.now(),rows});if(historicalCache.size>20)historicalCache.delete(historicalCache.keys().next().value);
 return rows;
}
export async function readHistorical(query={},opts={}){
 const f=archiveFilters(query,opts.now);const date=query.date||f.to;
 const all=(await historicalSnapshot(date,opts)).filter(r=>(!f.symbol||r.symbol.includes(f.symbol))&&(!f.direction||r.direction===f.direction));
 return {kind:'historical_engine_record',date,rows:all.slice(f.page*25,f.page*25+25),summary:{published:all.length},filters:f,note:'Last stored in-session evaluation per engine on the selected date. This is not a complete intraday publication archive. Original web-publication times and simulated entries are unverified.'};
}
export async function dailyPriceSeries(key,from,to,{request=rest,book=sharedCandleBook(),maxSessions=260}={}){
 const params=new URLSearchParams({select:'*',instrument_key:`eq.${key}`,session_date:`gte.${from}`,and:`(session_date.lte.${to})`,order:'session_date.asc',limit:'400'});
 const stored=await request('alpha_archive_daily_prices',{method:'GET',query:params.toString()})||[];
 const byDate=new Map(stored.map(r=>[r.session_date,r]));const rows=[],writes=[];
 for(let time=Date.parse(`${from}T12:00:00+05:30`);time<=Date.parse(`${to}T12:00:00+05:30`)&&rows.length<maxSessions;time+=86400000){
  const s=nseSession(time);if(!s)continue;
  const day=s.date;let row=byDate.get(day);
  if(!row){
   const result=await book.closeOn(key,day);
   row={instrument_key:key,session_date:day,price:positive(result.price),observed_at:result.candle_end||new Date(s.end).toISOString(),source:'upstox_daily_close_unadjusted',reason:result.reason||null};
   if(row.price){const {reason,...save}=row;writes.push(save);}
  }
  rows.push(row);
 }
 if(writes.length)await request('alpha_archive_daily_prices',{body:writes,query:'on_conflict=instrument_key,session_date',prefer:'resolution=ignore-duplicates,return=minimal'});
 return rows;
}
const detailCache=new Map();
export async function archiveDetail(id,{request=rest,book=sharedCandleBook(),now=new Date()}={}){
 if(!/^(h:\d{4}-\d{2}-\d{2}:[A-Z0-9&.\-]+|[a-f0-9-]{36})$/.test(id))throw Object.assign(new Error('Invalid signal record.'),{status:400});
 const hit=detailCache.get(id);if(hit&&now.getTime()-hit.at<60000)return hit.value;
 let record;
 if(id.startsWith('h:')){const [,day,symbol]=id.split(':');record=(await historicalSnapshot(day,{now,request})).find(r=>r.symbol===symbol);}
 else record=(await request('alpha_publications',{method:'GET',query:new URLSearchParams({select:'*,events:alpha_publication_events(*),followups:alpha_publication_followups(*),entries:alpha_publication_entries(*)',id:`eq.${id}`,limit:'1'}).toString()}))?.[0];
 if(!record)throw Object.assign(new Error('Signal not found.'),{status:404});
 const start=record.published_at||record.signal_at,from=istDateKey(start),to=istDateKey(new Date(now.getTime()-86400000));
 const [prices,benchmark]=from<=to?await Promise.all([dailyPriceSeries(record.instrument_key,from,to,{request,book}),dailyPriceSeries('NSE_INDEX|Nifty 50',from,to,{request,book})]):[[],[]];
 let referenceCheck={status:'recorded_publication'};
 if(id.startsWith('h:')){
  const [anchor,bmAnchor]=await Promise.all([book.priceAt(record.instrument_key,record.signal_at),book.priceAt('NSE_INDEX|Nifty 50',record.signal_at)]);
  if(!positive(bmAnchor.price)||!positive(record.benchmark_price)||Math.abs(record.benchmark_price/bmAnchor.price-1)>.03)record={...record,benchmark_price:null};
  referenceCheck={status:anchor.price&&positive(record.reference_price)&&Math.abs(Number(record.reference_price)/anchor.price-1)<=.03?'candle_consistent':'unverified',observed_price:anchor.price||null,reason:anchor.reason||null};
 }
 const validReference=referenceCheck.status!=='unverified';
 let chart=chartRows({...record,reference_price:validReference?record.reference_price:null},prices,benchmark);
 for(const f of record.followups||[]){if(f.status==='completed'&&positive(f.price)&&Date.parse(f.observed_at)>Date.parse(start))chart.push({at:f.observed_at,price:Number(f.price),stock_return_pct:validReference?stockReturn(record.reference_price,f.price):null,benchmark_return_pct:f.benchmark_return_pct,kind:'followup'});}
 chart=[...new Map(chart.map(p=>[p.at,p])).values()].sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
 const live=latestLiveAlphaPrints().get(record.instrument_key);const liveAt=Date.parse(live?.observed_at||'');
 if(positive(live?.ltp)&&Number.isFinite(liveAt)&&sessionState(liveAt).open&&!['previous_close_seed','upstox_ohlc_1m'].includes(live.source)&&liveAt>=Date.parse(start)&&liveAt<=now.getTime()&&(!chart.length||liveAt>Date.parse(chart.at(-1).at)))chart.push({at:live.observed_at,price:live.ltp,stock_return_pct:validReference?stockReturn(record.reference_price,live.ltp):null,benchmark_return_pct:null,kind:'recorded_quote'});
 const measured=chart.filter(p=>p.price&&Date.parse(p.at)>Date.parse(start));const last=measured.at(-1);const changes=measured.map(p=>p.stock_return_pct).filter(v=>v!=null);
 const value={record:{...record,signal_status:record.kind==='historical_engine_record'?'historical snapshot':archiveStatus(record.events)},chart,reference_check:referenceCheck,
  latest_price:last?.price||null,latest_price_at:last?.at||null,stock_return_pct:last?.stock_return_pct??null,directional_return_pct:directionReturn(record.direction,last?.stock_return_pct),
  best_observed_change_pct:changes.length?Math.max(...changes):null,worst_observed_change_pct:changes.length?Math.min(...changes):null,
  methodology:'Raw price change, before fees, tax and dividends. Daily closes and recorded quotes only; best/worst are observed points, not intraday extremes. Missing sessions break the chart. Corporate actions are not reconciled. A negative directional result assumes a hypothetical short, not buying the stock.',
  chart_limited:prices.length>=260,cost_model:COST_MODEL,generated_at:now.toISOString()};
 detailCache.set(id,{at:now.getTime(),value});if(detailCache.size>100)detailCache.delete(detailCache.keys().next().value);return value;
}
