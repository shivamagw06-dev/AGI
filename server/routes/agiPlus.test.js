import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import createPlusRouter from './agiPlus.js';
import { canonicalReference, membershipActive, plusAdmin } from '../services/agiPlus.js';
test('paid access uses dates, revocation and verified admin identity, never user metadata',()=>{
 const now=Date.parse('2026-10-27T10:00:00Z'),m={starts_at:'2026-10-01T00:00:00Z',expires_at:'2026-10-28T00:00:00Z',revoked_at:null};
 assert.equal(membershipActive(m,now),true);assert.equal(membershipActive({...m,revoked_at:'2026-10-26'},now),false);assert.equal(membershipActive({...m,expires_at:'2026-10-27T10:00:00Z'},now),false);assert.equal(membershipActive({...m,starts_at:'2026-10-29'},now),false);assert.equal(plusAdmin({id:'ordinary',user_metadata:{role:'admin',isAdmin:true}}),false);assert.equal(canonicalReference('  abc 123456789 '),'ABC123456789');assert.equal(canonicalReference('<script>'),null);
});
test('payment claims cannot approve access, spoof ownership or bypass bank verification',async()=>{
 const calls=[],service={config:async()=>({enabled:true,checkoutEnabled:true,amountPaise:19900}),user:async token=>token==='admin'?{id:'c56e4d07-273c-49c9-86a5-a4445e687ece',email:'admin@example.test'}:{id:'verified-user',email:'real@example.test'},membership:async()=>null,payments:async id=>{calls.push(['history',id]);return [];},submit:async(user,reference)=>{calls.push(['submit',user,reference]);return {id:'pending',status:'pending'};},queue:async()=>[],review:async(...args)=>{calls.push(['review',...args]);return {status:'approved'};}};
 const app=express();app.use(express.json());app.use('/plus',createPlusRouter(service));const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}/plus`,headers={'content-type':'application/json',authorization:'Bearer ordinary'};
 try{
  assert.equal((await fetch(base+'/status')).status,401);
  assert.equal((await fetch(base+'/admin',{headers})).status,403);
  const claim=await fetch(base+'/payments',{method:'POST',headers,body:JSON.stringify({reference:'123456789012',paidConfirmation:true,user_id:'spoof',amount_paise:1,status:'approved'})});assert.equal(claim.status,202);assert.equal((await claim.json()).status,'pending');assert.equal(calls[0][1].id,'verified-user');assert.equal(calls[0][2],'123456789012');
  const id='11111111-1111-4111-8111-111111111111',body={decision:'approve',note:'Verified credit',bankReference:'123456789012',verifiedAmountPaise:19900,bankCreditVerified:true};
  assert.equal((await fetch(base+`/admin/payments/${id}/review`,{method:'POST',headers,body:JSON.stringify(body)})).status,403);
  const adminHeaders={...headers,authorization:'Bearer admin'};
  assert.equal((await fetch(base+`/admin/payments/${id}/review`,{method:'POST',headers:adminHeaders,body:JSON.stringify({...body,bankCreditVerified:false})})).status,400);
  assert.equal((await fetch(base+`/admin/payments/${id}/review`,{method:'POST',headers:adminHeaders,body:JSON.stringify({...body,verifiedAmountPaise:100})})).status,400);
  assert.equal((await fetch(base+`/admin/payments/${id}/review`,{method:'POST',headers:adminHeaders,body:JSON.stringify(body)})).status,200);
  assert.equal(calls.filter(c=>c[0]==='review').length,1);
  await fetch(base+'/status?user_id=spoof',{headers});assert.deepEqual(calls.at(-1),['history','verified-user']);
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});
