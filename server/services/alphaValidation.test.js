import assert from 'node:assert/strict';
import test from 'node:test';
import { evaluateSignalOutcomes, validateAcrossHorizons } from './alphaValidation.js';

const observations = [
  { signalScore: 2.2, strategyReturn: 0.32, benchmarkReturn: 0.10, estimatedCostBps: 2, turnover: 1 },
  { signalScore: 1.4, strategyReturn: 0.18, benchmarkReturn: 0.08, estimatedCostBps: 2, turnover: 1 },
  { signalScore: -1.8, strategyReturn: -0.25, benchmarkReturn: -0.05, estimatedCostBps: 2, turnover: 1 },
  { signalScore: -0.9, strategyReturn: 0.02, benchmarkReturn: 0.08, estimatedCostBps: 2, turnover: 1 },
];

test('calculates net, cost-aware signal performance', () => {
  const result = evaluateSignalOutcomes(observations, { horizon: '1h', minimumSample: 3 });
  assert.equal(result.sample_size, 4);
  assert.equal(result.validation_status, 'eligible');
  assert.equal(result.hit_rate_pct, 50);
  assert.equal(result.average_estimated_cost_bps, 2);
  assert.ok(result.information_coefficient > 0.9);
  assert.ok(result.net_alpha_pct < result.gross_alpha_pct);
});

test('does not promote small samples', () => {
  const result = evaluateSignalOutcomes(observations, { horizon: '15m', minimumSample: 100 });
  assert.equal(result.validation_status, 'insufficient_sample');
});

test('returns every required forecast horizon', () => {
  const results = validateAcrossHorizons({ '1h': observations });
  assert.deepEqual(results.map((row) => row.horizon), ['5m', '15m', '30m', '1h', 'close', 'next_day', '5d']);
});
