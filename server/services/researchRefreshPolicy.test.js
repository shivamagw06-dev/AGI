import test from 'node:test';
import assert from 'node:assert/strict';
import {validateEnvelope,reviewPortfolios,SCREENERS} from './researchRefreshPolicy.js';
const now=new Date('2026-10-15T12:00:00Z');
const bundle=()=>({version:1,provider:'trendlyne',complete:true,collectedAt:now.toISOString(),screeners:SCREENERS.map(slug=>({slug,asOf:'2026-10-15',complete:true,expectedRows:1,tables:['csv']})),institutions:['individual','institutional'].map(category=>({country:'IN',category,asOf:'2026-09-30',complete:true,expectedRows:1,text:'csv'}))});
test('accepts fresh retrieval with older actual ownership disclosure dates',()=>assert.ok(validateEnvelope(bundle(),now)));
test('rejects stale, duplicate, incomplete and future source snapshots',()=>{
 for(const change of [b=>b.collectedAt='2026-09-30T00:00:00Z',b=>b.screeners[0].asOf='2026-10-16',b=>b.screeners[0].complete=false,b=>b.screeners[1].slug=b.screeners[0].slug,b=>b.institutions.pop()]){const b=bundle();change(b);assert.throws(()=>validateEnvelope(b,now));}
});
test('missing inputs never turn into zero-valued failures or automatic removals',()=>{
 const p=[{id:'in-value',holdings:[{symbol:'BANK',weight:98},{symbol:'GOLDBEES',weight:2}]}];
 const r=reviewPortfolios(p,{rows:[{symbol:'BANK',asOf:'2026-10-15',marketCapCr:10000,forwardEPS:10,forwardPE:20,recommendationCount:8}]},now)[0];
 assert.equal(r.action,'review_only');assert.equal(r.holdings[0].status,'ranking_pending');assert.deepEqual(r.holdings[0].failures,[]);assert.ok(r.holdings[0].reasons.includes('Missing estimateContributors'));assert.equal(r.holdings[1].status,'retain_gold_sleeve');
});
test('flags confirmed cap breach, but does not use stale metrics as exit evidence',()=>{
 const p=[{id:'in-all-weather',holdings:[{symbol:'X',weight:4}]}];const row={symbol:'X',asOf:'2026-10-15',marketCapCr:4571.7};
 assert.equal(reviewPortfolios(p,{rows:[row]},now)[0].holdings[0].status,'eligibility_review');row.asOf='2026-09-30';assert.deepEqual(reviewPortfolios(p,{rows:[row]},now)[0].holdings[0].failures,[]);
});
