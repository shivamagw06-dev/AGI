import test from 'node:test';
import assert from 'node:assert/strict';
import {completedUSDate,parseYahoo,createUSHistory} from './usaPortfolioHistory.js';
const payload={chart:{result:[{meta:{symbol:'SPY',currency:'USD',instrumentType:'ETF',exchangeTimezoneName:'America/New_York'},timestamp:[1790956800,1791043200],indicators:{quote:[{close:[100,110],volume:[1,2]}],adjclose:[{adjclose:[99,109]}]}}]}};
test('completed cutoff respects New York daylight saving and excludes partial sessions',()=>{
 assert.equal(completedUSDate(new Date('2026-10-05T20:30:00Z')),'2026-10-04');
 assert.equal(completedUSDate(new Date('2026-10-05T21:00:00Z')),'2026-10-05');
 assert.equal(completedUSDate(new Date('2026-12-01T21:30:00Z')),'2026-11-30');
});
test('Yahoo adjusted prices and identity validated',()=>{
 const s=parseYahoo('SPY',payload,'2026-10-02');assert.equal(s.bars[0][1],99);assert.equal(s.bars[0][2],100);
 assert.throws(()=>parseYahoo('OTHER',payload,'2026-10-02'));
 const p=structuredClone(payload);p.chart.result[0].meta.currency='INR';assert.throws(()=>parseYahoo('SPY',p,'2026-10-02'));
});
test('rate limits retain the dated snapshot and coalesce refreshes',async()=>{
 const seed={schemaVersion:1,asOf:'2026-10-01',requestedCutoff:'2026-10-01',securities:{SPY:{}},calendar:['2026-10-01']};let calls=0;
 const h=createUSHistory({readSeed:async()=>JSON.stringify(seed),now:()=>new Date('2026-10-05T22:00:00Z'),pause:async()=>{},fetcher:async()=>{calls++;return {status:429};}});
 const [a,b]=await Promise.all([h.refresh(),h.refresh()]);assert.equal(calls,1);assert.equal(a.asOf,'2026-10-01');assert.match(b.refresh.error,/429/);await h.refresh();assert.equal(calls,1);
});
