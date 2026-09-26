import test from 'node:test';
import assert from 'node:assert/strict';
import { requireStrategyLabAdmin } from './strategyLabAdminAuth.js';
import { readFileSync } from 'node:fs';
test('institution preview and publish use the server admin guard',()=>{
 const source=readFileSync(new URL('../routes/intelligence.js',import.meta.url),'utf8');
 assert.match(source,/for \(const operation of \['preview','publish'\]\)/);
 assert.ok(source.includes('router.post(`/institutions/${operation}`, requireStrategyLabAdmin,'));
});
test('publishing guard rejects missing credentials and a verified non-admin',async()=>{
 let status=0,passed=false;const res={status(n){status=n;return this;},json(){return this;}};
 await requireStrategyLabAdmin({get:()=>''},res,()=>{passed=true;});assert.equal(status,401);assert.equal(passed,false);
 const previous={SUPABASE_URL:process.env.SUPABASE_URL,SUPABASE_ANON_KEY:process.env.SUPABASE_ANON_KEY};const original=globalThis.fetch;
 process.env.SUPABASE_URL='https://example.invalid';process.env.SUPABASE_ANON_KEY='test';
 globalThis.fetch=async()=>({ok:true,json:async()=>({id:'ordinary-user-for-test',email:'ordinary-user@example.invalid'})});
 try{await requireStrategyLabAdmin({get:()=> 'Bearer test'},res,()=>{passed=true;});assert.equal(status,403);assert.equal(passed,false);}finally{globalThis.fetch=original;for(const [key,value] of Object.entries(previous)){if(value===undefined)delete process.env[key];else process.env[key]=value;}}
});
