import {budgetedMarketFetch} from '../lib/marketDataBudget.js';
import {resolveUpstoxAccessToken} from '../providers/upstox.js';
import {validDailyCandle} from './indiaPortfolioDaily.js';
import {nseSession,istDateKey} from './liveAlphaSession.js';
export const RETROSPECTIVE_START='2026-09-15';
export function retrospectiveDates(now=new Date()){
 const dates=[];
 for(let at=Date.parse(RETROSPECTIVE_START+'T12:00:00+05:30');at<=now.getTime();at+=86400000){
  const s=nseSession(at);if(s&&now.getTime()>=Math.max(s.end,Date.parse(s.date+'T16:00:00+05:30')))dates.push(s.date);
 }
 return dates;
}
export function createFactorRangeReader({fetcher=budgetedMarketFetch,token=()=>process.env.UPSTOX_ANALYTICS_TOKEN||resolveUpstoxAccessToken().token}={}){
 return async(h,end)=>{
  const credential=token();if(!credential)throw Error('Upstox history credentials unavailable');
  const r=await fetcher('upstox',`https://api.upstox.com/v3/historical-candle/${encodeURIComponent(h.instrumentKey)}/days/1/${end}/${RETROSPECTIVE_START}`,{headers:{Accept:'application/json',Authorization:`Bearer ${credential}`},redirect:'error',signal:AbortSignal.timeout(15000)});
  if(!r.ok)throw Error('Historical price collection pending');
  const body=await r.json();if(body.status!=='success'||!Array.isArray(body.data?.candles))throw Error('Historical price collection pending');
  const bars={};
  for(const c of body.data.candles){const date=istDateKey(c?.[0]);if(date>=RETROSPECTIVE_START&&date<=end&&validDailyCandle(c,date)&&nseSession(c[0])){
   if(bars[date]!=null&&bars[date]!==c[4])throw Error('Conflicting historical closes');bars[date]=c[4];
  }}
  return {instrumentKey:h.instrumentKey,bars};
 };
}
export async function collectRetrospective(document,candidates,snapshot,readRange,now=new Date(),limit=5){
 const dates=retrospectiveDates(now),end=dates.at(-1);if(!end||candidates.length!==50)return null;
 const old=document.factorRetrospective;
 const saved=old?.snapshot===snapshot&&old.startDate===RETROSPECTIVE_START?structuredClone(old):{snapshot,startDate:RETROSPECTIVE_START,securities:{}};
 let count=0;
 for(const h of candidates.slice(0,25)){
  const oldSeries=saved.securities[h.symbol],known=oldSeries?.instrumentKey===h.instrumentKey?oldSeries:null;
  const complete=known&&dates.every(d=>known.bars?.[d]>0);
  if(complete||known?.attemptedAt&&now.getTime()-Date.parse(known.attemptedAt)<3600000)continue;
  if(count++>=limit)break;
  try{const result=await readRange(h,end);if(result.instrumentKey!==h.instrumentKey)throw Error('Wrong instrument');
   saved.securities[h.symbol]={instrumentKey:h.instrumentKey,attemptedAt:now.toISOString(),source:'Upstox daily raw close',bars:{...result.bars,...known?.bars}};
  }catch{saved.securities[h.symbol]={...known,instrumentKey:h.instrumentKey,attemptedAt:now.toISOString(),bars:known?.bars||{}};}
 }
 return count? saved:null;
}
export function retrospectiveView(saved,candidates,snapshot,now=new Date()){
 const dates=retrospectiveDates(now),main=candidates.slice(0,25),valid=saved?.snapshot===snapshot&&saved.startDate===RETROSPECTIVE_START;
 const get=(h,d)=>valid&&saved.securities?.[h.symbol]?.instrumentKey===h.instrumentKey?saved.securities[h.symbol].bars?.[d]:null;
 const missingBaseline=main.filter(h=>!(get(h,RETROSPECTIVE_START)>0)).map(h=>h.symbol);
 const missingDates=dates.filter(d=>main.some(h=>!(get(h,d)>0)));
 const history=missingBaseline.length?[]:dates.filter(d=>!missingDates.includes(d)).map(date=>({date,value:main.reduce((sum,h)=>sum+4*get(h,date)/get(h,RETROSPECTIVE_START),0)}));
 let peak=100,maxDrawdown=0;for(const p of history){peak=Math.max(peak,p.value);maxDrawdown=Math.max(maxDrawdown,(1-p.value/peak)*100);}
 const last=history.at(-1);
 return {startDate:RETROSPECTIVE_START,selectionDate:'2026-10-11',priceDate:last?.date||null,returnPct:last?last.value-100:null,maxDrawdown:history.length?maxDrawdown:null,history:history.length?dates.map(date=>history.find(p=>p.date===date)||{date,value:null}):[],missingBaseline,missingDates,
  status:!missingBaseline.length&&!missingDates.length?'complete':'collecting',expectedThrough:dates.at(-1)||null,
  holdings:main.map(h=>({symbol:h.symbol,weight:4,basePrice:get(h,RETROSPECTIVE_START)||null,history:dates.filter(d=>get(h,d)>0).map(date=>({date,price:get(h,date)}))}))};
}
