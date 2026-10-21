import test from 'node:test';
import assert from 'node:assert/strict';
import { EarlyRadar, setupInputs } from './liveAlphaEarlyRadar.js';
const now = new Date('2026-10-09T06:30:30Z');
function fixture() {
 const minute = Math.floor(+now/60000)*60000;
 const points = Array.from({length:15},(_,i)=>({received_at:new Date(minute-(15-i)*60000).toISOString(),ltp:100+i*.02,cumulative_volume:1000+i*100}));
 const benchmark=[{received_at:new Date(minute-15*60000).toISOString(),ltp:100},{received_at:now.toISOString(),ltp:100}];
 const quote={ltp:100.26,effective_timestamp:now.toISOString(),best_bid:100.25,best_ask:100.27,cumulative_volume:2700};
 return {points,benchmark,quote,now};
}
test('prior-only level ignores current and future observations',()=>{
 const f=fixture();f.points.push({received_at:now.toISOString(),ltp:999,cumulative_volume:9999});
 const x=setupInputs(f);assert.equal(x.level,100.28);assert.equal(x.direction,'positive');
});
test('missing minute, stale quote, reset volume and missing depth are blocked',()=>{
 let f=fixture();f.points.pop();assert.ok(setupInputs(f).blocked);
 f=fixture();f.quote.effective_timestamp=new Date(+now-31000).toISOString();assert.ok(setupInputs(f).blocked);
 f=fixture();f.quote.cumulative_volume=0;assert.ok(setupInputs(f).blocked);
 f=fixture();f.quote.best_bid=null;assert.ok(setupInputs(f).blocked);
});
function radarFixture(){
 const f=fixture();const radar=new EarlyRadar({featureStore:{series:new Map([['s',f.points],['b',f.benchmark]])},quoteStore:{get:()=>f.quote},universe:[{symbol:'TEST',instrumentKey:'s'}],benchmarkKey:'b'});
 return {f,radar};
}
test('watch to trigger freezes price and level, then records failure without rewriting entry',async()=>{
 const {f,radar}=radarFixture();await radar.evaluate(now);let row=radar.episodes.get('TEST');assert.equal(row.stage,'watch');
 const later=new Date(+now+30000);f.quote.ltp=100.4;f.quote.effective_timestamp=later.toISOString();f.quote.cumulative_volume=2900;f.benchmark.push({received_at:later.toISOString(),ltp:100});
 // Supply the next completed minute to keep the input window complete.
 f.points.push({received_at:new Date(+now-30000).toISOString(),ltp:100.26,cumulative_volume:2600});
 await radar.evaluate(later);row=radar.episodes.get('TEST');assert.equal(row.stage,'triggered');assert.equal(row.level,100.28);assert.equal(row.trigger_price,100.4);
 const fail=new Date(+later+30000);f.quote.ltp=100;f.quote.effective_timestamp=fail.toISOString();await radar.evaluate(fail);
 assert.equal(row.stage,'failed');assert.equal(row.trigger_price,100.4);assert.deepEqual(radar.events.map(x=>x.stage),['watch','triggered','failed']);assert.equal(radar.events[1].current_price,100.4);
});
test('large jump is extended and is not presented as a trigger',async()=>{
 const {f,radar}=radarFixture();f.quote.ltp=101.2;f.quote.best_bid=101.19;f.quote.best_ask=101.21;await radar.evaluate(now);
 assert.equal(radar.episodes.get('TEST').stage,'extended');assert.equal(radar.episodes.get('TEST').trigger_price,undefined);
});
test('checkpoint restores frozen entries and stale state; save failure is visible',async()=>{
 const {radar}=radarFixture();radar.save=async()=>{throw new Error('disk')};await radar.evaluate(now);assert.match(radar.snapshot(now).storage_error,/pending retry/);
 const other=radarFixture().radar;other.restore({version:'early-range-v1',episodes:[...radar.episodes.values()],events:radar.events});assert.equal(other.episodes.get('TEST').level,100.28);assert.equal(other.snapshot(now).stale,true);
});
test('closed session and same bucket do not publish extra events',async()=>{
 const {radar}=radarFixture();await radar.evaluate(new Date('2026-10-10T06:30:30Z'));assert.equal(radar.events.length,0);
 await radar.evaluate(now);await radar.evaluate(new Date(+now+1000));assert.equal(radar.events.length,1);
});
test('negative setup mirrors direction and confirmation keeps first price',async()=>{
 const {f,radar}=radarFixture();f.points.forEach((p,i)=>p.ltp=100.28-i*.02);f.quote.ltp=99.85;f.quote.best_bid=99.84;f.quote.best_ask=99.86;
 await radar.evaluate(now);let row=radar.episodes.get('TEST');assert.equal(row.stage,'triggered');assert.equal(row.direction,'negative');assert.equal(row.level,100);
 const later=new Date(+now+60000);f.quote.ltp=99.65;f.quote.effective_timestamp=later.toISOString();await radar.evaluate(later);assert.equal(row.stage,'confirmed');assert.equal(row.trigger_price,99.85);assert.ok(row.return_pct>0);
});
test('stale prices cannot confirm a trigger',async()=>{
 const {f,radar}=radarFixture();f.quote.ltp=100.4;await radar.evaluate(now);const row=radar.episodes.get('TEST');assert.equal(row.stage,'triggered');f.quote.ltp=101;
 await radar.evaluate(new Date(+now+90000));assert.equal(row.stage,'triggered');assert.equal(row.current_price,100.4);assert.equal(radar.snapshot(new Date(+now+90000)).rows[0].quote_stale,true);
});
