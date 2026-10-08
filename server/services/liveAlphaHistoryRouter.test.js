import test from 'node:test';
import assert from 'node:assert/strict';
import { createLiveAlphaHistoryRouter, validHistoryPayload } from './liveAlphaHistoryRouter.js';
const row=['2026-10-05T09:15:00+05:30',100,102,99,101,40,0];
const payload={data:{candles:[row]}};
test('cash history uses both providers while futures retain Upstox mapping',async()=>{
 const requests=[];
 const router=createLiveAlphaHistoryRouter({growwConfigured:()=>true,master:async()=>new Map([['NSE_EQ|A','NSE-A'],['NSE_EQ|B','NSE-B']]),growwHistory:async(...args)=>{requests.push(args);return [[Date.parse(row[0])/1000,...row.slice(1)]];},upstoxIntraday:async()=>payload,now:()=>new Date('2026-10-05T10:00:00+05:30')});
 for(const key of ['NSE_EQ|A','NSE_EQ|B','NSE_FO|123'])await router.intraday(key,{unit:'minutes',interval:1});
 assert.equal(router.status().groww,1);assert.equal(router.status().upstox,2);assert.equal(requests[0][5],1);
});
test('bad or unmapped Groww history falls back without inventing candles',async()=>{
 const router=createLiveAlphaHistoryRouter({growwConfigured:()=>true,master:async()=>new Map(),upstoxIntraday:async()=>payload});
 for(const key of ['NSE_EQ|A','NSE_EQ|B'])assert.deepEqual((await router.intraday(key,{})).data,payload.data);
 assert.equal(router.status().groww,0);assert.equal(router.status().fallbacks,1);
});
test('both providers failing does not report successful coverage',async()=>{
 const router=createLiveAlphaHistoryRouter({growwConfigured:()=>true,master:async()=>new Map(),upstoxIntraday:async()=>({data:{candles:[]}})});
 await assert.rejects(router.intraday('NSE_EQ|A',{}));assert.equal(router.status().failures,1);
 assert.equal(validHistoryPayload({data:{candles:[[row[0],100,90,99,101,40]]}}),false);
 assert.equal(validHistoryPayload({data:{candles:[[row[0],100,102,99,101,null]]}}),false);
});
test('three configured providers split cash and leave index and futures unchanged',async()=>{
 const router=createLiveAlphaHistoryRouter({growwConfigured:()=>true,indConfigured:()=>true,indStatus:()=>({configured:true}),master:async()=>new Map(['A','B','C'].map(x=>[`NSE_EQ|${x}`,x])),growwHistory:async()=>[[Date.parse(row[0])/1000,...row.slice(1)]],indHistory:async()=>payload,upstoxIntraday:async()=>payload});
 for(const key of ['NSE_EQ|A','NSE_EQ|B','NSE_EQ|C','NSE_INDEX|Nifty 50','NSE_FO|123'])await router.intraday(key,{});
 assert.equal(router.status().indstocks,1);assert.equal(router.status().groww,1);assert.equal(router.status().upstox,3);
});
test('failed INDstocks requests fall back to intact Upstox series',async()=>{
 const router=createLiveAlphaHistoryRouter({growwConfigured:()=>false,indConfigured:()=>true,indStatus:()=>({}),indHistory:async()=>{throw Object.assign(new Error('auth'),{status:401});},upstoxIntraday:async()=>payload});
 for(const key of ['NSE_EQ|A','NSE_EQ|B'])assert.deepEqual((await router.intraday(key,{})).data,payload.data);
 assert.equal(router.status().indstocks,0);assert.equal(router.status().upstox,2);assert.equal(router.status().failures,0);
});
