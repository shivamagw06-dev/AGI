import test from 'node:test';
import assert from 'node:assert/strict';
import { gzipSync } from 'node:zlib';
import { parseUpstoxFunds, createUpstoxFundProvider } from './upstoxMutualFunds.js';
const row = {instrument_key:'INF109K01Q49',name:'Test Direct Growth',last_price:12.45,last_price_date:'2026-09-24',minimum_purchase_amount:100,purchase_allowed:false};
test('directory preserves missing fields and rejects invalid identities and dates',()=>{
  const rows = parseUpstoxFunds([row,row,{}, {...row,instrument_key:'INF109K01Q48',last_price:null,last_price_date:'2026-02-30'}]);
  assert.equal(rows.length,2); assert.equal(rows[0].purchaseAllowed,false); assert.equal(rows[0].plan,null);
  assert.equal(rows[1].price,null); assert.equal(rows[1].asOf,null);
});
test('gzip directory shares requests, caches and keeps stale records on failure',async()=>{
  let calls=0, now=0;
  const provider=createUpstoxFundProvider({now:()=>now,fetchImpl:async()=>{calls++; if(calls>1) throw new Error('offline');return new Response(gzipSync(JSON.stringify([row])));}});
  const [a,b]=await Promise.all([provider(),provider()]);
  assert.equal(calls,1);assert.equal(a,b);assert.equal(a.rows[0].price,12.45);
  await provider();assert.equal(calls,1);now=3600001;
  const stale=await provider();assert.equal(stale.status,'stale');assert.equal(stale.rows.length,1);
});
test('unavailable directory fails explicitly without invented data',async()=>{
  const provider=createUpstoxFundProvider({fetchImpl:async()=>new Response('{}')});
  assert.equal((await provider()).status,'unavailable');
});
