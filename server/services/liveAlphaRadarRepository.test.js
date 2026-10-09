import test from 'node:test';import assert from 'node:assert/strict';import {RadarRepository} from './liveAlphaRadarRepository.js';
const event=(stage,time)=>({version:'early-range-v1',symbol:'TEST',session:'2026-10-09',event_at:time,stage,level:100});
test('journal appends once and state keeps latest transition in a batch',async()=>{
 const calls=[];const repo=new RadarRepository({transport:async(...x)=>{calls.push(x);return []}});
 const events=[event('watch','2026-10-09T05:00:00Z'),event('triggered','2026-10-09T05:01:00Z')];
 await repo.save({events});await repo.save({events});assert.equal(calls.length,2);assert.equal(calls[0][1].body.length,2);assert.equal(calls[1][1].body.length,1);assert.equal(calls[1][1].body[0].observation.stage,'triggered');
});
test('partial write failure is retried idempotently, not acknowledged early',async()=>{
 let fail=true;const calls=[];const repo=new RadarRepository({transport:async(table,options)=>{calls.push([table,options]);if(table.endsWith('state')&&fail)throw Error('offline');return []}});
 const events=[event('triggered','2026-10-09T05:00:00Z')];await assert.rejects(repo.save({events}));assert.equal(repo.saved.size,0);fail=false;await repo.save({events});assert.equal(calls[2][1].prefer,'resolution=ignore-duplicates,return=minimal');assert.equal(repo.saved.size,1);
});
test('restore obtains current session states and recent immutable events',async()=>{
 const e=event('triggered','2026-10-09T05:00:00Z');const repo=new RadarRepository({transport:async(table,{query})=>{assert.match(query,/session_date=eq.2026-10-09/);return[{observation:e}]}});
 const state=await repo.load(new Date('2026-10-09T06:00:00Z'));assert.equal(state.episodes[0].stage,'triggered');assert.equal(state.events.length,1);
});
