import { resolveUpstoxAccessToken } from '../providers/upstox.js';
import { nseSession, istDateKey } from './liveAlphaSession.js';

export function dailyDue(now = new Date()) {
 const date=istDateKey(now), market=nseSession(now);
 return !!market && now.getTime() >= Math.max(Date.parse(`${date}T16:00:00+05:30`),market.end);
}
export function validDailyCandle(candle,date) {
 if(!Array.isArray(candle)||!Number.isFinite(Date.parse(candle[0]))||istDateKey(candle[0])!==date)return false;
 const [o,h,l,c]=candle.slice(1,5);
 return [o,h,l,c].every(x=>typeof x==='number'&&Number.isFinite(x)&&x>0)&&h>=Math.max(o,c)&&l<=Math.min(o,c)&&h>=l;
}
// At most four provider calls per second; successful prices are persisted and not fetched again.
export function createIndiaDailyReader({fetcher=fetch,token=()=>process.env.UPSTOX_ANALYTICS_TOKEN||resolveUpstoxAccessToken().token,now=()=>new Date(),pause=ms=>new Promise(r=>setTimeout(r,ms))}={}) {
 return async(date,instruments)=>{
  const credential=token();if(!credential)throw Error('Upstox credentials unavailable');
  const quotes={};
  for(const [i,h] of instruments.entries()){
   if(i)await pause(300);
   const key=encodeURIComponent(h.instrumentKey), today=istDateKey(now());
   const path=date===today?`intraday/${key}/days/1`:`${key}/days/1/${date}/${date}`;
   try{
    const response=await fetcher(`https://api.upstox.com/v3/historical-candle/${path}`,{headers:{Accept:'application/json',Authorization:`Bearer ${credential}`},redirect:'error',signal:AbortSignal.timeout(15000)});
    if([401,403,429].includes(response.status))break;
    if(!response.ok)continue;
    const body=await response.json();if(body.status!=='success')continue;
    const c=body.data?.candles?.find(x=>validDailyCandle(x,date));
    if(c)quotes[h.symbol]={price:c[4],time:c[0],instrumentKey:h.instrumentKey};
   }catch{/* Missing evidence stays missing; the scheduler retries later. */}
  }
  return quotes;
 };
}
export function dailyValuation(base,quotes){
 if(base.holdings.some(h=>!(quotes[h.symbol]?.price>0)||quotes[h.symbol]?.instrumentKey!==h.instrumentKey))return null;
 return base.holdings.reduce((sum,h)=>sum+h.weight*quotes[h.symbol].price/h.basePrice,base.cashWeight||0);
}
export function completedDates(now,start){
 const dates=[];
 for(let i=6;i>=0;i--){const at=new Date(now.getTime()-i*86400000),date=istDateKey(at);if(date>=start&&dailyDue(at))dates.push(date);}
 return dates;
}
