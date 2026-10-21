import test from 'node:test';
import assert from 'node:assert/strict';
import {createYahooRequest} from './yahooRequest.js';
const url='https://query1.finance.yahoo.com/v8/finance/chart/SPY';
test('deduplicates concurrent requests and caches independent readable responses',async()=>{
 let calls=0;const request=createYahooRequest({fetcher:async()=>{calls++;return Response.json({price:100});}});
 const [a,b]=await Promise.all([request(url),request(url)]);
 assert.deepEqual(await a.json(),{price:100});assert.deepEqual(await b.json(),{price:100});
 await request(url);assert.equal(calls,1);
});
test('serializes distinct requests with spacing',async()=>{
 let time=0;const starts=[];const request=createYahooRequest({now:()=>time,sleep:async ms=>{time+=ms;},fetcher:async()=>{starts.push(time);return Response.json({});}});
 await Promise.all([request(url),request(url+'?x=1'),request(url+'?x=2')]);assert.deepEqual(starts,[0,500,1000]);
});
test('429 cools all queued callers and respects Retry-After then exponential backoff',async()=>{
 let time=0,calls=0;const request=createYahooRequest({now:()=>time,sleep:async ms=>{time+=ms;},fetcher:async()=>{calls++;return new Response('',{status:429,headers:{'Retry-After':'90'}});}});
 const results=await Promise.all([request(url),request(url+'?x=1')]);assert.ok(results.every(r=>r.status===429));assert.equal(calls,1);
 time=89999;await request(url);assert.equal(calls,1);
 time=90001;await request(url);assert.equal(calls,2);
 time=180002;await request(url);assert.equal(calls,2);
});
test('failed responses are not cached and non-Yahoo writes are rejected',async()=>{
 let calls=0;const request=createYahooRequest({spacingMs:0,fetcher:async()=>{calls++;return new Response('',{status:500});}});
 await request(url);await request(url);assert.equal(calls,2);
 await assert.rejects(request('https://example.com'));await assert.rejects(request(url,{method:'POST'}));
});
