import { Router } from 'express';
import {publicWebsiteStats} from '../services/publicWebsiteStats.js';
import rateLimit from 'express-rate-limit';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
export default function websiteAnalytics(engineFetch) {
 const router=Router();
 const cache=new Map();
 router.get('/public-summary',rateLimit({windowMs:60000,max:60,standardHeaders:true,legacyHeaders:false}),async(req,res)=>{
  const days=Number(req.query.days||7);if(![1,7,30,90].includes(days))return res.status(400).json({error:'Invalid range'});
  try {
   const hit=cache.get(days);if(hit&&Date.now()-hit.at<60000)return res.json(hit.value);
   const r=await engineFetch(`/v1/website-analytics/summary?days=${days}`,{timeoutMs:20000});
   if(r.status!==200||!r.data?.ok)return res.status(503).json({error:'Statistics are temporarily unavailable.'});
   const value=publicWebsiteStats(r.data);cache.set(days,{at:Date.now(),value});res.set('Cache-Control','public, max-age=60');return res.json(value);
  }catch{return res.status(503).json({error:'Statistics are temporarily unavailable. Please refresh shortly.'});}
 });
 const allowed=new Set(['https://agarwalglobalinvestments.com','https://www.agarwalglobalinvestments.com']);
 router.post('/event',rateLimit({windowMs:60000,max:90,standardHeaders:true,legacyHeaders:false}),async(req,res)=>{
  if(!allowed.has(req.get('origin')))return res.status(403).json({error:'Origin not allowed'});
  if(/bot|crawler|spider|headless/i.test(req.get('user-agent')||'')||req.get('dnt')==='1'||req.get('sec-gpc')==='1')return res.status(204).end();
  if(JSON.stringify(req.body||{}).length>2000)return res.status(413).json({error:'Event too large'});
  try { const r=await engineFetch('/v1/website-analytics/event',{method:'POST',body:req.body,timeoutMs:12000});res.status(r.ok?202:r.status).json(r.ok?{ok:true}:{error:'Analytics event rejected'}); }
  catch(e){res.status(e.status===400?400:503).json({error:'Analytics event unavailable'});}
 });
 router.get('/summary',requireStrategyLabAdmin,async(req,res)=>{
  const days=Number(req.query.days||7);if(![1,7,30,90].includes(days))return res.status(400).json({error:'Invalid range'});
  try {res.set('Cache-Control','no-store');const r=await engineFetch(`/v1/website-analytics/summary?days=${days}`,{timeoutMs:20000});res.status(r.status).json(r.data);}
  catch {res.status(503).json({error:'Analytics unavailable. Try a shorter range or refresh shortly.'});}
 });
 return router;
}
