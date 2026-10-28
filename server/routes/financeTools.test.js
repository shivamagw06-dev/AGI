import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import financeTools from './financeTools.js';
test('prelaunch cannot publish or pay; applications use verified identity and admin protection', async () => {
 const calls=[];
 const app=express();app.use(express.json());
 app.use('/tools',financeTools(async(path,options)=>{calls.push({path,options});return {status:200,data:{ok:true,applications:[]}};},{
  member:(req,res,next)=>{if(req.get('authorization')!=='Bearer member')return res.status(401).end();req.toolsMember={id:'real-owner',email:'real@example.test'};next();},
  admin:(req,res,next)=>{if(req.get('authorization')!=='Bearer admin')return res.status(403).end();req.strategyLabActor={id:'admin'};next();}
 }));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const url=`http://127.0.0.1:${server.address().port}/tools`;
 try {
  const board=await (await fetch(url+'/board')).json();assert.equal(board.checkoutEnabled,false);assert.deepEqual(board.listings,[]);
  assert.equal((await fetch(url+'/applications',{method:'POST'})).status,401);
  assert.equal((await fetch(url+'/admin')).status,403);
  await fetch(url+'/applications',{method:'POST',headers:{authorization:'Bearer member','content-type':'application/json'},body:JSON.stringify({name:'Tool',owner:'spoof',email:'spoof',amount:999999,status:'paid',budget:500})});
  assert.equal(calls[0].options.body.owner,'real-owner');assert.equal(calls[0].options.body.email,'real@example.test');assert.equal(calls[0].options.body.status,undefined);assert.equal(calls[0].options.body.amount,undefined);
  await fetch(url+'/mine?owner=someone-else',{headers:{authorization:'Bearer member'}});assert.equal(calls[1].path,'/v1/finance-tools/applications?owner=real-owner');
  assert.equal((await fetch(url+'/checkout',{method:'POST'})).status,404);
 } finally {server.closeAllConnections();await new Promise(r=>server.close(r));}
});
