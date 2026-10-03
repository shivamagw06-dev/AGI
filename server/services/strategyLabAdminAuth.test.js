import test from 'node:test';
import assert from 'node:assert/strict';
import { requireStrategyLabAdmin } from './strategyLabAdminAuth.js';

test('investor review guard rejects missing sessions and user-editable admin metadata', async t => {
 const before={...process.env};t.after(()=>{for(const key of Object.keys(process.env))if(!(key in before))delete process.env[key];Object.assign(process.env,before);});
 const env=(key,value)=>{process.env[key]=value;};
 env('SUPABASE_URL','https://auth.example');
 env('SUPABASE_ANON_KEY','test-public-key');
 env('ADMIN_EMAILS','owner@example.com');
 env('VITE_ADMIN_EMAILS','');
 env('ADMIN_USER_ID','');
 env('VITE_ADMIN_ID','');
 const response=()=>({code:null,body:null,status(code){this.code=code;return this;},json(body){this.body=body;return this;}});
 let next=false;
 const missing=response();await requireStrategyLabAdmin({get:()=>''},missing,()=>{next=true;});assert.equal(missing.code,401);assert.equal(next,false);
 t.mock.method(globalThis,'fetch',async()=>({ok:true,json:async()=>({id:'other-user',email:'visitor@example.com',user_metadata:{role:'admin'}})}));
 const denied=response();await requireStrategyLabAdmin({get:()=> 'Bearer test'},denied,()=>{next=true;});assert.equal(denied.code,403);assert.equal(next,false);
});
