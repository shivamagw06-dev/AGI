import express from 'express';
import rateLimit from 'express-rate-limit';
import { requireStrategyLabAdmin } from '../services/strategyLabAdminAuth.js';
import { database, result, snapshot, saveAsset, reviewEvent } from '../services/globalIntelligence/store.js';
import {archive,documents,eventHistory,buildInbox,validatePreferences,DEFAULT_PREFERENCES} from '../services/globalIntelligence/workflows.js';
import {collectDocuments} from '../services/globalIntelligence/documents.js';
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
  router.get('/archive',handle(async(req,res)=>{
    const page=Number(req.query.page||1);if(!Number.isInteger(page)||page<1||page>100)return res.status(400).json({error:'Choose a page from 1 to 100.'});
    res.set('Cache-Control','public, max-age=60').json(await (deps.archive||archive)({page,search:String(req.query.search||'').slice(0,100)}));
  }));
  router.get('/documents',handle(async(req,res)=>res.set('Cache-Control','public, max-age=300').json(await (deps.documents||documents)())));
  router.get('/events/:id/history',handle(async(req,res)=>res.set('Cache-Control','public, max-age=60').json(await (deps.eventHistory||eventHistory)(req.params.id))));
  router.get('/admin/documents',admin,handle(async(req,res)=>res.set('Cache-Control','no-store').json(await (deps.documents||documents)({admin:true}))));
  router.post('/admin/documents/collect',admin,handle(async(req,res)=>{
    // Seven bounded network checks can exceed a request timeout; run in background.
    void (deps.collectDocuments||collectDocuments)({force:true}).catch(e=>console.warn('[gi-documents]',e.message));
    res.status(202).json({message:'Document checks requested. Refresh this panel shortly; an active ten-minute collection lease can defer a duplicate request.'});
  }));
  router.use('/alerts',handle(async(req,res)=>{
    const user=await auth(req);if(!user)return res.status(401).json({error:'Sign in to manage your private alerts.'});
    res.set('Cache-Control','no-store');
    if(req.method==='GET'&&req.path==='/'){
      const loadedAt=new Date().toISOString();
      const prefs=await result(db().from('gi_alert_preferences').select('enabled,observations,assessments,documents,enabled_at,last_read_at').eq('user_id',user.id).maybeSingle())||DEFAULT_PREFERENCES;
      if(!prefs.enabled)return res.json({preferences:prefs,items:[],loaded_at:loadedAt});
      const [watch,feed,docs]=await Promise.all([result(db().from('gi_watchlists').select('symbols').eq('user_id',user.id).maybeSingle()),read(),(deps.documents||documents)()]);
      return res.json({preferences:prefs,items:buildInbox({preferences:prefs,watch:watch?.symbols||[],events:feed.events,...docs}),loaded_at:loadedAt});
    }
    if(req.method==='POST'&&req.path==='/'){
      const p=validate(()=>validatePreferences(req.body));
      const preferences=await result(db().rpc('gi_set_alert_preferences',{p_user:user.id,p_enabled:p.enabled,p_observations:p.observations,p_assessments:p.assessments,p_documents:p.documents}));
      return res.json({preferences});
    }
    if(req.method==='POST'&&req.path==='/read'){
      // Read only through the batch the client saw; never mark later arrivals read.
      const through=Date.parse(req.body.through);
      if(!Number.isFinite(through)||through>Date.now()||through<Date.now()-3600000)return res.status(400).json({error:'Refresh your inbox before marking it read.'});
      await result(db().from('gi_alert_preferences').update({last_read_at:new Date(through).toISOString()}).eq('user_id',user.id));
      return res.json({ok:true});
    }
    res.status(405).json({error:'Method not allowed.'});
  }));
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
    if(req.method!=='POST')return res.status(405).json({error:'Method not allowed.'});
    if(!Array.isArray(req.body.symbols)||req.body.symbols.length>100||req.body.symbols.some(x=>typeof x!=='string'))return res.status(400).json({error:'Choose up to 100 listed companies.'});
    const symbols=[...new Set(req.body.symbols)];
    const assets=await result(db().from('gi_assets').select('symbol').eq('active',true));
    if(symbols.some(s=>!assets.some(a=>a.symbol===s)))return res.status(400).json({error:'Watchlists support companies in the current asset directory.'});
    await result(db().from('gi_watchlists').upsert({user_id:user.id,symbols,updated_at:new Date().toISOString()}));
    res.json({symbols});
  }));
  return router;
}
