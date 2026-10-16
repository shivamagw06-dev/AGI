import test from 'node:test';
import assert from 'node:assert/strict';
import {createResearchRefreshAgent,readApprovedFeed} from './researchRefreshAgent.js';
import {SCREENERS} from './researchRefreshPolicy.js';
const now=()=>new Date('2026-10-15T12:00:00Z');
function fixture(){
 const b={version:1,provider:'trendlyne',complete:true,collectedAt:now().toISOString(),screeners:SCREENERS.map(slug=>({slug,asOf:'2026-10-15',complete:true,expectedRows:1,tables:['csv']})),institutions:['individual','institutional'].map(category=>({country:'IN',category,asOf:'2026-09-30',complete:true,expectedRows:1,text:'csv'}))};
 const calls=[],rows=[{isin:'INE000000001',stock:'Example'}],adapters=Object.fromEntries(SCREENERS.map(s=>[s,[()=>rows,async()=>null,async()=>{calls.push(s);return {id:1};}]]));
 const client={rpc:async(name,args)=>{calls.push({name,args});return {data:true};}};
 const engineFetch=async(path)=>({status:200,data:path.includes('preview')?{ok:true,row_count:1,rows}:path.includes('publish')?(calls.push('institution'),{ok:true}):{rows:[]}});
 return {b,calls,adapters,client,engineFetch};
}
test('validates all sources before any publication and records blocked run',async()=>{
 const f=fixture();f.b.screeners.at(-1).expectedRows=2;
 const a=createResearchRefreshAgent({client:f.client,feed:async()=>f.b,screeners:f.adapters,engineFetch:f.engineFetch,portfolios:async()=>[],now});
 const r=await a.run({force:true});assert.equal(r.status,'blocked');assert.equal(f.calls.filter(c=>typeof c==='string').length,0);assert.equal(f.calls.at(-1).name,'finish_research_refresh');
});
test('publishes valid data, labels unsupported scopes, and never invokes rebalance',async()=>{
 const f=fixture();const r=await createResearchRefreshAgent({client:f.client,feed:async()=>f.b,screeners:f.adapters,engineFetch:f.engineFetch,portfolios:async()=>[],now}).run();
 assert.equal(r.status,'complete');assert.equal(r.publications.length,7);assert.equal(r.blockers.length,2);assert.equal(f.calls.filter(c=>typeof c==='string').length,7);
});
test('duplicate scheduler claim makes no source requests',async()=>{
 const a=createResearchRefreshAgent({client:{rpc:async()=>({data:false})},feed:async()=>{throw Error('must not run');},now});assert.equal((await a.run()).status,'not_due_or_running');
});
test('same data and dates are idempotent on retry',async()=>{
 const f=fixture(),rows=[{isin:'INE000000001',stock:'Example'}];for(const s of SCREENERS)f.adapters[s][1]=async()=>({id:1,as_of:'2026-10-15',rows});
 f.engineFetch=async()=>({status:200,data:{ok:true,asOf:'2026-09-30',row_count:1,rows}});
 const r=await createResearchRefreshAgent({client:f.client,feed:async()=>f.b,screeners:f.adapters,engineFetch:f.engineFetch,portfolios:async()=>[],now}).run();assert.ok(r.publications.every(p=>p.status==='unchanged'));assert.equal(f.calls.filter(c=>typeof c==='string').length,0);
});
test('unconfigured source and authentication HTML cannot be accepted as data',async()=>{
 await assert.rejects(readApprovedFeed({env:{}}),/SOURCE_NOT_CONFIGURED/);
 await assert.rejects(readApprovedFeed({env:{RESEARCH_REFRESH_FEED_URL:'https://example.org/data'},fetcher:async()=>new Response('<html>login</html>',{headers:{'content-type':'text/html'}})}),/login/);
});
test('scheduled work waits until 17:00 India time; explicit checks can run earlier',async()=>{
 const a=createResearchRefreshAgent({client:{rpc:async()=>({data:false})},now:()=>new Date('2026-10-15T06:00:00Z')});
 assert.equal((await a.run()).status,'waiting_for_17_ist');assert.equal((await a.run({force:true})).status,'not_due_or_running');
});
test('a publication failure preserves a partial report rather than claiming completion',async()=>{
 const f=fixture();f.adapters['low-pe'][2]=async()=>{throw Error('Write unavailable');};
 const r=await createResearchRefreshAgent({client:f.client,feed:async()=>f.b,screeners:f.adapters,engineFetch:f.engineFetch,portfolios:async()=>[],now}).run();
 assert.equal(r.status,'partial');assert.equal(r.publications.length,1);assert.equal(r.publications[0].name,'momentum');
});
