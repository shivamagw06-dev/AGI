/** Narrow authenticated market-data bridge. Never returns the broker access token. */
import {timingSafeEqual,randomUUID} from 'node:crypto';
import {growwRequest,resolveGrowwAccessToken} from '../providers/groww.js';
export function engineAuthorized(header,expected=process.env.INTELLIGENCE_ENGINE_TOKEN){
 const a=Buffer.from(String(header||'').replace(/^Bearer /i,''));const b=Buffer.from(String(expected||'').trim());
 return b.length>=16 && a.length===b.length && timingSafeEqual(a,b);
}
export function validateRequest(body){
 const {action,params={}}=body||{};
 if(action==='socket'){
  if(!/^U[A-Z2-7]{55}$/.test(params.socketKey||''))throw new Error('Invalid public socket key');
  return {socketKey:params.socketKey};
 }
 const allowed={quote:'/live-data/quote',expiries:'/historical/expiries',contracts:'/historical/contracts',candles:'/historical/candles'};
 if(!allowed[action])throw new Error('Unsupported read-only action');
 const p={exchange:'NSE'};
 if(action==='quote')return {path:allowed[action],params:{...p,segment:'CASH',trading_symbol:'NIFTY'}};
 if(action==='expiries'){
  if(!Number.isInteger(Number(params.year))||Number(params.year)<2020||Number(params.year)>new Date().getUTCFullYear()||!Number.isInteger(Number(params.month))||Number(params.month)<1||Number(params.month)>12)throw new Error('Invalid expiry range');
  return {path:allowed[action],params:{...p,underlying_symbol:'NIFTY',year:Number(params.year),month:Number(params.month)}};
 }
 if(action==='contracts'){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(params.expiry_date||''))throw new Error('Invalid expiry');
  return {path:allowed[action],params:{...p,underlying_symbol:'NIFTY',expiry_date:params.expiry_date}};
 }
 if(!/^NSE-NIFTY(?:-\d{2}[A-Za-z]{3}\d{2}-(?:\d+(?:\.\d+)?-(?:CE|PE)|FUT))?$/.test(params.groww_symbol||''))throw new Error('Invalid NIFTY symbol');
 const times=['start_time','end_time'].map(k=>{
  if(!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(params[k]||''))throw new Error('Invalid time');
  return Date.parse(params[k].replace(' ','T')+'+05:30');
 });
 if(times.some(v=>!Number.isFinite(v))||times[1]<times[0]||times[1]-times[0]>30*86400000)throw new Error('Invalid candle range');
 return {path:allowed[action],params:{...p,segment:params.groww_symbol==='NSE-NIFTY'?'CASH':'FNO',groww_symbol:params.groww_symbol,start_time:params.start_time,end_time:params.end_time,candle_interval:'1minute'}};
}
export async function handleGrowwEvidence(req,res){
 res.set('Cache-Control','no-store');
 if(!engineAuthorized(req.headers.authorization))return res.status(401).json({error:'SERVICE_AUTH_REQUIRED'});
 let input;try{input=validateRequest(req.body);}catch{return res.status(422).json({error:'INVALID_DATA_REQUEST'});}
 try{
  if(input.path)return res.json(await growwRequest(input.path,input.params));
  const token=await resolveGrowwAccessToken();
  const r=await fetch('https://api.groww.in/v1/api/apex/v1/socket/token/create/',{method:'POST',redirect:'error',signal:AbortSignal.timeout(20000),headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json','X-API-VERSION':'1.0','x-request-id':randomUUID(),'x-client-id':'growwapi','x-client-platform':'growwapi-python-client','x-client-platform-version':'1.5.0'},body:JSON.stringify(input)});
  const body=await r.json();
  const payload=body.payload||body;
  if(!r.ok||body.status==='FAILURE'||typeof payload.token!=='string'||!payload.subscriptionId)throw new Error('Socket authorization failed');
  // Scoped, short-lived socket authorization only; not a trading API token.
  return res.json({token:payload.token,subscriptionId:payload.subscriptionId});
 }catch{return res.status(503).json({error:'GROWW_DATA_UNAVAILABLE'});}
}
