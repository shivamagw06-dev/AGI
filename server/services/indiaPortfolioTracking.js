import { withGrowthMomentum } from './growthMomentumPortfolio.js';
import { nseSession } from './liveAlphaSession.js';
import { convictionView } from './convictionTracking.js';
import { createIndiaDailyReader, dailyDue, dailyValuation, completedDates } from './indiaPortfolioDaily.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { loadUpstoxNseIsinMap } from './companyIsinBackfill.js';
let instrumentCache=null,instrumentExpiry=0;
async function indiaMaster(){
 if(instrumentCache&&Date.now()<instrumentExpiry)return instrumentCache;
 const map=await loadUpstoxNseIsinMap({instrumentTypes:['EQ','BE']});
 instrumentCache={items:[...map].map(([symbol,x])=>({symbol,instrumentKey:x.instrument_key}))};instrumentExpiry=Date.now()+86400000;return instrumentCache;
}
import { createPortfolioStore } from './portfolioCatalog.js';
import { resolveUpstoxAccessToken } from '../providers/upstox.js';

export const INDIA_START = '2026-10-05';
export const INDIA_IDS = ['in-momentum','in-growth','in-value','in-quality','in-all-weather','in-preferred','in-conviction-long','in-conviction-short','in-growth-momentum-private'];
export function session(now = new Date()) {
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).map(x=>[x.type,x.value]));
 const minutes=+p.hour*60 + +p.minute;
 return {date:`${p.year}-${p.month}-${p.day}`,open:!!nseSession(now)&&minutes>=555&&minutes<930};
}
const stamp=v=>{const n=typeof v==='string'&&/^\d+$/.test(v)?Number(v):v;const d=new Date(n);return v!=null&&Number.isFinite(d.getTime())?d.toISOString():null;};
export function fresh(q, now) {const age=now.getTime()-Date.parse(q?.time);return q?.price>0&&age>=0&&age<=120000;}
export function createIndiaQuotes({master=indiaMaster, fetcher=fetch, token=()=>process.env.UPSTOX_ANALYTICS_TOKEN||resolveUpstoxAccessToken().token, now=()=>new Date()}={}) {
 let cache=null,pending=null;
 return async symbols=>{
  const key=[...new Set(symbols)].sort().join(',');const time=now();
  if(cache?.key===key&&time.getTime()-cache.saved<30000)return cache.value;
  if(pending)return pending;
  pending=(async()=>{
   const credential=token();if(!credential)throw Error('Upstox credentials unavailable');
   const {items}=await master();const resolved=symbols.map(symbol=>items.find(x=>x.symbol===symbol)).filter(Boolean);
   if(!resolved.length)throw Error('No NSE instruments resolved');
   const response=await fetcher('https://api.upstox.com/v3/market-quote/quotes?instrument_key='+encodeURIComponent(resolved.map(x=>x.instrumentKey).join(',')),{headers:{Accept:'application/json',Authorization:`Bearer ${credential}`},redirect:'error',signal:AbortSignal.timeout(20000)});
   if(!response.ok)throw Error(`Upstox quotes HTTP ${response.status}`);
   const body=await response.json();if(body.status!=='success'||!body.data)throw Error('Invalid Upstox response');
   const quotes={};for(const item of resolved){const raw=body.data[`NSE_EQ:${item.symbol}`]||body.data[item.instrumentKey]||body.data[item.instrumentKey.replace('|',':')];if(!raw)continue;
    // Last-trade time is required: a newly generated snapshot may contain stale LTP.
    const price=Number(raw.last_price);quotes[item.symbol]={price:Number.isFinite(price)&&price>0?price:null,time:stamp(raw.last_trade_time),instrumentKey:item.instrumentKey};}
   const value={quotes,fetchedAt:time.toISOString(),source:'Upstox'};cache={key,saved:time.getTime(),value};return value;
  })();try{return await pending;}finally{pending=null;}
 };
}
export function makeBaseline(p,quotes,now=new Date()) {
 const s=session(now);if(s.date!==INDIA_START||!s.open)return null;
 if(p.incomplete||!p.holdings?.length||p.holdings.some(h=>!h.symbol||!(h.weight>0))||Math.abs(p.holdings.reduce((sum,h)=>sum+h.weight,0)+(p.cashWeight||0)-100)>0.05)return null;
 if(p.holdings.some(h=>!fresh(quotes[h.symbol],now)||(h.instrumentKey&&quotes[h.symbol]?.instrumentKey!==h.instrumentKey)))return null;
 const total=p.holdings.reduce((sum,h)=>sum+h.weight,0)+(p.cashWeight||0);
 return {startedAt:now.toISOString(),revision:p.revision,...(p.conviction?{categories:p.categories,direction:p.direction}:{}),cashWeight:(p.cashWeight||0)/total*100,holdings:p.holdings.map(h=>({...h,weight:h.weight/total*100,basePrice:quotes[h.symbol].price,baseTime:quotes[h.symbol].time,instrumentKey:quotes[h.symbol].instrumentKey}))};
}
export function valueBaseline(base,quotes,now=new Date()) {
 const positions=base.holdings.map(h=>({...h,price:quotes[h.symbol]?.price??null,quoteTime:quotes[h.symbol]?.time??null,fresh:fresh(quotes[h.symbol],now)}));
 const complete=positions.every(h=>h.fresh&&h.price>0&&quotes[h.symbol].instrumentKey===h.instrumentKey);
 return {positions,complete,nav:complete?positions.reduce((sum,h)=>sum+h.weight*h.price/h.basePrice,base.cashWeight||0):null};
}
async function allRows(client,table) {
 const rows=[];
 for(let offset=0;;offset+=500){let query=client.from(table).select('*').order(table==='agi_india_daily_prices'?'session_date':'portfolio_id');if(table==='agi_india_portfolio_marks')query=query.order('session_date');const {data,error}=await query.range(offset,offset+499);if(error)throw error;rows.push(...data);if(data.length<500)return rows;}
}
export function createIndiaTracker({client=createSupabaseAdmin(),readQuotes=createIndiaQuotes(),readDaily=createIndiaDailyReader(),now=()=>new Date()}={}) {
 let running=null;
 const states=async()=>{if(!client)throw Error('Tracking storage unavailable');return allRows(client,'agi_india_portfolio_tracking');};
 return {
 async collect(portfolios){
  if(running)return running;
  running=(async()=>{
   const time=now(),s=session(time);let saved=await states();
   const selected=portfolios.filter(p=>INDIA_IDS.includes(p.id)&&p.market==='india');
   const pending=selected.filter(p=>!saved.some(x=>x.portfolio_id===p.id));
   if(pending.length&&s.date===INDIA_START&&s.open){
    const feed=await readQuotes([...new Set(pending.flatMap(p=>p.holdings.map(h=>h.symbol)))]);
    for(const p of pending){const baseline=makeBaseline(p,feed.quotes,now());if(!baseline)continue;
     const {error}=await client.from('agi_india_portfolio_tracking').insert({portfolio_id:p.id,baseline});if(error&&error.code!=='23505')throw error;
    }
    saved=await states();
   }
   if(!saved.length)return;
   const daily=await allRows(client,'agi_india_daily_prices');
   const marks=await allRows(client,'agi_india_portfolio_marks');
   for(const date of completedDates(time,INDIA_START)){
    const eligible=saved.filter(x=>session(new Date(x.baseline.startedAt)).date<=date);
    const pendingMarks=eligible.filter(x=>!marks.some(m=>m.portfolio_id===x.portfolio_id&&m.session_date===date&&m.valuation_method==='upstox_daily'));
    if(!pendingMarks.length)continue;
    const existing=daily.find(x=>x.session_date===date)?.prices||{};
    const instruments=[...new Map(pendingMarks.flatMap(x=>x.baseline.holdings).map(h=>[h.symbol,h])).values()];
    const missing=instruments.filter(h=>!(existing[h.symbol]?.price>0)||existing[h.symbol]?.instrumentKey!==h.instrumentKey);
    const prices={...existing,...(missing.length?await readDaily(date,missing):{})};
    const collectedAt=now().toISOString();
    if(missing.length){const {error}=await client.from('agi_india_daily_prices').upsert({session_date:date,prices,collected_at:collectedAt});if(error)throw error;}
    for(const row of pendingMarks){const nav=dailyValuation(row.baseline,prices);if(nav==null)continue;
     const {error}=await client.from('agi_india_portfolio_marks').upsert({portfolio_id:row.portfolio_id,session_date:date,marked_at:collectedAt,nav,valuation_method:'upstox_daily'});if(error)throw error;
    }
   }
  })();try{return await running;}finally{running=null;}
 },
 async read(portfolios){
  const time=now(),s=session(time),saved=await states();
  const daily=await allRows(client,'agi_india_daily_prices');
  const marks=(await allRows(client,'agi_india_portfolio_marks')).filter(x=>x.valuation_method==='upstox_daily').sort((a,b)=>a.session_date.localeCompare(b.session_date));
  return {startDate:INDIA_START,source:'Upstox daily candles',updateTime:'16:00 Asia/Kolkata',marketOpen:s.open,portfolios:portfolios.filter(p=>INDIA_IDS.includes(p.id)&&p.market==='india').map(p=>{
   const base=saved.find(x=>x.portfolio_id===p.id)?.baseline;
   const history=marks.filter(x=>x.portfolio_id===p.id).map(x=>({date:x.session_date,nav:x.nav,recordedAt:x.marked_at}));
   const last=history.at(-1),prior=history.at(-2);
   const positions=(base?.holdings||p.holdings).map(h=>{
    const points=base?daily.filter(x=>x.session_date>=session(new Date(base.startedAt)).date&&x.prices[h.symbol]?.instrumentKey===h.instrumentKey&&x.prices[h.symbol]?.price>0).map(x=>({date:x.session_date,price:x.prices[h.symbol].price})).sort((a,b)=>a.date.localeCompare(b.date)):[];
    const latest=points.at(-1),previous=points.at(-2);
    return {...h,price:latest?.price??null,priceDate:latest?.date??null,history:points,returnPct:latest&&h.basePrice?(latest.price/h.basePrice-1)*100:null,dayReturnPct:latest?(latest.price/(previous?.price||h.basePrice)-1)*100:null};
   });
   const due=completedDates(time,INDIA_START).at(-1);
   return convictionView(p,base,daily,{id:p.id,startDate:INDIA_START,startedAt:base?.startedAt||null,status:!base?(s.date<INDIA_START?'scheduled':s.date>INDIA_START?'start_missed':'awaiting_fresh_prices'):last?(due&&last.date<due?'daily_pending':'daily_recorded'):'awaiting_daily',nav:last?.nav??null,returnPct:last?last.nav-100:null,dayReturnPct:last?(last.nav/(prior?.nav||100)-1)*100:null,markedAt:last?.recordedAt||null,priceDate:last?.date||null,history,positions,cashWeight:base?.cashWeight??p.cashWeight??0});
  })};
 }
 };
}
let tracker;
function sharedTracker(){return tracker||=createIndiaTracker();}
export const readIndiaTracking=async portfolios=>sharedTracker().read(portfolios);
let running=false,lastDailyAttempt=0;
export function startIndiaPortfolioScheduler(){
 const tick=async()=>{const now=new Date(),s=session(now);const launch=s.date===INDIA_START&&s.open;const due=dailyDue(now);if(running||s.date<INDIA_START||(!launch&&!due)||(!launch&&Date.now()-lastDailyAttempt<300000))return;
  running=true;if(due)lastDailyAttempt=Date.now();try{const rows=await createPortfolioStore().list(); let all=rows; try {all=withGrowthMomentum(rows);} catch {console.warn('[india-portfolios] Private combination unavailable; public collection continues.');} await sharedTracker().collect(all);}catch{console.warn('[india-portfolios] Collection failed; retaining recorded evidence.');}finally{running=false;}};
 const timer=setInterval(tick,60000);timer.unref();tick();return timer;
}
