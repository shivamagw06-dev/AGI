import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import createRouter from './portfolioCatalog.js';
import {factorTarget,factorIds,factorCandidates} from '../services/factorSelection.js';
const id='in-momentum',portfolio=factorTarget({id,name:'Momentum',market:'india',asOf:'2026-10-19'});
const row={portfolio_id:id,revision:4,document:{portfolio,history:[],events:[],account:{holdings:[]},categories:[]}};
test('public selection batches and caches the shared universe; writes require admin',async()=>{
 let reads=0,writes=0,seen=[];
 const app=express();app.use(express.json());app.use(createRouter({now:()=>new Date('2026-10-19T06:00:00Z'),ledger:()=>({get:async()=>row,schedule:async()=>{writes++;return row;}}),readFactorQuotes:async symbols=>{reads++;seen=symbols;return {quotes:{}};},admin:(_req,res)=>res.sendStatus(403)}));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}`;
 try{const responses=await Promise.all([fetch(base+`/${id}/factor-selection`),fetch(base+`/${id}/factor-selection`)]);for(const r of responses){assert.equal(r.status,200);const d=await r.json();assert.equal(d.positions.length,50);assert.equal(d.active,false);}assert.equal(reads,1);assert.equal(new Set(seen).size,seen.length);assert.equal(seen.length,new Set(factorIds.flatMap(id=>factorCandidates(id).map(h=>h.symbol))).size);assert.equal((await fetch(base+`/${id}/factor-selection/rebalance`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,403);assert.equal(writes,0);}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
test('market closed does not request live quotes',async()=>{
 let reads=0;const app=express();app.use(createRouter({now:()=>new Date('2026-10-19T16:00Z'),ledger:()=>({get:async()=>row}),readFactorQuotes:async()=>{reads++;return {quotes:{}};}}));const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 try{const r=await fetch(`http://127.0.0.1:${server.address().port}/${id}/factor-selection`);assert.equal(r.status,200);assert.equal(reads,0);}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
