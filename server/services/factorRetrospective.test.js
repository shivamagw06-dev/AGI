import test from 'node:test';
import assert from 'node:assert/strict';
import {collectRetrospective,retrospectiveView,retrospectiveDates,createFactorRangeReader,verifiedNseBars} from './factorRetrospective.js';
const now=new Date('2026-09-16T12:00:00Z'),snapshot='test',c=Array.from({length:50},(_,i)=>({symbol:'S'+i,instrumentKey:'NSE_EQ|'+i}));
const saved=()=>({snapshot,startDate:'2026-09-15',securities:Object.fromEntries(c.slice(0,25).map(h=>[h.symbol,{instrumentKey:h.instrumentKey,bars:{'2026-09-15':100,'2026-09-16':110}}]))});
test('retrospective basket starts at 100, excludes reserves, and does not mutate ledger',()=>{const s=saved(),copy=structuredClone(s),v=retrospectiveView(s,c,snapshot,now);assert.equal(v.history[0].value,100);assert.ok(Math.abs(v.returnPct-10)<1e-8);assert.equal(v.status,'complete');assert.equal(v.holdings.length,50);assert.deepEqual(s,copy);});
test('missing baseline never changes start date or renormalizes weights',()=>{const s=saved();delete s.securities.S0.bars['2026-09-15'];const v=retrospectiveView(s,c,snapshot,now);assert.equal(v.returnPct,null);assert.equal(v.history.length,0);assert.deepEqual(v.missingBaseline,['S0']);});
test('wrong instrument and snapshot cannot produce returns',()=>{const s=saved();s.securities.S0.instrumentKey='wrong';assert.equal(retrospectiveView(s,c,snapshot,now).returnPct,null);assert.equal(retrospectiveView(s,c,'other',now).returnPct,null);});
test('calendar excludes incomplete day and weekends',()=>{assert.deepEqual(retrospectiveDates(new Date('2026-09-15T09:00:00Z')),[]);assert.equal(retrospectiveDates(new Date('2026-09-20T12:00Z')).at(-1),'2026-09-18');});
test('collector persists bounded partial evidence separately and retries missing data',async()=>{const doc={events:[{type:'rebalance'}],history:[{nav:98}],portfolio:{holdings:c}},copy=structuredClone(doc);let calls=0;const read=async h=>{calls++;return {instrumentKey:h.instrumentKey,bars:{'2026-09-15':100}};};const out=await collectRetrospective(doc,c,snapshot,read,now,5);assert.equal(calls,5);assert.equal(Object.keys(out.securities).length,5);assert.deepEqual(doc,copy);const again=await collectRetrospective({...doc,factorRetrospective:out},c,snapshot,read,now,5);assert.equal(Object.keys(again.securities).length,10);});
test('reader validates OHLC, excludes future bars and uses daily range once',async()=>{
 let url;
 const candles=[['2026-09-15T00:00:00+05:30',100,110,90,105],['2026-09-16T00:00:00+05:30',100,90,100,105],['2026-09-17T00:00:00+05:30',100,110,90,106]];
 const reader=createFactorRangeReader({token:()=> 'test-only',fetcher:async(_p,u)=>{url=u;return {ok:true,json:async()=>({status:'success',data:{candles}})};}});
 const out=await reader(c[0],'2026-09-16');assert.ok(url.endsWith('/days/1/2026-09-16/2026-09-15'));assert.deepEqual(out.bars,{'2026-09-15':105});
});

test('NSE archive gap supplement requires both symbol and instrument identity',async()=>{
 const h={symbol:'ZEEL',instrumentKey:'NSE_EQ|INE256A01028',weight:100};const bars=verifiedNseBars(h,'2026-10-21');assert.equal(bars['2026-09-15'],77.41);assert.equal(Object.keys(bars).length,25);assert.deepEqual(verifiedNseBars({...h,instrumentKey:'wrong'},'2026-10-21'),{});
 let reads=0;const doc={history:[{nav:96}],events:[{type:'opening'}]},copy=structuredClone(doc);const out=await collectRetrospective(doc,[h],'test',async()=>{reads++;throw Error('Provider gap');},new Date('2026-10-21T14:00Z'));assert.equal(reads,0);assert.equal(out.securities.ZEEL.verifiedNse,true);assert.equal(out.securities.ZEEL.bars['2026-09-15'],77.41);assert.deepEqual(doc,copy);
});
