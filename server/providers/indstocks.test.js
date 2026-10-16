import test from 'node:test';
import assert from 'node:assert/strict';
import {cashInstrumentMap,normalizeIndstocksCandles,createIndstocksClient} from './indstocks.js';
const header='EXCH,SEGMENT,SERIES,ISIN,SECURITY_ID';
const csv=header+'\nNSE,E,EQ,INE062A01020,3045';
const start=Date.parse('2026-10-08T09:15:00+05:30');
const bar={ts:start/1000,o:100,h:102,l:99,c:101,v:50};
const response={success:true,data:{NSE_3045:{candles:[bar]}}};
test('master refuses ambiguity, wrong exchanges and series',()=>{
 assert.equal(cashInstrumentMap(csv).get('NSE_EQ|INE062A01020'),'NSE_3045');
 assert.equal(cashInstrumentMap(csv+'\nNSE,E,EQ,INE062A01020,123').get('NSE_EQ|INE062A01020'),null);
 assert.equal(cashInstrumentMap(header+'\nBSE,E,EQ,INE062A01020,3045\nNSE,E,BE,INE062A01020,3045').size,0);
});
test('timestamps are seconds; preserve OHLCV and reject malformed data',()=>{
 assert.deepEqual(normalizeIndstocksCandles(response,'NSE_3045',start,start+60000),[[new Date(start).toISOString(),100,102,99,101,50]]);
 for(const change of [{v:null},{h:90},{ts:start/1000-1},{o:NaN}])assert.throws(()=>normalizeIndstocksCandles({success:true,data:{NSE_3045:{candles:[{...bar,...change}]}}},'NSE_3045',start,start+60000));
 assert.throws(()=>normalizeIndstocksCandles({success:false},'NSE_3045',start,start+60000));
});
test('authenticated GETs only, one cached ISIN master, request spacing',async()=>{
 let clock=start+120000;const calls=[],waits=[];
 const client=createIndstocksClient({token:()=> 'secret',now:()=>clock,sleep:async n=>{waits.push(n);clock+=n;},fetchImpl:async(url,options)=>{calls.push({url,options});return {ok:true,status:200,text:async()=>csv,json:async()=>response};}});
 await client.history('NSE_EQ|INE062A01020',{},true);await client.history('NSE_EQ|INE062A01020',{},true);
 assert.equal(calls.length,3);assert.equal(calls[0].options.headers.Authorization,'secret');assert.equal(calls[1].options.method,undefined);assert.ok(waits.slice(1).every(n=>n===350));assert.equal(client.status().mapped_instruments,1);
 assert.ok(!JSON.stringify(client.status()).includes('secret'));
});
test('401 causes cooldown rather than repeated requests or secret errors',async()=>{
 let calls=0;const client=createIndstocksClient({token:()=> 'secret',now:()=>start+120000,sleep:async()=>{},fetchImpl:async()=>{calls++;return {ok:false,status:401};}});
 await assert.rejects(client.history('NSE_EQ|INE062A01020',{},true),e=>e.status===401&&!e.message.includes('secret'));
 await assert.rejects(client.history('NSE_EQ|INE062A01020',{},true));assert.equal(calls,1);assert.equal(client.status().cooling_down,true);
});
test('long minute range is paged at seven days, with exclusive bounds',async()=>{
 const calls=[];const client=createIndstocksClient({token:()=> 'secret',now:()=>Date.parse('2026-10-09T10:00:00Z'),sleep:async()=>{},fetchImpl:async url=>{calls.push(url);return {ok:true,status:200,text:async()=>csv,json:async()=>({success:true,data:{}})};}});
 await client.history('NSE_EQ|INE062A01020',{unit:'minutes',interval:1,from:'2026-09-25',to:'2026-10-08'});
 assert.equal(calls.length,3);const windows=calls.slice(1).map(u=>new URL(u).searchParams);
 assert.equal(windows[0].get('end_time'),windows[1].get('start_time'));
 assert.equal(+windows[0].get('end_time')- +windows[0].get('start_time'),7*86400000);
 await assert.rejects(client.history('NSE_INDEX|Nifty 50',{},true));
 await assert.rejects(client.history('NSE_EQ|INE062A01020',{unit:'days'},true));
});
