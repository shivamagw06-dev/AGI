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
