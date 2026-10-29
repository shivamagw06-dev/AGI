import { Router } from 'express';
import { createPlusService, membershipActive, plusAdmin } from '../services/agiPlus.js';
import { getPrivateCapitalResearch } from '../services/privateCapitalResearch.js';
export default function createPrivateCapitalRouter({billing=createPlusService(),getSnapshot=getPrivateCapitalResearch}={}){
 const router=Router();
 router.use((_req,res,next)=>{res.set('Cache-Control','private, no-store');next();});
 router.get('/',async(req,res)=>{
  const token=String(req.get('authorization')||'').match(/^Bearer\s+(.+)$/i)?.[1];
  if(!token)return res.status(401).json({error:'Sign in to view private-capital research.'});
  let user;try{user=await billing.user(token);}catch{return res.status(401).json({error:'Your session could not be verified. Please sign in again.'});}
  try{
   if(!plusAdmin(user)){
    const [config,membership]=await Promise.all([billing.config(),billing.membership(user.id)]);
    if(typeof config?.enabled!=='boolean')throw Error('Access check unavailable');
    if(config.enabled&&!membershipActive(membership))return res.status(402).json({error:'An active AGI Plus membership is required.'});
   }
   return res.json(getSnapshot());
  }catch{return res.status(503).json({error:'Private-capital research is temporarily unavailable. Please retry.'});}
 });
 return router;
}
