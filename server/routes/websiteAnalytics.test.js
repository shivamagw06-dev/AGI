import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import websiteAnalytics from './websiteAnalytics.js';
test('analytics rejects foreign origins, hides summaries, and forwards collection results',async t=>{
 const app=express();app.use(express.json());let calls=0;
 app.use(websiteAnalytics(async()=>{calls++;return{ok:true,status:200,data:{ok:true}};}));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));t.after(()=>server.close());
 const url=`http://127.0.0.1:${server.address().port}`;
 let r=await fetch(url+'/summary');assert.equal(r.status,401);assert.equal(calls,0);
 r=await fetch(url+'/event',{method:'POST',headers:{Origin:'https://other.example','Content-Type':'application/json'},body:'{}'});assert.equal(r.status,403);assert.equal(calls,0);
 r=await fetch(url+'/event',{method:'POST',headers:{Origin:'https://agarwalglobalinvestments.com','Content-Type':'application/json',DNT:'1'},body:'{}'});assert.equal(r.status,204);assert.equal(calls,0);
 r=await fetch(url+'/event',{method:'POST',headers:{Origin:'https://agarwalglobalinvestments.com','Content-Type':'application/json'},body:'{}'});assert.equal(r.status,202);assert.deepEqual(await r.json(),{ok:true});assert.equal(calls,1);
});
test('public summary is unauthenticated, sanitized, cached and range constrained',async t=>{
 const app=express();let calls=0;app.use(websiteAnalytics(async()=>{calls++;return{status:200,data:{ok:true,days:1,visitors:2,pages:[{label:'/portfolio/secret',views:1}],referrers:[],trend:[],visitorIds:['secret']}};}));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));t.after(()=>server.close());const url=`http://127.0.0.1:${server.address().port}`;
 assert.equal((await fetch(url+'/public-summary?days=2')).status,400);assert.equal(calls,0);
 let r=await fetch(url+'/public-summary?days=1');assert.equal(r.status,200);const body=await r.json();assert.equal(body.visitors,2);assert.ok(!JSON.stringify(body).includes('secret'));
 await fetch(url+'/public-summary?days=1');assert.equal(calls,1);assert.equal((await fetch(url+'/summary?days=1')).status,401);
});
