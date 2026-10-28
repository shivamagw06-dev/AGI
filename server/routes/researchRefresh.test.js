import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import createRouter from './researchRefresh.js';
test('all agent controls require the administrator guard before calling the agent',async()=>{
 let calls=0;const app=express();app.use(express.json());app.use(createRouter({status:async()=>{calls++;return {ok:true};},run:async()=>{calls++;return {status:'blocked'};},setEnabled:async()=>{calls++;return {}; }},(req,res,next)=>req.get('authorization')==='Bearer test-admin'?next():res.sendStatus(403)));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const url=`http://127.0.0.1:${server.address().port}`;
 try{for(const [path,method] of [['/','GET'],['/run','POST'],['/schedule','POST']])assert.equal((await fetch(url+path,{method})).status,403);assert.equal(calls,0);assert.equal((await fetch(url,{headers:{Authorization:'Bearer test-admin'}})).status,200);assert.equal(calls,1);}finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
