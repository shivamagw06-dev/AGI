import { nseSession, sessionState, istDateKey } from './liveAlphaSession.js';
export const PUBLICATION_HORIZONS = ['15m','1h','close','1d','5d','20d'];
export const COST_MODEL = '10 bps round-trip fees + 5 bps slippage per side; bid/ask fills; short borrow and financing excluded';
export const positive = n => n !== null && n !== undefined && Number.isFinite(Number(n)) && Number(n)>0 ? Number(n) : null;
export function stockReturn(reference, latest) { return positive(reference) && positive(latest) ? (Number(latest)/Number(reference)-1)*100 : null; }
export function directionReturn(direction, value) { return value == null || !['positive','negative'].includes(direction) ? null : value*(direction==='negative' ? -1 : 1); }
export function nextSession(at) {
 for(let d=1;d<=14;d++){const s=nseSession(new Date(new Date(at).getTime()+d*86400000));if(s)return s;}
 throw new Error('No trading session available');
}
export function publicationDueAt(at,horizon) {
 let s=nseSession(at); if(!s) throw new Error('Publication must be in a trading session');
 if(horizon==='close')return new Date(s.end).toISOString();
 if(horizon==='15m'||horizon==='1h'){
  let t=Date.parse(at), remaining=(horizon==='15m'?15:60)*60000;
  while(t+remaining>s.end){remaining-=Math.max(0,s.end-t);s=nextSession(s.start);t=s.start;}
  return new Date(t+remaining).toISOString();
 }
 const days={'1d':1,'5d':5,'20d':20}[horizon]; if(!days)throw new Error('Invalid horizon');
 for(let i=0;i<days;i++)s=nextSession(s.start);
 return new Date(s.end).toISOString();
}
export function publicationRows(signals, now=new Date()) {
 const rows=new Map();
 for(const signal of signals){
  const row=rows.get(signal.symbol)||{symbol:signal.symbol,sector:signal.sector,signal_at:signal.as_of,components:[]};
  if(Date.parse(signal.as_of)>Date.parse(row.signal_at)){row.signal_at=signal.as_of;row.components=[];}
  if(Date.parse(signal.as_of)===Date.parse(row.signal_at))row.components.push(signal);
  rows.set(signal.symbol,row);
 }
 return [...rows.values()].map(row=>{
  const active=row.components.filter(s=>['positive','negative'].includes(s.direction));
  const scores=active.map(s=>(s.direction==='negative'?-1:1)*Math.min(99,Math.round(Math.abs(Number(s.alpha_z)||0)*28+(Number(s.signal_quality_score??s.signal_quality?.score)||0)*.35)));
  const score=Math.max(-99,Math.min(99,scores.length?Math.round(scores.reduce((a,b)=>a+b,0)/Math.sqrt(scores.length)):0));
  const dirs=new Set(active.map(s=>s.direction));
  const anchor=row.components.find(s=>s.cash_instrument_key)||row.components.find(s=>String(s.instrument_key).startsWith('NSE_EQ|'))||row.components[0];
  const quoteAt=anchor?.price_quote_at||null;
  const age=quoteAt ? now.getTime()-Date.parse(quoteAt) : Infinity;
  return {symbol:row.symbol,sector:row.sector,signal_at:row.signal_at,source_key:`${row.symbol}|${row.signal_at}`,
   direction:dirs.size>1?'conflicting':dirs.size?[...dirs][0]:null,score,
   instrument_key:anchor?.cash_instrument_key||anchor?.instrument_key,
   reference_price:positive(anchor?.price_at_signal),benchmark_price:positive(anchor?.nifty_at_signal),quote_at:quoteAt,
   quality:{quote_fresh:age>=0&&age<=60000,quote_age_ms:Number.isFinite(age)?age:null,liquidity_verified:active.length>0&&active.every(s=>s.liquidity_verified===true&&s.liquidity_ok===true)},
   components:active.map(s=>({engine:s.engine,direction:s.direction,classification:s.classification,alpha_z:s.alpha_z,quality:s.signal_quality_score??s.signal_quality?.score,liquidity_verified:s.liquidity_verified===true,run_id:s.run_id||null})),
   component_keys:active.map(s=>`${s.engine}:${s.direction}`).sort(),schedule_base:now.toISOString(),
   schedule:sessionState(now).open?PUBLICATION_HORIZONS.map(horizon=>({horizon,due_at:publicationDueAt(now.toISOString(),horizon)})):[]
  };
 }).filter(r=>String(r.instrument_key).startsWith('NSE_EQ|'));
}
// A post-publication quote must be received after publication, stamped by the
// exchange after publication, and have uncrossed, reasonably tight depth.
export function eligibleQuote(rows, at, direction, {exit=false, windowMs=5*60000}={}) {
 if(!['positive','negative'].includes(direction))return null;
 const start=Date.parse(at);
 for(const r of [...rows].sort((a,b)=>Date.parse(a.exchange_timestamp)-Date.parse(b.exchange_timestamp))){
  const time=Date.parse(r.exchange_timestamp),received=Date.parse(r.observed_at);
  const bid=positive(r.best_bid),ask=positive(r.best_ask);
  if(!Number.isFinite(time)||!Number.isFinite(received)||time<=start||time>start+windowMs||received<time||received-time>60000||!sessionState(time).open||!bid||!ask||ask<bid||(ask-bid)/((ask+bid)/2)>0.02)continue;
  const buy=exit?direction==='negative':direction==='positive';
  return {observed_at:r.exchange_timestamp,price:buy?ask:bid,source:'recorded_bid_ask',spread_bps:(ask-bid)/((ask+bid)/2)*10000};
 }
 return null;
}
export function simulatedReturn(direction,entry,exit){
 if(!entry||!exit||!positive(entry.price)||!positive(exit.price))return null;
 const long=direction==='positive';if(!long&&direction!=='negative')return null;
 const entryFill=entry.price*(long?1.0005:.9995),exitFill=exit.price*(long?.9995:1.0005);
 return (long?(exitFill-entryFill):(entryFill-exitFill))/entryFill*100-.1;
}
export function archiveStatus(events=[]){return events.find(e=>e.kind==='reversed'||e.kind==='withdrawn')?.kind||'active';}
export function chartRows(publication,prices,benchmarks){
 const benchmarkMap=new Map(benchmarks.map(p=>[String(p.session_date),p]));
 return [{at:publication.published_at||publication.signal_at,price:publication.reference_price,stock_return_pct:positive(publication.reference_price)?0:null,benchmark_return_pct:positive(publication.benchmark_price)?0:null,kind:'reference'},
 ...prices.map(p=>({at:p.observed_at,price:positive(p.price),stock_return_pct:stockReturn(publication.reference_price,p.price),benchmark_return_pct:stockReturn(publication.benchmark_price,benchmarkMap.get(String(p.session_date))?.price),kind:'daily_close'}))];
}
export {istDateKey};

export function entryRow(entries){return Array.isArray(entries)?entries[0]:entries||null;}
