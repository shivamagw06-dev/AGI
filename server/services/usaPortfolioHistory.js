// Read-only Yahoo daily data. No broker calls or portfolio allocation mutations.
import fs from 'node:fs/promises';
import {createSupabaseAdmin} from '../lib/supabaseAdmin.js';
const RETRY_MS=15*60*1000;
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
const seedPath=fileURLToPath(new URL('../data/usaPortfolioHistory.json',import.meta.url));
export function completedUSDate(now=new Date()) {
 const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',hourCycle:'h23'}).formatToParts(now).map(p=>[p.type,p.value]));
 const day=`${parts.year}-${parts.month}-${parts.day}`;
 // Wait until 5 pm New York, including on early-close days. Never ingest an open daily bar.
 return Number(parts.hour)>=17?day:new Date(Date.parse(day+'T00:00:00Z')-86400000).toISOString().slice(0,10);
}
export function parseYahoo(symbol,payload,cutoff){
 const d=payload?.chart?.result?.[0],m=d?.meta,q=d?.indicators?.quote?.[0],adj=d?.indicators?.adjclose?.[0]?.adjclose;
 if(!m||m.symbol!==symbol||m.currency!=='USD'||!['EQUITY','ETF'].includes(m.instrumentType)||!q||!adj)throw Error('Unverified USD equity/ETF history');
 const fmt=new Intl.DateTimeFormat('en-CA',{timeZone:m.exchangeTimezoneName||'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'});
 const bars=[],pendingDates=[];let expectedDate=null;
 for(const [i,t] of (d.timestamp||[]).entries()){
  const parts=Object.fromEntries(fmt.formatToParts(new Date(t*1000)).map(p=>[p.type,p.value]));const date=`${parts.year}-${parts.month}-${parts.day}`;
  if(date>cutoff)continue;expectedDate=!expectedDate||date>expectedDate?date:expectedDate;
  const a=adj[i],c=q.close?.[i];if(!Number.isFinite(a)||a<=0||!Number.isFinite(c)||c<=0){pendingDates.push(date);continue;}
  bars.push([date,a,c,q.volume?.[i]??null]);
 }
 if(m.regularMarketTime){const marketDate=fmt.format(new Date(m.regularMarketTime*1000));if(marketDate<=cutoff&&(!expectedDate||marketDate>expectedDate))expectedDate=marketDate;}
 bars.sort((a,b)=>a[0].localeCompare(b[0]));
 if(!bars.length||new Set(bars.map(b=>b[0])).size!==bars.length)throw Error('Missing or duplicate daily prices');
 return {status:'ok',pendingDates,expectedDate,source:`https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/history/`,name:m.longName||m.shortName,currency:m.currency,exchange:m.exchangeName,instrumentType:m.instrumentType,bars,events:d.events||{},firstDate:bars[0][0],lastDate:bars.at(-1)[0]};
}
export function createUSHistory({fetcher=fetch,now=()=>new Date(),pause=ms=>new Promise(r=>setTimeout(r,ms)),readSeed=()=>fs.readFile(seedPath,'utf8'),persist=async()=>{}}={}){
 let snapshot=null,inflight=null,lastAttempt=0,lastError=null;
 async function read(){if(!snapshot)snapshot=JSON.parse(await readSeed());return {...snapshot,refresh:{mode:'daily-after-us-close',lastAttempt:lastAttempt?new Date(lastAttempt).toISOString():null,error:lastError,inProgress:!!inflight,nextRetryAt:lastError&&lastAttempt?new Date(lastAttempt+RETRY_MS).toISOString():null}};}
 async function refresh(){
  if(inflight)return inflight;
  inflight=(async()=>{
   const old=await read(),cutoff=completedUSDate(now());
   if(old.completedCutoff===cutoff||lastAttempt&&now().getTime()-lastAttempt<RETRY_MS)return read();
   lastAttempt=now().getTime();const securities={...old.securities},pending=[];
   const start=Math.min(Date.parse(cutoff+'T00:00:00Z')-405*86400000,Date.parse('2026-09-15T00:00:00Z'),Date.parse((old.calendar[0]||'2026-09-15')+'T00:00:00Z'));
   const symbols=['SPY',...Object.keys(old.securities).filter(s=>s!=='SPY')];
   for(const symbol of symbols){
    const url=new URL(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`);
    url.search=new URLSearchParams({interval:'1d',period1:String(Math.floor(start/1000)),period2:String(Date.parse(cutoff+'T00:00:00Z')/1000+86400),events:'div,splits',includeAdjustedClose:'true'});
    try{
     const res=await fetcher(url,{headers:{'User-Agent':'Mozilla/5.0','Accept':'application/json'},signal:AbortSignal.timeout(20000)});
     if([401,403,429].includes(res.status))throw Object.assign(Error(`Yahoo HTTP ${res.status}; refresh paused`),{abort:true});
     if(!res.ok)throw Error(`Yahoo HTTP ${res.status}`);
     const series=parseYahoo(symbol,await res.json(),cutoff);
     const expected=securities.SPY?.bars?.map(b=>b[0])||[];
     const dates=new Set(series.bars.map(b=>b[0]));
     if((old.securities[symbol]?.bars||[]).some(b=>!dates.has(b[0])))throw Error('Incomplete history response; verified prices retained');
     const missing=(series.pendingDates||[]).filter(d=>d>=(old.securities[symbol]?.firstDate||series.firstDate));
     if(symbol==='SPY'&&(missing.length||series.lastDate<series.expectedDate||series.lastDate<old.asOf))throw Error(`Latest US close pending from Yahoo${' for '+(missing.at(-1)||series.expectedDate||cutoff)}; last verified prices retained`);
     if(symbol!=='SPY'&&(missing.length||expected.some(d=>d>=series.firstDate&&!dates.has(d))||series.lastDate<old.securities[symbol]?.lastDate))throw Error('Incomplete daily series');
     securities[symbol]=series;
    }catch(e){if(e.abort||symbol==='SPY')throw e;pending.push(symbol);if(!securities[symbol])securities[symbol]={status:'unavailable',reason:'Daily history refresh pending; no prices estimated'};}
    await pause(300);
   }
   const calendar=securities.SPY.bars.map(b=>b[0]),asOf=calendar.at(-1);
   if(Date.parse(cutoff)-Date.parse(asOf)>4*86400000)throw Error('Yahoo benchmark is stale; previous snapshot retained');
   if(asOf<old.asOf)throw Error('Older benchmark response rejected');
   snapshot={...old,generatedAt:now().toISOString(),requestedCutoff:cutoff,completedCutoff:pending.length?null:cutoff,asOf,calendar,securities};delete snapshot.refresh;
   lastError=pending.length?`Latest close pending for ${pending.length} instruments; verified history retained. Retrying every 15 minutes.`:null;
   await persist(snapshot);
   return read();
  })().catch(e=>{lastError=e.message;if(snapshot)snapshot.completedCutoff=null;return read();}).finally(()=>{inflight=null;});return inflight;
 }
 async function ensureSymbol(symbol){
  if(!/^[A-Z0-9][A-Z0-9.\-^]{0,19}$/.test(symbol))throw Error('Invalid Yahoo symbol');
  if(inflight)await inflight;
  const old=await read();if(old.securities[symbol]?.status==='ok')return old.securities[symbol];
  const cutoff=completedUSDate(now()),url=new URL(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`);
  url.search=new URLSearchParams({interval:'1d',period1:String(Math.floor(Date.parse('2026-09-15T00:00:00Z')/1000)),period2:String(Date.parse(cutoff+'T00:00:00Z')/1000+86400),events:'div,splits',includeAdjustedClose:'true'});
  const res=await fetcher(url,{headers:{'User-Agent':'Mozilla/5.0',Accept:'application/json'},signal:AbortSignal.timeout(20000)});if(!res.ok)throw Error('Yahoo instrument verification unavailable');
  const series=parseYahoo(symbol,await res.json(),cutoff);snapshot={...snapshot,securities:{...snapshot.securities,[symbol]:series}};await persist(snapshot);return series;
 }
 return {read,refresh,ensureSymbol};
}
const cachePath=path.join(process.env.DATA_DIR||os.tmpdir(),'agi-usa-portfolio-history.json');
export function selectHistorySnapshot(seed,candidates=[]){
 const valid=[seed,...candidates].filter(d=>d?.schemaVersion===1&&d.asOf&&d.calendar?.length&&d.securities?.SPY?.status==='ok');
 valid.sort((a,b)=>b.asOf.localeCompare(a.asOf)||(b.generatedAt||'').localeCompare(a.generatedAt||''));
 return {...valid[0],mappings:seed.mappings};
}
async function persistStored(snapshot){
 const client=createSupabaseAdmin();if(!client)throw Error('Durable USA history storage unavailable');
 const {error}=await client.from('agi_usa_history_snapshot').upsert({id:'daily',document:snapshot,updated_at:new Date().toISOString()});if(error)throw Error('USA history persistence pending; retry scheduled');
 await fs.mkdir(path.dirname(cachePath),{recursive:true});await fs.writeFile(cachePath+'.tmp',JSON.stringify(snapshot));await fs.rename(cachePath+'.tmp',cachePath);
}
async function readStoredSeed(){
 const seed=JSON.parse(await fs.readFile(seedPath,'utf8')),candidates=[];
 try{candidates.push(JSON.parse(await fs.readFile(cachePath,'utf8')));}catch{}
 const client=createSupabaseAdmin();if(!client)throw Error('Durable USA history storage unavailable');
 const {data,error}=await client.from('agi_usa_history_snapshot').select('document').eq('id','daily').maybeSingle();if(error)throw Error('Durable USA history cannot be read; refusing to fall back to an older deployment seed');
 if(data)candidates.push(data.document);
 const selected=selectHistorySnapshot(seed,candidates);if(!data||selected.asOf>data.document.asOf)await persistStored(selected);
 return JSON.stringify(selected);
}
export const usaHistory=createUSHistory({readSeed:readStoredSeed,persist:persistStored});
export function startUSHistoryScheduler(){usaHistory.refresh().catch(()=>{});const timer=setInterval(()=>usaHistory.refresh().catch(()=>{}),60000);timer.unref();return timer;}
