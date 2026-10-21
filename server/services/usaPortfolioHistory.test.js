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
function yahoo(symbol,dates,prices){return {chart:{result:[{meta:{symbol,currency:'USD',instrumentType:'ETF',exchangeTimezoneName:'America/New_York'},timestamp:dates.map(d=>Date.parse(d+'T13:30:00Z')/1000),indicators:{quote:[{close:prices,volume:prices.map(()=>1)}],adjclose:[{adjclose:prices}]}}]}};}
const dates=['2026-10-02','2026-10-05'];
const seedFor=()=>({schemaVersion:1,asOf:dates[0],requestedCutoff:dates[1],calendar:[dates[0]],securities:{SPY:parseYahoo('SPY',yahoo('SPY',[dates[0]],[100]),dates[1]),AAPL:parseYahoo('AAPL',yahoo('AAPL',[dates[0]],[200]),dates[1])}});
test('null latest candle remains pending and retries the SAME cutoff after fifteen minutes',async()=>{
 let time=Date.parse('2026-10-06T00:00Z'),ready=false,calls=0,saves=0;
 const h=createUSHistory({readSeed:async()=>JSON.stringify(seedFor()),now:()=>new Date(time),pause:async()=>{},persist:async()=>{saves++},fetcher:async url=>{calls++;const s=new URL(url).pathname.split('/').at(-1);return {ok:true,status:200,json:async()=>yahoo(s,dates,[s==='SPY'?100:200,ready?(s==='SPY'?110:210):null])}}});
 const a=await h.refresh();assert.equal(a.asOf,dates[0]);assert.match(a.refresh.error,/pending/);assert.equal(calls,1);await h.refresh();assert.equal(calls,1);
 ready=true;time+=15*60*1000;const b=await h.refresh();assert.equal(b.asOf,dates[1]);assert.equal(b.completedCutoff,dates[1]);assert.equal(saves,1);assert.equal(calls,3);assert.equal(b.refresh.error,null);
});
test('individual failures retain verified history and do not finish the cutoff',async()=>{
 const seed=seedFor();const h=createUSHistory({readSeed:async()=>JSON.stringify(seed),now:()=>new Date('2026-10-06T00:00Z'),pause:async()=>{},fetcher:async url=>{const s=new URL(url).pathname.split('/').at(-1);return s==='AAPL'?{ok:false,status:502}:{ok:true,status:200,json:async()=>yahoo(s,dates,[100,110])}}});
 const d=await h.refresh();assert.equal(d.asOf,dates[1]);assert.deepEqual(d.securities.AAPL,JSON.parse(JSON.stringify(seed.securities.AAPL)));assert.equal(d.completedCutoff,null);assert.match(d.refresh.error,/1 instruments/);
});
test('durable newer history wins after restart over a deployment seed',async()=>{
 const {selectHistorySnapshot}=await import('./usaPortfolioHistory.js');const old=seedFor(),newer={...old,asOf:dates[1],calendar:dates,securities:{SPY:parseYahoo('SPY',yahoo('SPY',dates,[100,110]),dates[1])}};assert.equal(selectHistorySnapshot(old,[newer]).asOf,dates[1]);assert.equal(selectHistorySnapshot(newer,[old]).asOf,dates[1]);
});
test('persistence failure cannot suppress the next retry',async()=>{
 const h=createUSHistory({readSeed:async()=>JSON.stringify({...seedFor(),securities:{SPY:seedFor().securities.SPY}}),now:()=>new Date('2026-10-06T00:00Z'),pause:async()=>{},persist:async()=>{throw Error('storage unavailable')},fetcher:async()=>({ok:true,status:200,json:async()=>yahoo('SPY',dates,[100,110])})});const d=await h.refresh();assert.equal(d.completedCutoff,null);assert.match(d.refresh.error,/storage/);
});
