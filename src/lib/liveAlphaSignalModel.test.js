import test from 'node:test';
import assert from 'node:assert/strict';

import { buildCanonicalSignals, confidenceBasis, confidenceLabel } from './liveAlphaSignalModel.js';


test('sample count never manufactures a validation claim', () => {
  assert.equal(confidenceLabel(80, 100), 'SAMPLE-RICH');
  assert.match(confidenceBasis(100), /not research validation/i);
});


test('canonical signals remain research-only after the sample threshold', () => {
  const rows = buildCanonicalSignals([
    {
      id: 'signal-1', symbol: 'TEST', engine: 'cross_sectional_momentum_v1',
      direction: 'positive', alpha_z: 2, signal_quality_score: 80,
      empirical_confidence_score: 80, comparable_observations: 100,
      as_of: '2026-08-23T09:30:00Z', liquidity_ok: true,
    },
  ]);
  assert.equal(rows[0].validation_status, 'SAMPLE THRESHOLD MET');
  assert.equal(rows[0].strategy_status, 'RESEARCH ONLY');
  assert.notEqual(rows[0].validation_status, 'RESEARCH VALIDATED');
});

test('mixed timestamps cannot create false agreement or borrow another components sample count', () => {
  const base = {symbol:'TEST', direction:'positive', alpha_z:2, signal_quality_score:90, liquidity_ok:true, as_of:'2026-10-01T09:55:00Z'};
  let [r] = buildCanonicalSignals([{...base,engine:'cross_sectional_momentum_v1',comparable_observations:200}, {...base,engine:'volume_liquidity_anomaly_v1',comparable_observations:0}]);
  assert.equal(r.samples,0);
  assert.equal(r.confidence,'MODEL-ONLY');
  assert.equal(r.input_data_status,'REVIEW REQUIRED');
  [r] = buildCanonicalSignals([{...base,engine:'cross_sectional_momentum_v1'}, {...base,engine:'volume_liquidity_anomaly_v1',as_of:'2026-10-01T09:50:00Z'}]);
  assert.equal(r.active.length,1);
  assert.equal(r.excluded_components.length,1);
});
