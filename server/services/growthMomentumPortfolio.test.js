import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import {growthMomentumPortfolio,GROWTH_MOMENTUM_ID} from './growthMomentumPortfolio.js';
import createRouter from '../routes/portfolioCatalog.js';
const parents=[{id:'in-growth',name:'Growth',asOf:'2026-10-03',revision:2,market:'india',holdings:[{symbol:'A',name:'A',weight:60,instrumentKey:'a'},{symbol:'B',name:'B',weight:40,instrumentKey:'b'}]}, {id:'in-momentum',name:'Momentum',asOf:'2026-10-03',revision:3,market:'india',holdings:[{symbol:'A',name:'A',weight:20,instrumentKey:'a'},{symbol:'C',name:'C',weight:80,instrumentKey:'c'}]}];
test('50/50 combination preserves parent weights and merges overlap without rounding drift',()=>{
 const p=growthMomentumPortfolio(parents);assert.equal(p.visibility,'admin');assert.equal(p.holdings.length,3);assert.deepEqual(Object.fromEntries(p.holdings.map(h=>[h.symbol,h.weight])),{A:40,C:40,B:20});
 assert.equal(p.holdings.reduce((s,h)=>s+h.weight,0),100);assert.equal(p.holdings.find(h=>h.symbol==='A').contributions.length,2);
 assert.equal(parents[0].holdings[0].weight,60);
});
test('incomplete, duplicate or conflicting sources fail rather than fabricating an allocation',()=>{
 assert.throws(()=>growthMomentumPortfolio([]));
 for(const change of [p=>p[0].incomplete=true,p=>p[0].holdings[0].weight=NaN,p=>p[1].holdings[0].instrumentKey='wrong',p=>p[0].holdings[1].symbol='A']){const p=structuredClone(parents);change(p);assert.throws(()=>growthMomentumPortfolio(p));}
});
test('private endpoint requires admin and neither public endpoint exposes private holdings or tracking',async()=>{
 const app=express();const privateP=growthMomentumPortfolio(parents);let calls=0;
 app.use('/api/portfolios',createRouter({store:{list:async()=>[...parents,privateP]},admin:(req,res,next)=>req.get('authorization')==='Bearer admin'?next():res.sendStatus(403),readTracking:async rows=>{calls++;return {portfolios:rows.map(p=>({id:p.id,status:'scheduled'}))};}}));
 const server=app.listen(0);await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}/api/portfolios`;
 try{
  for(const path of ['', '/india-tracking']){const body=await(await fetch(base+path)).json();assert.equal(body.portfolios.length,2);assert.ok(body.portfolios.every(p=>p.id!==GROWTH_MOMENTUM_ID));}
  const prior=calls;assert.equal((await fetch(base+'/admin/growth-momentum')).status,403);assert.equal((await fetch(base+'/admin/growth-momentum',{headers:{Authorization:'Bearer non-admin'}})).status,403);assert.equal(calls,prior);
  const response=await fetch(base+'/admin/growth-momentum',{headers:{Authorization:'Bearer admin'}});assert.equal(response.status,200);assert.equal(response.headers.get('cache-control'),'private, no-store');const body=await response.json();assert.equal(body.portfolio.id,GROWTH_MOMENTUM_ID);assert.equal(body.tracking.portfolios.length,3);
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
