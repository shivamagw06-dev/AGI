import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {session,makeBaseline,valueBaseline,createIndiaQuotes} from './indiaPortfolioTracking.js';
import {validatePortfolio} from './portfolioCatalog.js';
const seeds=JSON.parse(readFileSync(new URL('../data/indiaPortfolioSeeds.json',import.meta.url)));
const monday=new Date('2026-10-05T03:46:00Z');
const p={revision:1,holdings:[{symbol:'A',weight:48},{symbol:'B',weight:50}],cashWeight:2};
const quotes={A:{price:100,time:monday.toISOString(),instrumentKey:'NSE_EQ|A'},B:{price:200,time:monday.toISOString(),instrumentKey:'NSE_EQ|B'}};
test('final membership counts, exact totals and all caps',()=>{
 const counts={'in-momentum':22,'in-growth':23,'in-value':25,'in-quality':25,'in-all-weather':25};
 for(const p of seeds){validatePortfolio(p);assert.equal(p.holdings.filter(h=>h.assetType!=='gold_etf').length,counts[p.id]);const sectors={};let total=Math.round(p.cashWeight*100);
 for(const h of p.holdings){total+=Math.round(h.weight*100);assert.ok(h.weight<=7&&h.weight>0);if(h.marketCapCr<10000)assert.ok(h.weight<=4);sectors[h.sector]=(sectors[h.sector]||0)+Math.round(h.weight*100);}
 assert.equal(total,10000);for(const w of Object.values(sectors))assert.ok(w<=2500);}
 assert.equal(new Set(seeds.flatMap(p=>p.holdings.filter(h=>h.assetType!=='gold_etf').map(h=>h.symbol))).size,100);
});
test('no prelaunch, weekend, stale, missing or late backfilled baseline',()=>{
 assert.equal(session(new Date('2026-10-03T04:00:00Z')).open,false);
 for(const date of ['2026-10-02T04:00:00Z','2026-10-05T03:44:00Z','2026-10-06T04:00:00Z'])assert.equal(makeBaseline(p,quotes,new Date(date)),null);
 assert.equal(makeBaseline(p,{A:quotes.A},monday),null);
 assert.equal(makeBaseline(p,{...quotes,A:{...quotes.A,time:'2026-10-01T10:00:00Z'}},monday),null);
 assert.equal(makeBaseline({...p,cashWeight:0},quotes,monday),null);
});
test('fixed units, cash, quote gaps and instrument changes',()=>{
 const base=makeBaseline(p,quotes,monday);assert.ok(base);assert.equal(valueBaseline(base,quotes,monday).nav,100);
 assert.equal(valueBaseline(base,{...quotes,A:{...quotes.A,price:110}},monday).nav,104.8);
 assert.equal(valueBaseline(base,{A:quotes.A},monday).nav,null);
 assert.equal(valueBaseline(base,{...quotes,A:{...quotes.A,instrumentKey:'changed'}},monday).nav,null);
 assert.equal(base.holdings[0].basePrice,100);
});
test('Upstox adapter resolves keys, validates response and caches calls',async()=>{
 let calls=0;const reader=createIndiaQuotes({master:async()=>({items:[{symbol:'A',instrumentKey:'NSE_EQ|A'}]}),token:()=> 'test',now:()=>monday,fetcher:async()=>{calls++;return {ok:true,json:async()=>({status:'success',data:{'NSE_EQ:A':{last_price:100,last_trade_time:monday.getTime()}}})};}});
 const result=await reader(['A']);assert.equal(result.quotes.A.time,monday.toISOString());assert.equal(result.quotes.A.price,100);await reader(['A']);assert.equal(calls,1);
});
