import test from 'node:test';
import assert from 'node:assert/strict';
import {liveAlphaSnapshotDisplay as display} from './liveAlphaSnapshotDisplay.js';
const saved={freshness:{stale:true,latest_successful_at:'2026-10-08T09:55:00Z'},signals:[{direction:'positive'}],runtime:{evaluation_status:'market_closed'},now:Date.parse('2026-10-11T10:00:00Z')};
test('closed sessions and weekends retain dated saved signals',()=>assert.deepEqual(display(saved),{historical:true,withheld:false}));
test('reopening does not turn stale history into current signals',()=>assert.deepEqual(display({...saved,runtime:{evaluation_status:'degraded'}}),{historical:false,withheld:true}));
test('failed requests, missing snapshots and future timestamps remain withheld',()=>{
 for(const change of [{requestFailed:true},{signals:[]},{freshness:{stale:true}},{now:Date.parse('2026-10-07T10:00:00Z')}])assert.equal(display({...saved,...change}).withheld,true);
});
test('fresh open-session signals still display normally',()=>assert.deepEqual(display({...saved,runtime:{evaluation_status:'live'},freshness:{...saved.freshness,stale:false}}),{historical:false,withheld:false}));
