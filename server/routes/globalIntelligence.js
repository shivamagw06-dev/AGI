import express from 'express';
import rateLimit from 'express-rate-limit';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import { database, result, snapshot, saveAsset, reviewEvent } from '../services/globalIntelligence/store.js';
import { collectEvents } from '../services/globalIntelligence/collector.js';

export async function verifiedUser(req) {
  const token=String(req.headers.authorization||'').match(/^Bearer\s+(\S+)$/i)?.[1];
  if(!token)return null;
  const {data,error}=await database().auth.getUser(token);
  return !error && data?.user && !data.user.is_anonymous && data.user.email_confirmed_at ? data.user : null;
}
export default function createGlobalIntelligenceRouter(deps={}) {
  const router=express.Router();
  const db=deps.database||database, read=deps.snapshot||snapshot, auth=deps.verifiedUser||verifiedUser;
  const admin=deps.requireAdmin||requireStrategyLabAdmin;
  router.use(express.json({limit:'32kb'}));
  router.use(rateLimit({windowMs:60000,max:90,standardHeaders:true,legacyHeaders:false}));
  const handle=fn=>async(req,res)=>{try{await fn(req,res);}catch(e){
    const status=e.status||(e.code==='40001'?409:e.code==='P0002'?404:e.code==='23505'?409:503);
    res.status(status).json({error:status===503?'Global Intelligence is temporarily unavailable. Please retry.':e.message});
  }};
  const validate=fn=>{try{return fn();}catch(e){e.status=400;throw e;}};
  router.get('/snapshot',handle(async(req,res)=>res.set('Cache-Control','public, max-age=60').json(await read())));
  router.get('/admin',admin,handle(async(req,res)=>res.set('Cache-Control','no-store').json(await read({admin:true}))));
  router.post('/collect',admin,handle(async(req,res)=>res.json(await (deps.collectEvents||collectEvents)())));
  router.post('/assets',admin,handle(async(req,res)=>{
    const {validateAsset}=await import('../services/globalIntelligence/model.js'); validate(()=>validateAsset(req.body));
    res.status(201).json(await saveAsset(req.body,req.strategyLabActor.id));
  }));
  router.delete('/assets/:id',admin,handle(async(req,res)=>{
    if(!/^[a-f0-9-]{36}$/i.test(req.params.id))return res.status(400).json({error:'Invalid asset ID.'});
    await result(db().from('gi_assets').update({active:false}).eq('id',req.params.id));res.json({ok:true});
  }));
  router.post('/events/:id/review',admin,handle(async(req,res)=>{
    const {validateReview}=await import('../services/globalIntelligence/model.js');validate(()=>validateReview(req.body));
    res.json(await reviewEvent(req.params.id,req.body,req.strategyLabActor.id));
  }));
  router.use('/watchlist',handle(async(req,res)=>{
    const user=await auth(req);if(!user)return res.status(401).json({error:'Sign in to save your watchlist.'});
    res.set('Cache-Control','no-store');
    if(req.method==='GET'){
      const rows=await result(db().from('gi_watchlists').select('symbols,updated_at').eq('user_id',user.id).maybeSingle());
      return res.json(rows||{symbols:[]});
    }
    if(req.method!=='PUT')return res.status(405).json({error:'Method not allowed.'});
    if(!Array.isArray(req.body.symbols)||req.body.symbols.length>100||req.body.symbols.some(x=>typeof x!=='string'))return res.status(400).json({error:'Choose up to 100 listed companies.'});
    const symbols=[...new Set(req.body.symbols)];
    const assets=await result(db().from('gi_assets').select('symbol').eq('active',true));
    if(symbols.some(s=>!assets.some(a=>a.symbol===s)))return res.status(400).json({error:'Watchlists support companies in the current asset directory.'});
    await result(db().from('gi_watchlists').upsert({user_id:user.id,symbols,updated_at:new Date().toISOString()}));
    res.json({symbols});
  }));
  return router;
}
