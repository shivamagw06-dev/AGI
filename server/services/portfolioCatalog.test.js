import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import express from 'express';
import { validatePortfolio } from './portfolioCatalog.js';
import createRouter from '../routes/portfolioCatalog.js';
const seeds=JSON.parse(readFileSync(new URL('../data/portfolioSeeds.json',import.meta.url)));
test('all 26 source allocations validate without rescaling partial holdings',()=>{
 assert.equal(seeds.length,26);
 for(const p of seeds) assert.deepEqual(validatePortfolio(p).holdings,p.holdings);
 const partial=seeds.find(p=>p.id==='us-top10');
 assert.equal(partial.holdings.length,3);
 assert.equal(Math.round(partial.holdings.reduce((s,h)=>s+h.weight,0)*100),2960);
});
test('reject invalid weights, dates, duplicates and complete portfolios below 100%',()=>{
 const p=seeds[0];
 for(const patch of [{asOf:'2026-02-30'},{market:'uk'},{holdings:[{name:'X',weight:-1}]},{holdings:[{name:'X',weight:50}]},{holdings:[{name:'X',weight:50},{name:'X',weight:50}]},{holdings:[{name:'X',weight:Infinity}]},{holdings:[{name:'X',symbol:'ABC',weight:50},{name:'Y',symbol:'ABC',weight:50}]}])assert.throws(()=>validatePortfolio({...p,...patch}));
 assert.equal(validatePortfolio({...p,holdings:[{name:'X',weight:40}],incomplete:true}).holdings[0].weight,40);
});
test('public reads, anonymous write denial and admin validated saves',async()=>{
 const app=express(); app.use(express.json());let writes=0;
 app.use('/api/portfolios',createRouter({store:{list:async()=>seeds,save:async(id,p,actor)=>{writes++;assert.equal(actor,'admin');return {...p,id};}},admin:(req,res,next)=>{if(req.get('authorization')!=='Bearer admin')return res.sendStatus(403);req.strategyLabActor={id:'admin'};next();}}));
 const server=app.listen(0);await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}/api/portfolios`;
 try{
 assert.equal((await(await fetch(base)).json()).portfolios.length,26);
 const send=(data,token)=>fetch(base+'/test',{method:'PUT',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer admin'}:{})},body:JSON.stringify(data)});
 assert.equal((await send(seeds[0])).status,403);assert.equal(writes,0);
 assert.equal((await send({...seeds[0],holdings:[]},true)).status,400);assert.equal(writes,0);
 assert.equal((await send(seeds[0],true)).status,200);assert.equal(writes,1);
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
