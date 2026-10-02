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
export const INDIA_IDS = ['in-momentum','in-growth','in-value','in-quality','in-all-weather'];
export function session(now = new Date()) {
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).map(x=>[x.type,x.value]));
 const minutes=+p.hour*60 + +p.minute;
 return {date:`${p.year}-${p.month}-${p.day}`,open:!['Sat','Sun'].includes(p.weekday)&&minutes>=555&&minutes<930};
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
 if(p.holdings.some(h=>!fresh(quotes[h.symbol],now)))return null;
 const total=p.holdings.reduce((sum,h)=>sum+h.weight,0)+(p.cashWeight||0);
 return {startedAt:now.toISOString(),revision:p.revision,cashWeight:(p.cashWeight||0)/total*100,holdings:p.holdings.map(h=>({...h,weight:h.weight/total*100,basePrice:quotes[h.symbol].price,baseTime:quotes[h.symbol].time,instrumentKey:quotes[h.symbol].instrumentKey}))};
}
export function valueBaseline(base,quotes,now=new Date()) {
 const positions=base.holdings.map(h=>({...h,price:quotes[h.symbol]?.price??null,quoteTime:quotes[h.symbol]?.time??null,fresh:fresh(quotes[h.symbol],now)}));
 const complete=positions.every(h=>h.fresh&&h.price>0&&quotes[h.symbol].instrumentKey===h.instrumentKey);
 return {positions,complete,nav:complete?positions.reduce((sum,h)=>sum+h.weight*h.price/h.basePrice,base.cashWeight||0):null};
}
export function createIndiaTracker({client=createSupabaseAdmin(), readQuotes=createIndiaQuotes(), now=()=>new Date()}={}) {
 const table=()=>{if(!client)throw Error('Tracking storage unavailable');return client.from('agi_india_portfolio_tracking');};
 let inFlight=null;
 return {async read(portfolios){
  if(inFlight)return inFlight;
  inFlight=(async()=>{
   let time=now();const s=session(time);const selected=portfolios.filter(p=>INDIA_IDS.includes(p.id)&&p.market==='india');
   if(!selected.length)return {startDate:INDIA_START,portfolios:[],source:'Upstox'};
   const {data:states,error}=await table().select('*');if(error)throw error;
   const {data:marks,error:markError}=await client.from('agi_india_portfolio_marks').select('*').order('session_date');if(markError)throw markError;
   const map=new Map(states.map(x=>[x.portfolio_id,x]));
   const symbols=[...new Set(selected.flatMap(p=>[...p.holdings,...(map.get(p.id)?.baseline.holdings||[])].map(h=>h.symbol)))];
   let feed={quotes:{},fetchedAt:null},quoteError=null;try{feed=await readQuotes(symbols);}catch{quoteError='Upstox prices temporarily unavailable';}
   time=now();
   const result=[];
   for(const p of selected){let state=map.get(p.id);
    if(!state){const baseline=makeBaseline(p,feed.quotes,time);if(baseline){
      const {data:created,error:insertError}=await table().insert({portfolio_id:p.id,baseline}).select('*').single();
      if(insertError?.code==='23505'){const {data,error}=await table().select('*').eq('portfolio_id',p.id).single();if(error)throw error;state=data;}
      else if(insertError)throw insertError;else state=created;
    }}
    const valuation=state?valueBaseline(state.baseline,feed.quotes,time):null;
    const history=marks.filter(m=>m.portfolio_id===p.id);
    const lastMark=history.at(-1)||null;
    if(state&&valuation.complete&&s.open){const {error}=await client.from('agi_india_portfolio_marks').upsert({portfolio_id:p.id,session_date:s.date,marked_at:time.toISOString(),nav:valuation.nav});if(error)throw error;}
    const nav=valuation?.complete&&s.open?valuation.nav:lastMark?.nav??null;
    result.push({id:p.id,status:!state?(s.date<INDIA_START?'scheduled':s.date>INDIA_START?'start_missed':'awaiting_fresh_prices'):valuation.complete&&s.open?'live':'stale',startDate:INDIA_START,startedAt:state?.baseline.startedAt||null,returnPct:nav==null?null:nav-100,nav,markedAt:valuation?.complete&&s.open?time.toISOString():lastMark?.marked_at||null,history:history.map(m=>({date:m.session_date,nav:m.nav})),cashWeight:state?.baseline.cashWeight??p.cashWeight??0,positions:valuation?.positions||p.holdings.map(h=>({...h,price:feed.quotes[h.symbol]?.price??null,quoteTime:feed.quotes[h.symbol]?.time??null})),allocationChanged:!!state&&state.baseline.revision!==p.revision});
   }
   return {startDate:INDIA_START,marketOpen:s.open,source:'Upstox',fetchedAt:feed.fetchedAt,quoteError,portfolios:result};
  })();try{return await inFlight;}finally{inFlight=null;}
 }};
}

let tracker;
export const readIndiaTracking=async portfolios=>{tracker||=createIndiaTracker();return tracker.read(portfolios);};
let running=false;
export function startIndiaPortfolioScheduler(){
 const tick=async()=>{if(running||!session().open||session().date<INDIA_START)return;running=true;try{await readIndiaTracking(await createPortfolioStore().list());}catch{console.warn('[india-portfolios] Tracking refresh failed; retaining recorded evidence.');}finally{running=false;}};
 const timer=setInterval(tick,60000);timer.unref();tick();return timer;
}
