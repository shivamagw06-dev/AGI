import test from 'node:test';
import assert from 'node:assert/strict';
import {publicationDueAt,publicationRows,eligibleQuote,stockReturn,directionReturn,simulatedReturn,chartRows,entryRow} from './liveAlphaPublicationModel.js';
import {buildCanonicalSignals} from '../../src/lib/liveAlphaSignalModel.js';
import {settlePublicationFollowup,collectPublicationEntries} from './liveAlphaArchiveCollector.js';
import {archiveFilters,dailyPriceSeries} from './liveAlphaArchive.js';
import {publishAlphaSnapshot} from './liveAlphaPublications.js';
const now=new Date('2026-10-01T05:00:00Z');
const signals=[{symbol:'TEST',instrument_key:'NSE_EQ|TEST',as_of:now.toISOString(),engine:'momentum',direction:'positive',alpha_z:1.7,signal_quality_score:50,price_at_signal:100,nifty_at_signal:22000,price_quote_at:'2026-10-01T04:59:45Z'}, {symbol:'TEST',instrument_key:'NSE_EQ|TEST',as_of:now.toISOString(),engine:'volume',direction:'negative',alpha_z:1.4,signal_quality_score:40}];
test('archive composite matches the actual displayed signal, including conflicts and older exclusion',()=>{
 const input=[...signals,{...signals[0],as_of:'2026-09-30T05:00:00Z',engine:'old'}];
 const [r]=publicationRows(input,now),[canonical]=buildCanonicalSignals(input);
 assert.equal(r.score,canonical.composite);assert.equal(r.direction,'conflicting');assert.equal(r.components.length,2);assert.equal(r.quality.quote_fresh,true);
});
test('fixed horizons respect Gandhi Jayanti and weekend; trading minutes carry over',()=>{
 assert.equal(publicationDueAt('2026-10-01T09:55:00Z','15m'),'2026-10-05T03:55:00.000Z');
 assert.equal(publicationDueAt(now.toISOString(),'1d'),'2026-10-05T10:00:00.000Z');
 assert.equal(publicationDueAt(now.toISOString(),'5d'),'2026-10-09T10:00:00.000Z');
});
const quote=(at,extra={})=>({exchange_timestamp:at,observed_at:at,best_bid:99,best_ask:100,ltp:99.5,...extra});
test('entry uses strictly post-publication timestamp, valid receive time and correct side',()=>{
 const rows=[quote('2026-10-01T04:59:59Z'),quote('2026-10-01T05:00:00Z'),quote('2026-10-01T05:00:01Z',{observed_at:null}),quote('2026-10-01T05:00:02Z',{best_bid:101}),quote('2026-10-01T05:00:03Z')];
 assert.equal(eligibleQuote(rows,now.toISOString(),'positive').price,100);
 assert.equal(eligibleQuote(rows,now.toISOString(),'negative').price,99);
 assert.equal(eligibleQuote(rows,now.toISOString(),'positive').observed_at,'2026-10-01T05:00:03Z');
 assert.equal(eligibleQuote(rows,now.toISOString(),'conflicting'),null);
 assert.equal(eligibleQuote([quote('2026-10-01T05:06:00Z')],now.toISOString(),'positive'),null);
});
test('buying a falling stock loses even if a negative signal was correct; costs reduce simulations',()=>{
 assert.ok(Math.abs(stockReturn(100,90)+10)<1e-9);assert.ok(directionReturn('negative',stockReturn(100,90))>0);
 assert.equal(stockReturn(null,90),null);assert.equal(stockReturn(100,null),null);assert.equal(directionReturn('conflicting',10),null);
 assert.ok(simulatedReturn('positive',{price:100},{price:100})<-.19);
 assert.ok(simulatedReturn('negative',{price:100},{price:90})<10);
});
test('missing prices stay null and chart gaps are explicit',()=>{
 const rows=chartRows({published_at:now.toISOString(),reference_price:100,benchmark_price:200},[{session_date:'2026-10-01',price:null,observed_at:'2026-10-01T10:00:00Z'}],[]);
 assert.equal(rows[1].price,null);assert.equal(rows[1].stock_return_pct,null);assert.equal(rows[1].benchmark_return_pct,null);
});
test('one-to-one entry relation supports PostgREST object and test array shapes',()=>{assert.equal(entryRow({price:10}).price,10);assert.equal(entryRow([{price:10}]).price,10);assert.equal(entryRow(null),null);});
test('a session close never settles at a 15:29 live price',async()=>{
 const row={due_at:'2026-10-01T10:00:00Z',horizon:'close',publication:{instrument_key:'TEST',reference_price:100}};
 const result=await settlePublicationFollowup(row,{now:new Date('2026-10-01T10:01:00Z'),request:async()=>[quote('2026-10-01T09:59:20Z')]});assert.equal(result.status,'pending');assert.equal(result.price,undefined);
 const settled=await settlePublicationFollowup(row,{now:new Date('2026-10-04T05:00:00Z'),request:async()=>[],book:{closeOn:async()=>({price:102,candle_end:'2026-10-01T10:00:00Z'})}});
 assert.equal(settled.status,'completed');assert.equal(settled.price,102);assert.equal(settled.simulated_net_return_pct,null);
});
test('missing follow-ups expire honestly instead of recording zero returns',async()=>{
 const row={due_at:'2026-09-21T05:00:00Z',horizon:'15m',publication:{instrument_key:'TEST',reference_price:100}};
 const result=await settlePublicationFollowup(row,{now,request:async()=>[],book:{priceAt:async()=>({price:null})}});assert.equal(result.status,'missing');assert.equal(result.stock_return_pct,undefined);
});
test('invalid filters reject injection and invalid calendar dates',()=>{
 assert.throws(()=>archiveFilters({symbol:'a,b)'},now));assert.throws(()=>archiveFilters({from:'2026-02-30'},now));assert.throws(()=>archiveFilters({to:'2027-01-01'},now));
});
test('daily chart cache preserves gaps and only stores actual prices',async()=>{
 const writes=[];const rows=await dailyPriceSeries('TEST','2026-09-30','2026-10-05',{request:async(t,o)=>{if(o.method==='GET')return [];writes.push(...o.body);},book:{closeOn:async(k,d)=>({price:d==='2026-10-01'?null:100})}});
 assert.deepEqual(rows.map(r=>r.session_date),['2026-09-30','2026-10-01','2026-10-05']);assert.equal(writes.length,2);
});
test('market closed and partially failed evaluations cannot become published calls',async()=>{
 const request=async()=>{throw new Error('must not publish');};
 assert.equal((await publishAlphaSnapshot([],[],{request,now:new Date('2026-10-04')})).skipped,'market_closed');
 assert.equal((await publishAlphaSnapshot([],[{status:'failed'}],{request,now})).skipped,'partial_engine_failure');
 assert.equal((await publishAlphaSnapshot([],[{status:'stored',rejected_signals:1}],{request,now})).skipped,'partial_engine_failure');
});
test('entry collection never re-enters a one-to-one entry already captured',async()=>{
 let queries=0;const result=await collectPublicationEntries({now,request:async()=>{queries++;return [{direction:'positive',quality:{quote_fresh:true},entries:{price:100}}];}});assert.equal(result,0);assert.equal(queries,1);
});

test('close simulation never exits before its post-publication entry',async()=>{
 const row={due_at:'2026-10-01T10:00:00Z',horizon:'close',publication:{direction:'positive',instrument_key:'TEST',reference_price:100,entries:{price:100,observed_at:'2026-10-01T09:59:50Z'}}};
 const result=await settlePublicationFollowup(row,{now:new Date('2026-10-04T05:00:00Z'),request:async()=>[quote('2026-10-01T09:59:10Z')],book:{closeOn:async()=>({price:102,candle_end:'2026-10-01T10:00:00Z'})}});
 assert.equal(result.stock_return_pct,2.0000000000000018);assert.equal(result.simulated_net_return_pct,null);
});
