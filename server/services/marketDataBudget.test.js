import test from 'node:test';
import assert from 'node:assert/strict';
import { MarketDataBudget } from '../lib/marketDataBudget.js';
import { SharedLiveQuotes } from './sharedLiveQuotes.js';
import { createIndiaQuotes } from './indiaPortfolioTracking.js';

function fixture(budgets = { upstox: [[1000, 2], [60_000, 4]], groww: [[1000, 1]] }) {
 let at=100000; const waits=[];
 return { budget:new MarketDataBudget({budgets,now:()=>at,sleep:async ms=>{await new Promise(resolve=>setImmediate(resolve));waits.push(ms);at+=ms;}}),waits, now:()=>at };
}
test('concurrent requests respect shared windows and keep provider budgets separate',async()=>{
 const {budget,now}=fixture(); const calls=[];
 const fetcher=async()=>{calls.push(now());return new Response('{}');};
 await Promise.all([1,2,3].map(i=>budget.fetch('upstox',`https://test/history/${i}`,{},fetcher)));
 assert.deepEqual(calls,[100000,100000,101000]);
 await budget.fetch('groww','https://test/history',{},fetcher);
 assert.equal(budget.status().providers.groww.requests,1);
});
test('duplicate downloads coalesce without sharing consumed response bodies',async()=>{
 const {budget}=fixture();let calls=0,release;
 const wait=new Promise(resolve=>release=resolve);
 const fetcher=async()=>{calls++;await wait;return new Response('{"ok":true}');};
 const a=budget.fetch('upstox','https://test/history',{},fetcher),b=budget.fetch('upstox','https://test/history',{},fetcher);
 release();const rows=await Promise.all([a,b]);
 assert.equal(calls,1);assert.deepEqual(await Promise.all(rows.map(r=>r.json())),[{ok:true},{ok:true}]);
});
test('429 opens circuit; no retry storm, errors are not cached',async()=>{
 const {budget}=fixture();let calls=0;
 const fetcher=async()=>{calls++;return new Response('{}',{status:429,headers:{'retry-after':'90'}});};
 await budget.fetch('groww','https://test/live-data/quote',{},fetcher);
 await assert.rejects(budget.fetch('groww','https://test/live-data/quote',{},fetcher),e=>e.status===429);
 assert.equal(calls,1);assert.equal(budget.status().providers.groww.deferred,1);
});
test('authentication separates cached quotes; writes cannot enter the data client',async()=>{
 const {budget}=fixture({upstox:[[1000,10]]});let calls=0;
 const fetcher=async()=>{calls++;return new Response('{}');};
 for(const token of ['a','a','b'])await budget.fetch('upstox','https://test/market-quote/quotes',{headers:{Authorization:token}},fetcher);
 assert.equal(calls,2);
 await assert.rejects(budget.fetch('upstox','https://test',{method:'POST'},fetcher),/read-only/);
});
test('shared prices reject stale, future and out-of-order trades',()=>{
 const store=new SharedLiveQuotes();
 store.ingest([{instrument_key:'x',ltp:10,exchange_timestamp:100000}],100000);
 store.ingest([{instrument_key:'x',ltp:20,exchange_timestamp:90000},{instrument_key:'x',ltp:30,exchange_timestamp:200000}],100000);
 assert.equal(store.get('x',100000).price,10);assert.equal(store.get('x',131000),null);
});
test('portfolio reuses live quotes and only fetches missing instruments',async()=>{
 const shared=new SharedLiveQuotes(),at=Date.parse('2026-10-05T09:00:00Z');
 shared.ingest([{instrument_key:'NSE_EQ|a',ltp:10,exchange_timestamp:at}],at);
 let url='';
 const quotes=createIndiaQuotes({shared,now:()=>new Date(at),token:()=> 'test',master:async()=>({items:[{symbol:'A',instrumentKey:'NSE_EQ|a'},{symbol:'B',instrumentKey:'NSE_EQ|b'}]}),fetcher:async u=>{url=decodeURIComponent(u);return new Response(JSON.stringify({status:'success',data:{'NSE_EQ:B':{last_price:20,last_trade_time:at}}}));}});
 const result=await quotes(['A','B']);assert.equal(result.quotes.A.price,10);assert.equal(result.quotes.B.price,20);
 assert.match(url,/NSE_EQ\|b/);assert.doesNotMatch(url,/NSE_EQ\|a/);
 assert.equal(result.quotes.A.time,new Date(at).toISOString());
});

test('background downloads cannot consume the live quote reserve',async()=>{
 const budget=new MarketDataBudget({now:()=>100000,budgets:{upstox:[[60000,2]]},backgroundBudgets:{upstox:[[60000,1]]}});
 let calls=0;const fetcher=async()=>{calls++;return new Response('{}');};
 await budget.fetch('upstox','https://test/history/1',{},fetcher);
 await assert.rejects(budget.fetch('upstox','https://test/history/2',{},fetcher),e=>e.status===429);
 const quote=await budget.fetch('upstox','https://test/market-quote/quotes',{},fetcher);
 assert.equal(quote.status,200);assert.equal(calls,2);
});
