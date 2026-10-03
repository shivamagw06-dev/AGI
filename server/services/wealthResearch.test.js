import test from 'node:test';
import assert from 'node:assert/strict';
import { getWealthEquityResearch, validateEvidenceFeed, createEvidenceProvider } from './wealthResearch.js';
const now=Date.parse('2026-09-24T12:00:00Z');
test('research reads stored evidence only and excludes meaningless metrics',async()=>{
 const r=await getWealthEquityResearch('TEST',{now:()=>now,readPack:async()=>({ok:true,freshness:'fresh',generated_at:'2026-09-24T11:59:00Z',table:[{metric:'pe',company:20,meaningful:true},{metric:'roe',company:null,meaningful:true},{metric:'pb',company:3,meaningful:false}]})});
 assert.equal(r.status,'available');assert.equal(r.metrics.length,1);assert.equal(r.metrics[0].value,20);
 const stale=await getWealthEquityResearch('TEST',{now:()=>now,readPack:async()=>({ok:true,freshness:'fresh',generated_at:'2027-01-01',table:[]})});assert.equal(stale.status,'stale');
});
test('missing company research remains unavailable',async()=>assert.equal((await getWealthEquityResearch('TEST',{readPack:async()=>null})).status,'unavailable'));
test('external evidence requires explicit rights, a dated review and valid records',()=>{
 const input={version:'agi-wealth-evidence-v1',provider:'Example provider',displayRightsConfirmed:true,reviewedAt:'2026-09-24',records:[{kind:'events',id:'e',name:'Review issuer',due:'2026-10-01',source:'https://example.com/disclosure',impact:'Review credit',status:'pending'}]};
 assert.equal(validateEvidenceFeed(input,now).records.length,1);
 assert.throws(()=>validateEvidenceFeed({...input,displayRightsConfirmed:false},now));
 assert.throws(()=>validateEvidenceFeed({...input,reviewedAt:'2026-01-01'},now));
 assert.throws(()=>validateEvidenceFeed({...input,records:[...input.records,...input.records]},now),/Duplicate/);
});
test('unconfigured and invalid evidence feeds fail closed; no user URL fetching',async()=>{
 const missing=createEvidenceProvider({path:()=>null});assert.equal((await missing()).status,'not_connected');
 let reads=0;const bad=createEvidenceProvider({path:()=>'/configured/file',info:async()=>({size:3000000}),read:async()=>{reads++;return '{}';},now:()=>now});
 assert.equal((await bad()).status,'unavailable');assert.equal(reads,0);
});
