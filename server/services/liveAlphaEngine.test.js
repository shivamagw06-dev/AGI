import assert from 'node:assert/strict';
import test from 'node:test';
import { evaluateCrossSectionalMomentum } from './liveAlphaEngine.js';

function universe(size = 20) {
  return Array.from({ length: size }, (_, index) => ({
    symbol: `STOCK${index + 1}`,
    sector: index < 10 ? 'BANKS' : 'IT',
    instrumentKey: `NSE_EQ|TEST${index + 1}`,
    return15m: index * 0.12 - 1,
    return60m: index * 0.25 - 2,
    benchmarkReturn15m: 0.2,
    benchmarkReturn60m: 0.4,
    sectorReturn15m: index < 10 ? 0.1 : -0.1,
    sectorReturn60m: index < 10 ? 0.2 : -0.2,
    cumulativeVolume: 100_000 + index * 12_000,
    expectedCumulativeVolume: 100_000,
    spreadBps: 8,
  }));
}

test('ranks residual momentum and selects both research tails', () => {
  const result = evaluateCrossSectionalMomentum(universe(), { asOf: '2026-08-09T06:00:00Z' });
  assert.equal(result.research_only, true);
  assert.equal(result.execution_enabled, false);
  assert.equal(result.tail_size, 2);
  assert.equal(result.signals[0].symbol, 'STOCK20');
  assert.equal(result.signals[0].classification, 'positive_research_candidate');
  assert.equal(result.signals[0].signal_quality.empirical, false);
  assert.equal(result.signals[0].empirical_confidence.status, 'unvalidated');
  assert.equal(result.signals.at(-1).classification, 'negative_research_candidate');
  assert.equal('order' in result.signals[0], false);
});

test('filters illiquid names even when their score is extreme', () => {
  const rows = universe();
  rows.at(-1).spreadBps = 90;
  const result = evaluateCrossSectionalMomentum(rows);
  assert.equal(result.signals.find((row) => row.symbol === 'STOCK20').classification, 'filtered');
});

test('rejects undersized universes, duplicate symbols and invalid weights', () => {
  assert.throws(() => evaluateCrossSectionalMomentum(universe(5)), /at least 10/);
  const duplicate = universe();
  duplicate[1].symbol = duplicate[0].symbol;
  assert.throws(() => evaluateCrossSectionalMomentum(duplicate), /unique/);
  assert.throws(() => evaluateCrossSectionalMomentum(universe(), { weights: { residual15m: 1 } }), /sum to 1/);
});

test('removes benchmark and sector moves before ranking', () => {
  const rows = universe();
  rows[10] = {
    ...rows[10], symbol: 'RAWLEADER', return15m: 3, return60m: 5,
    benchmarkReturn15m: 1, benchmarkReturn60m: 2,
    sectorReturn15m: 2, sectorReturn60m: 3,
  };
  const result = evaluateCrossSectionalMomentum(rows);
  const leader = result.signals.find((row) => row.symbol === 'RAWLEADER');
  assert.equal(leader.residual_15m, 0);
  assert.equal(leader.residual_60m, 0);
  assert.notEqual(leader.rank, 1);
});
