// Read-only Yahoo daily data. No broker calls or portfolio allocation mutations.
import fs from 'node:fs/promises';
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
 const bars=[];
 for(const [i,t] of (d.timestamp||[]).entries()){
  const parts=Object.fromEntries(fmt.formatToParts(new Date(t*1000)).map(p=>[p.type,p.value]));const date=`${parts.year}-${parts.month}-${parts.day}`;
  if(date>cutoff)continue;
  const a=adj[i],c=q.close?.[i];if(!Number.isFinite(a)||a<=0||!Number.isFinite(c)||c<=0)continue;
  bars.push([date,a,c,q.volume?.[i]??null]);
 }
 bars.sort((a,b)=>a[0].localeCompare(b[0]));
 if(!bars.length||new Set(bars.map(b=>b[0])).size!==bars.length)throw Error('Missing or duplicate daily prices');
 return {status:'ok',source:`https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}/history/`,name:m.longName||m.shortName,currency:m.currency,exchange:m.exchangeName,instrumentType:m.instrumentType,bars,events:d.events||{},firstDate:bars[0][0],lastDate:bars.at(-1)[0]};
}
export function createUSHistory({fetcher=fetch,now=()=>new Date(),pause=ms=>new Promise(r=>setTimeout(r,ms)),readSeed=()=>fs.readFile(seedPath,'utf8')}={}){
 let snapshot=null,inflight=null,lastAttempt=0,lastError=null;
 async function read(){if(!snapshot)snapshot=JSON.parse(await readSeed());return {...snapshot,refresh:{mode:'daily-after-us-close',lastAttempt:lastAttempt?new Date(lastAttempt).toISOString():null,error:lastError}};}
 async function refresh(){
  if(inflight)return inflight;
  inflight=(async()=>{
   const old=await read(),cutoff=completedUSDate(now());
   if(old.requestedCutoff===cutoff||now().getTime()-lastAttempt<3600000)return old;
   lastAttempt=now().getTime();const securities={};
   const start=Math.min(Date.parse(cutoff+'T00:00:00Z')-405*86400000,Date.parse('2026-09-15T00:00:00Z'));
   const symbols=['SPY',...Object.keys(old.securities).filter(s=>s!=='SPY')];
   for(const symbol of symbols){
    const url=new URL(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`);
    url.search=new URLSearchParams({interval:'1d',period1:String(Math.floor(start/1000)),period2:String(Date.parse(cutoff+'T00:00:00Z')/1000+86400),events:'div,splits',includeAdjustedClose:'true'});
    try{
     const res=await fetcher(url,{headers:{'User-Agent':'Mozilla/5.0','Accept':'application/json'},signal:AbortSignal.timeout(20000)});
     if([401,403,429].includes(res.status))throw Object.assign(Error(`Yahoo HTTP ${res.status}; refresh paused`),{abort:true});
     if(!res.ok)throw Error(`Yahoo HTTP ${res.status}`);
     securities[symbol]=parseYahoo(symbol,await res.json(),cutoff);
    }catch(e){if(e.abort||symbol==='SPY')throw e;securities[symbol]={status:'unavailable',reason:'Daily history refresh failed; no prices estimated'};}
    await pause(300);
   }
   const calendar=securities.SPY.bars.map(b=>b[0]),asOf=calendar.at(-1);
   if(Date.parse(cutoff)-Date.parse(asOf)>4*86400000)throw Error('Yahoo benchmark is stale; previous snapshot retained');
   snapshot={...old,generatedAt:now().toISOString(),requestedCutoff:cutoff,asOf,calendar,securities};delete snapshot.refresh;lastError=null;
   return read();
  })().catch(e=>{lastError=e.message;return read();}).finally(()=>{inflight=null;});return inflight;
 }
 return {read,refresh};
}
const cachePath=path.join(process.env.DATA_DIR||os.tmpdir(),'agi-usa-portfolio-history.json');
async function readStoredSeed(){
 const seed=JSON.parse(await fs.readFile(seedPath,'utf8'));
 try{const cached=JSON.parse(await fs.readFile(cachePath,'utf8'));if(cached.schemaVersion===1&&cached.asOf>=seed.asOf&&cached.calendar?.length&&cached.securities?.SPY?.status==='ok')return JSON.stringify({...cached,mappings:seed.mappings});}catch{/* Rebuild the public price cache from the committed snapshot. */}
 return JSON.stringify(seed);
}
export const usaHistory=createUSHistory({readSeed:readStoredSeed});
async function refreshStored(){const d=await usaHistory.refresh();if(!d.refresh.error){await fs.mkdir(path.dirname(cachePath),{recursive:true});await fs.writeFile(cachePath+'.tmp',JSON.stringify(d));await fs.rename(cachePath+'.tmp',cachePath);}}
export function startUSHistoryScheduler(){refreshStored().catch(()=>{});const timer=setInterval(()=>refreshStored().catch(()=>{}),3600000);timer.unref();return timer;}
