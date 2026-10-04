import {rest} from './liveAlphaPersistence.js';
import {sharedCandleBook} from './candlePriceBook.js';
import {eligibleQuote,simulatedReturn,stockReturn,directionReturn,positive,istDateKey,entryRow} from './liveAlphaPublicationModel.js';
import {nseSession} from './liveAlphaSession.js';
const BENCHMARK='NSE_INDEX|Nifty 50';
export async function snapshotWindow(key,at,{request=rest,minutes=5}={}){
 const time=Date.parse(at);
 return await request('live_market_snapshots',{method:'GET',query:new URLSearchParams({select:'instrument_key,exchange_timestamp,observed_at,ltp,best_bid,best_ask',instrument_key:`eq.${key}`,observed_at:`gte.${new Date(time).toISOString()}`,and:`(observed_at.lte.${new Date(time+(minutes+1)*60000).toISOString()})`,order:'observed_at.asc',limit:'100'}).toString()})||[];
}
export async function collectPublicationEntries({request=rest,now=new Date()}={}){
 const pubs=await request('alpha_publications',{method:'GET',query:new URLSearchParams({select:'*,entries:alpha_publication_entries(publication_id)',published_at:`gte.${new Date(now.getTime()-10*60000).toISOString()}`,order:'published_at.asc',limit:'1000'}).toString()})||[];
 const pending=pubs.filter(p=>!entryRow(p.entries)&&p.direction!=='conflicting'&&p.quality?.quote_fresh===true);
 if(!pending.length)return 0;
 const from=pending[0].published_at;
 const snapshots=[];
 for(let offset=0;offset<10000;offset+=1000){
  const rows=await request('live_market_snapshots',{method:'GET',query:new URLSearchParams({select:'instrument_key,exchange_timestamp,observed_at,ltp,best_bid,best_ask',observed_at:`gte.${from}`,order:'observed_at.asc,instrument_key.asc',limit:'1000',offset:String(offset)}).toString()})||[];
  snapshots.push(...rows);if(rows.length<1000)break;
 }
 const groups=new Map();for(const q of snapshots){if(!groups.has(q.instrument_key))groups.set(q.instrument_key,[]);groups.get(q.instrument_key).push(q);}
 const entries=pending.map(p=>{const q=eligibleQuote(groups.get(p.instrument_key)||[],p.published_at,p.direction);return q?{publication_id:p.id,...q}:null;}).filter(Boolean);
 if(entries.length)await request('alpha_publication_entries',{body:entries,query:'on_conflict=publication_id',prefer:'resolution=ignore-duplicates,return=minimal'});
 return entries.length;
}
export async function settlePublicationFollowup(row,{request=rest,book=sharedCandleBook(),now=new Date()}={}){
 const p=row.publication;if(!p||Date.parse(row.due_at)>now.getTime())return null;
 const base={attempts:Number(row.attempts||0)+1,next_attempt_at:new Date(now.getTime()+15*60000).toISOString()};
 const dueDate=istDateKey(row.due_at),session=nseSession(row.due_at);
 const isClose=['close','1d','5d','20d'].includes(row.horizon);
 const quoteTime=isClose&&session?new Date(session.end-60000).toISOString():row.due_at;
 const quotes=await snapshotWindow(p.instrument_key,quoteTime,{request,minutes:isClose?1:5});
 const quote=eligibleQuote(quotes.filter(q=>Date.parse(q.observed_at)<=now.getTime()),quoteTime,p.direction,{exit:true,windowMs:(isClose?1:5)*60000});
 let price=null,observed=null,source=null;
 // Directionless conflicting calls still have ordinary stock-price tracking.
 const ltpQuote=!isClose&&quotes.find(q=>positive(q.ltp)&&Number.isFinite(Date.parse(q.observed_at))&&Date.parse(q.observed_at)>=Date.parse(q.exchange_timestamp)&&Date.parse(q.observed_at)-Date.parse(q.exchange_timestamp)<=60000&&Date.parse(q.exchange_timestamp)>=Date.parse(quoteTime)&&Date.parse(q.exchange_timestamp)<=Date.parse(quoteTime)+60000&&Date.parse(q.exchange_timestamp)<=now.getTime());
 if(ltpQuote){price=Number(ltpQuote.ltp);observed=ltpQuote.exchange_timestamp;source='recorded_ltp';}
 let bm=null;
 if(dueDate<istDateKey(now)){
  const [stock,benchmark]=await Promise.all([isClose?book.closeOn(p.instrument_key,dueDate):book.priceAt(p.instrument_key,row.due_at),isClose?book.closeOn(BENCHMARK,dueDate):book.priceAt(BENCHMARK,row.due_at)]);
  if(positive(stock.price)&&(isClose||Math.abs(Date.parse(stock.candle_end)-Date.parse(row.due_at))<=60000)){price=Number(stock.price);observed=stock.candle_end;source=isClose?'upstox_daily_close_unadjusted':'upstox_minute_close_unadjusted';}
  if(positive(benchmark.price)&&(isClose||Math.abs(Date.parse(benchmark.candle_end)-Date.parse(row.due_at))<=60000))bm=benchmark;
 }else{
  const benchmarkQuotes=await snapshotWindow(BENCHMARK,quoteTime,{request,minutes:1});
  const match=benchmarkQuotes.find(q=>positive(q.ltp)&&Math.abs(Date.parse(q.exchange_timestamp)-Date.parse(observed||row.due_at))<=60000&&Date.parse(q.exchange_timestamp)<=now.getTime());
  if(match)bm={price:Number(match.ltp),candle_end:match.exchange_timestamp};
 }
 if(!price){const expired=now.getTime()-Date.parse(row.due_at)>7*86400000;return {...base,status:expired?'missing':'pending',reason:expired?'No usable follow-up price after seven days':'Awaiting quote or published historical candle'};}
 const raw=stockReturn(p.reference_price,price);
 const entry=entryRow(p.entries);
 return {...base,status:'completed',price,observed_at:observed,price_source:source,benchmark_price:bm?.price||null,benchmark_observed_at:bm?.candle_end||null,
  stock_return_pct:raw,directional_return_pct:directionReturn(p.direction,raw),benchmark_return_pct:stockReturn(p.benchmark_price,bm?.price),
  simulated_net_return_pct:entry&&quote?simulatedReturn(p.direction,entry,quote):null,
  reason:entry&&quote?'Hypothetical fixed-horizon bid/ask return; not an executed trade. Short borrow not verified':'Price tracking only; eligible post-publication entry or exit quote missing'};
}
export async function runArchiveCollection({request=rest,book=sharedCandleBook(),now=new Date()}={}){
 const entries=await collectPublicationEntries({request,now});
 const due=await request('alpha_publication_followups',{method:'GET',query:new URLSearchParams({select:'*,publication:alpha_publications!inner(*,entries:alpha_publication_entries(*))',status:'eq.pending',due_at:`lte.${now.toISOString()}`,next_attempt_at:`lte.${now.toISOString()}`,order:'next_attempt_at.asc,due_at.asc',limit:'25'}).toString()})||[];
 let completed=0;
 for(const row of due){
  const patch=await settlePublicationFollowup(row,{request,book,now});if(!patch)continue;
  await request('alpha_publication_followups',{method:'PATCH',query:new URLSearchParams({publication_id:`eq.${row.publication_id}`,horizon:`eq.${row.horizon}`,status:'eq.pending'}).toString(),body:patch});
  completed+=patch.status==='completed'?1:0;
 }
 return {entries,processed:due.length,completed};
}
let timer=null;let state={status:'not_started',last_at:null,last_error:null};
export function archiveCollectorStatus(){return {...state};}
export function startArchiveCollector(){
 if(timer||String(process.env.LIVE_ALPHA_SHADOW_ENABLED).toLowerCase()!=='true')return;
 const tick=async()=>{state={...state,status:'running'};try{const result=await runArchiveCollection();state={status:'ready',last_at:new Date().toISOString(),last_error:null,...result};}catch{state={...state,status:'degraded',last_at:new Date().toISOString(),last_error:'Archive follow-up collection failed'};}finally{timer=setTimeout(tick,60000);timer.unref?.();}};
 timer=setTimeout(tick,30000);timer.unref?.();
}
