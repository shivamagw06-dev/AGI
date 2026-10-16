import {Router} from 'express';
import {requireStrategyLabAdmin} from '../services/strategyLabAdminAuth.js';
export default function researchRefreshRouter(agent,admin=requireStrategyLabAdmin){
 const router=Router();router.use(admin);
 router.get('/',async(_req,res)=>{try{res.set('Cache-Control','no-store').json(await agent.status());}catch{res.status(503).json({error:'Agent storage is not ready. Apply the research-refresh migration.'});}});
 router.post('/schedule',async(req,res)=>{try{res.json(await agent.setEnabled(req.body?.enabled));}catch{res.status(400).json({error:'Unable to update schedule.'});}});
 router.post('/run',async(_req,res)=>{try{res.json(await agent.run({force:true}));}catch{res.status(503).json({error:'Run could not finish. Check stored run history before retrying.'});}});
 return router;
}
