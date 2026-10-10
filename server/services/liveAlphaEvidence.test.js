import test from 'node:test';
import assert from 'node:assert/strict';
import {summarizeAlphaEvidence,getLiveAlphaEvidence} from './liveAlphaEvidence.js';

test('outcomes distinguish pending/missed, reject missing returns and disclose zero costs',()=>{
 const base={horizon:'15m',signal:{run:{engine:'momentum',as_of:'2026-10-01T06:00:00Z'}}};
 const report=summarizeAlphaEvidence([
  {...base,status:'completed',directional_return_pct:1,estimated_cost_bps:20},
  {...base,status:'completed',directional_return_pct:-.2,estimated_cost_bps:0},
  {...base,status:'completed',directional_return_pct:null,estimated_cost_bps:0},
  {...base,status:'pending'},{...base,status:'missed'},
 ]);
 const r=report.rows[0];
 assert.equal(r.completed,2);assert.equal(r.pending,1);assert.equal(r.missed,1);assert.equal(r.invalid,1);
 assert.ok(Math.abs(r.mean_net_directional_return_pct-.3)<1e-10);
 assert.equal(r.positive_outcome_pct,50);assert.equal(r.minimum_cost_bps,0);assert.equal(r.sessions,1);
 assert.equal(report.portfolio_backtest,false);
});
test('history query is bounded and only covers already-due outcomes',async()=>{
 let calls=0;
 const result=await getLiveAlphaEvidence({now:new Date('2026-10-04T07:00:00Z'),request:async(table,opts)=>{
  calls++; assert.equal(table,'live_alpha_signal_outcomes');
  const q=new URLSearchParams(opts.query);assert.match(q.get('and'),/due_at.lte/);assert.equal(q.get('limit'),'1000');
  return [];
 }});
 assert.equal(calls,2);assert.equal(result.sampled_rows,0);assert.equal(result.truncated,false);
});
