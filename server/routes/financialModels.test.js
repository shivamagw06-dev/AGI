import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import createFinancialModelsRouter from './financialModels.js';

test('Excel downloads require a server-verified non-anonymous account',async()=>{
 const app=express();let validations=0;
 app.use('/api/financial-models',createFinancialModelsRouter({authenticate:async token=>{validations++;if(token==='valid')return{id:'test-user',email_confirmed_at:'2026-01-01'};if(token==='anonymous')return{id:'anonymous',is_anonymous:true};if(token==='unverified')return{id:'test-user'};return null;}}));
 const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));const url=`http://127.0.0.1:${server.address().port}/api/financial-models/library`;
 try{
  assert.equal((await fetch(url)).status,401);assert.equal((await fetch(url.replace('/library','/catalog'))).status,401);assert.equal(validations,0);
  for(const token of ['bad','anonymous'])assert.equal((await fetch(url,{headers:{Authorization:`Bearer ${token}`}})).status,401);
  assert.equal((await fetch(url,{headers:{Authorization:'Bearer unverified'}})).status,403);
  const catalog=await fetch(url.replace('/library','/catalog'),{headers:{Authorization:'Bearer valid'}});assert.equal(catalog.status,200);assert.equal((await catalog.json()).models.length,16);
  const valid=await fetch(url,{headers:{Authorization:'Bearer valid'}});assert.equal(valid.status,200);assert.match(valid.headers.get('content-type'),/spreadsheetml/);assert.match(valid.headers.get('cache-control'),/no-store/);const bytes=new Uint8Array(await valid.arrayBuffer());assert.equal(bytes[0],80);assert.equal(bytes[1],75);assert.ok(bytes.length>100000);
 }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
