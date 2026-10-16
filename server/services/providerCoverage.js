import { budgetedMarketFetch } from '../lib/marketDataBudget.js';
/** Read-only broker probes. No order, account, or position endpoints are called. */
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { growwRequest, getHistoricalCandleRange } from '../providers/groww.js';
import { resolveUpstoxAccessToken } from '../providers/upstox.js';

const catalog = [
 ['spot_quote','Spot quote / depth','Live snapshot; after-market quotes are not live freshness proof'],
 ['option_chain','Option chain / IV / Greeks','Sample one expiry; field presence is checked separately'],
 ['history','Spot one-minute history','Seven-day sample, not proof of full-year completeness'],
 ['expiries','Historical expiry discovery','Required before requesting expired contracts'],
 ['contracts','Expired option contracts','Use provider-issued identifiers'],
 ['option_history','Expired option one-minute history','One contract sample; no historical bid/ask reconstruction'],
 ['futures_contracts','Futures contract discovery','Groww discovery shares the contracts endpoint'],
 ['futures_history','Futures one-minute history','One expired contract sample'],
 ['stream','Streaming price and depth','Needs an observed streaming session; REST cannot verify streaming'],
 ['constituents','All 50 Nifty constituents','Needs dated membership, mapping and full-universe coverage'],
 ['news','News with publication/receipt times','No Groww news endpoint verified in reviewed documentation'],
 ['calendar','Reviewed event calendar','Trading holidays alone do not constitute economic-event review'],
 ['margins','Basket margins and charges','Requires a defined basket; not inferred from quotes'],
 ['retention','Long-term live evidence','Must audit recorder storage separately'],
];
const root=()=>process.env.PROVIDER_COVERAGE_DIR || path.join(os.tmpdir(),'agi-provider-coverage');
let report=null, running=null;
export function evidence(rows) {
 if (!Array.isArray(rows) || !rows.length) return {status:'empty',count:0};
 let invalid=0; const times=[];
 for (const r of rows) {
  const at=typeof r[0]==='number'?r[0]*1000:Date.parse(r[0]);
  const values=r.slice(1,5).map(Number);
  if (!Number.isFinite(at)||r.length<5||r.slice(1,5).some(v=>v==null)||values.some(v=>!Number.isFinite(v)||v<=0)||values[1]<Math.max(values[0],values[2],values[3])||values[2]>Math.min(values[0],values[1],values[3])) invalid++;
  else times.push(at);
 }
 return {status:invalid?'invalid':'passed',count:rows.length,invalid,first:times.length?new Date(Math.min(...times)).toISOString():null,last:times.length?new Date(Math.max(...times)).toISOString():null,has_volume:rows.some(r=>r[5]!=null),has_oi:rows.some(r=>r[6]!=null)};
}
async function up(pathname,params={}) {
 const {token}=resolveUpstoxAccessToken();
 if (!token) throw new Error('AUTH_NOT_CONFIGURED');
 const url=new URL(`https://api.upstox.com/v2${pathname}`);
 Object.entries(params).forEach(([k,v])=>url.searchParams.set(k,v));
 const res=await budgetedMarketFetch('upstox',url,{headers:{Authorization:`Bearer ${token}`,Accept:'application/json'},signal:AbortSignal.timeout(15000),redirect:'error'});
 if (!res.ok) throw new Error(`HTTP_${res.status}`);
 const body=await res.json();
 if(body.status!=='success')throw new Error('PROVIDER_REJECTED');
 return body.data;
}
export async function coverageStatus() {
 if (!report) {try {report=JSON.parse(await fs.readFile(path.join(root(),'report.json'),'utf8')); if (!report.finished_at && !running) { report.error='AUDIT_INTERRUPTED_BY_RESTART'; }}catch{}}
 return {ok:true,running:!!running,report,storage:process.env.PROVIDER_COVERAGE_DIR?'Configured directory — durability depends on its mounted disk':'Temporary storage — may be lost on redeploy',catalog:catalog.map(([id,label,note])=>({id,label,note})),scope:'NIFTY data capability samples; no orders or automatic provider switching'};
}
async function save() {
 await fs.mkdir(root(),{recursive:true,mode:0o700});
 const tmp=path.join(root(),'report.tmp');
 await fs.writeFile(tmp,JSON.stringify(report),{mode:0o600});await fs.rename(tmp,path.join(root(),'report.json'));
}
export function startCoverageAudit() {
 if(running)return {ok:true,started:false};
 if(report?.finished_at && Date.now()-Date.parse(report.finished_at)<300000)return {ok:true,started:false,cooldown:true};
 running=run().catch(async()=>{if(report){report.error='AUDIT_INTERRUPTED';report.finished_at=new Date().toISOString();try{await save();}catch{}}}).finally(()=>{running=null;});
 return {ok:true,started:true};
}
async function run() {
 const now=new Date(), end=new Date(now.getTime()-86400000), start=new Date(end.getTime()-7*86400000), previous=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()-1,1));
 const day=d=>d.toISOString().slice(0,10);
 report={started_at:now.toISOString(),finished_at:null,providers:{groww:{},upstox:{}},sample_window:{from:day(start),to:day(end)}};
 for(const provider of ['groww','upstox'])for(const [id]of catalog)report.providers[provider][id]={status:'not_tested',recorded:false,used_by_agents:provider==='upstox'&&['spot_quote','option_chain','stream','news'].includes(id)?'Existing paper-engine integration; runtime health shown separately':'Not connected by this audit'};
 await save();
 async function probe(provider,id,fn,shape) {
  const row=report.providers[provider][id];row.status='running';await save();
  try {
   const data=await fn();const summary=shape(data);
   Object.assign(row,summary,{checked_at:new Date().toISOString()});
   if(summary.status==='passed') {
    await fs.writeFile(path.join(root(),`${provider}-${id}.json`),JSON.stringify({provider,id,received_at:row.checked_at,data}),{mode:0o600});row.recorded=true;
   }
   return data;
  }catch(e){row.status='failed';row.error=/HTTP_\d{3}|AUTH_NOT_CONFIGURED/.exec(e.message)?.[0]||'PROVIDER_REQUEST_OR_STORAGE_FAILED';row.checked_at=new Date().toISOString();}
  finally{await save();}
 }
 const list=d=>({status:Array.isArray(d)&&d.length?'passed':'empty',count:Array.isArray(d)?d.length:0});
 const quote=d=>({status:Number(d?.last_price??d?.lastPrice)>0?'passed':'invalid',fields:Object.keys(d||{}),has_bid_ask:Number(d?.bid_price)>0&&Number(d?.offer_price)>0});
 const gq=await probe('groww','spot_quote',()=>growwRequest('/live-data/quote',{exchange:'NSE',segment:'CASH',trading_symbol:'NIFTY'}),quote);
 await probe('groww','history',()=>getHistoricalCandleRange('NSE','CASH','NIFTY',start,end,1),evidence);
 const ge=await probe('groww','expiries',async()=> (await growwRequest('/historical/expiries',{exchange:'NSE',underlying_symbol:'NIFTY',year:previous.getUTCFullYear(),month:previous.getUTCMonth()+1}))?.expiries,list);
 const expiry=ge?.filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&x<day(now)).sort().at(-1);
 if(expiry){
  const gc=await probe('groww','contracts',async()=>(await growwRequest('/historical/contracts',{exchange:'NSE',underlying_symbol:'NIFTY',expiry_date:expiry}))?.contracts,list);
  const opt=gc?.filter(x=>/-\d+-CE$/.test(x)).sort((a,b)=>Math.abs(Number(a.split('-').at(-2))-Number(gq?.last_price||25000))-Math.abs(Number(b.split('-').at(-2))-Number(gq?.last_price||25000)))[0];
  const histStart=new Date(`${expiry}T00:00:00+05:30`);histStart.setDate(histStart.getDate()-6);
  const histEnd=new Date(`${expiry}T15:30:00+05:30`);
  if(opt)await probe('groww','option_history',()=>getHistoricalCandleRange('NSE','FNO',opt,histStart,histEnd,1),d=>({...evidence(d),instrument:opt}));
  const futures=gc?.filter(x=>x.endsWith('-FUT'))||[];
  await probe('groww','futures_contracts',async()=>futures,list);
  if(futures[0])await probe('groww','futures_history',()=>getHistoricalCandleRange('NSE','FNO',futures[0],histStart,histEnd,1),d=>({...evidence(d),instrument:futures[0]}));
 }
 const current=await growwRequest('/historical/expiries',{exchange:'NSE',underlying_symbol:'NIFTY',year:now.getUTCFullYear(),month:now.getUTCMonth()+1}).catch(()=>null);
 const next=current?.expiries?.filter(x=>x>=day(now)).sort()[0];
 if(next)await probe('groww','option_chain',()=>growwRequest(`/option-chain/exchange/NSE/underlying/NIFTY`,{expiry_date:next}),d=>({status:Object.keys(d?.strikes||{}).length?'passed':'empty',strikes:Object.keys(d?.strikes||{}).length,has_greeks:Object.values(d?.strikes||{}).some(x=>x.CE?.greeks?.delta!=null)}));
 await probe('upstox','spot_quote',()=>up('/market-quote/quotes',{instrument_key:'NSE_INDEX|Nifty 50'}),d=>({status:Object.values(d||{}).some(x=>x.last_price>0)?'passed':'invalid',instruments:Object.keys(d||{})}));
 await probe('upstox','history',async()=> (await up(`/historical-candle/${encodeURIComponent('NSE_INDEX|Nifty 50')}/1minute/${day(end)}/${day(start)}`))?.candles,evidence);
 const ue=await probe('upstox','expiries',()=>up('/expired-instruments/expiries',{instrument_key:'NSE_INDEX|Nifty 50'}),list);
 const ux=ue?.filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&x<day(now)).sort().at(-1);
 if(ux){
  const uc=await probe('upstox','contracts',()=>up('/expired-instruments/option/contract',{instrument_key:'NSE_INDEX|Nifty 50',expiry_date:ux}),list);
  const uf=await probe('upstox','futures_contracts',()=>up('/expired-instruments/future/contract',{instrument_key:'NSE_INDEX|Nifty 50',expiry_date:ux}),list);
  const from=new Date(`${ux}T00:00:00Z`);from.setUTCDate(from.getUTCDate()-6);
  for(const [id,contract]of [['option_history',uc?.filter(x=>x.instrument_type==='CE').sort((a,b)=>Math.abs(a.strike_price-25000)-Math.abs(b.strike_price-25000))[0]],['futures_history',uf?.[0]]])if(contract?.instrument_key)await probe('upstox',id,async()=> (await up(`/expired-instruments/historical-candle/${encodeURIComponent(contract.instrument_key)}/1minute/${ux}/${day(from)}`))?.candles,d=>({...evidence(d),instrument:contract.instrument_key}));
 }
 const active=await up('/option/contract',{instrument_key:'NSE_INDEX|Nifty 50'}).catch(()=>null);
 const activeExpiry=active?.map(x=>x.expiry).filter(x=>x>=day(now)).sort()[0];
 if(activeExpiry)await probe('upstox','option_chain',()=>up('/option/chain',{instrument_key:'NSE_INDEX|Nifty 50',expiry_date:activeExpiry}),d=>({...list(d),has_greeks:d?.some(x=>x.call_options?.option_greeks?.delta!=null)}));
 await probe('upstox','news',()=>up('/news',{category:'instrument_keys',instrument_keys:'NSE_EQ|INE002A01018',page_size:1}),d=>({status:Object.values(d||{}).some(x=>Array.isArray(x)&&x.length)?'passed':'empty',scope:'Reliance sample only'}));
 report.finished_at=new Date().toISOString();await save();
}
