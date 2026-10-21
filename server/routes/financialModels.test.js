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

test('production auth client verifies a member without a native WebSocket',async()=>{
 const originalFetch=globalThis.fetch, originalSocket=globalThis.WebSocket;
 const oldUrl=process.env.SUPABASE_URL, oldKey=process.env.SUPABASE_ANON_KEY;
 process.env.SUPABASE_URL='https://model-auth-test.supabase.co';process.env.SUPABASE_ANON_KEY='test-public-key';
 globalThis.WebSocket=undefined;
 let verified=0;
 globalThis.fetch=async(input,options)=>{
  if(String(input).startsWith('https://model-auth-test.supabase.co/auth/v1/user')){
   verified++;assert.equal(new Headers(options.headers).get('Authorization'),'Bearer member-session');
   return new Response(JSON.stringify({id:'member',email:'member@example.test',email_confirmed_at:'2026-01-01',is_anonymous:false}),{status:200,headers:{'Content-Type':'application/json'}});
  }
  return originalFetch(input,options);
 };
 const app=express();app.use('/models',createFinancialModelsRouter());
 const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
 try{
  const response=await originalFetch(`http://127.0.0.1:${server.address().port}/models/catalog`,{headers:{Authorization:'Bearer member-session'}});
  assert.equal(response.status,200,await response.clone().text());assert.equal((await response.json()).models.length,16);assert.equal(verified,1);
  const workbook=await originalFetch(`http://127.0.0.1:${server.address().port}/models/library`,{headers:{Authorization:'Bearer member-session'}});
  assert.equal(workbook.status,200);assert.match(workbook.headers.get('content-type'),/spreadsheetml/);await workbook.arrayBuffer();assert.equal(verified,2);
 }finally{
  globalThis.fetch=originalFetch;globalThis.WebSocket=originalSocket;
  if(oldUrl===undefined)delete process.env.SUPABASE_URL;else process.env.SUPABASE_URL=oldUrl;
  if(oldKey===undefined)delete process.env.SUPABASE_ANON_KEY;else process.env.SUPABASE_ANON_KEY=oldKey;
  server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
 }
});
