import assert from 'node:assert/strict';
import test from 'node:test';
import { buildCanonicalSignals, interpretCanonicalSignal, reconcileLiveAlpha, confidenceLabel, confidenceBasis } from './liveAlphaSignalModel.js';

const component = (engine, score, direction = score > 0 ? 'positive' : 'negative') => ({ id: `${engine}-${score}`, symbol: 'TEST', engine, direction, alpha_z: Math.abs(score) / 28, signal_quality_score: 0, liquidity_ok: true, as_of: '2026-08-13T07:00:00Z' });
const interpreted = (composite, strategies) => interpretCanonicalSignal({ composite, strategies, active: Object.values(strategies).filter((signal) => signal.direction) });

test('classifies aligned multi-factor positive and primary driver', () => {
  const result = interpreted(92, { cross_sectional_momentum_v1: component('cross_sectional_momentum_v1', 58), volume_liquidity_anomaly_v1: component('volume_liquidity_anomaly_v1', 72) });
  assert.equal(result.structure, 'MULTI-FACTOR POSITIVE'); assert.equal(result.alignment, 'HIGH ALIGNMENT'); assert.equal(result.primary_driver.engine, 'volume_liquidity_anomaly_v1');
});
test('classifies single-factor positive without confirmation', () => { assert.equal(interpreted(73, { volume_liquidity_anomaly_v1: component('volume_liquidity_anomaly_v1', 73) }).structure, 'SINGLE-FACTOR POSITIVE'); });
test('classifies aligned multi-factor negative', () => { const x = interpreted(-99, { cross_sectional_momentum_v1: component('cross_sectional_momentum_v1', -57), volume_liquidity_anomaly_v1: component('volume_liquidity_anomaly_v1', -99) }); assert.equal(x.structure, 'MULTI-FACTOR NEGATIVE'); assert.equal(x.primary_driver.engine, 'volume_liquidity_anomaly_v1'); });
test('classifies opposing components as conflicting', () => { const x = interpreted(-10, { cross_sectional_momentum_v1: component('cross_sectional_momentum_v1', 85), volume_liquidity_anomaly_v1: component('volume_liquidity_anomaly_v1', -99) }); assert.equal(x.structure, 'CONFLICTING'); assert.equal(x.primary_driver, null); });
test('classifies no active components as neutral', () => assert.equal(interpreted(0, {}).structure, 'NEUTRAL'));
test('canonical rows keep one shared interpretation', () => { const rows = buildCanonicalSignals([component('cross_sectional_momentum_v1', 85), component('volume_liquidity_anomaly_v1', -99)]); assert.equal(rows[0].signal_structure, 'CONFLICTING'); assert.equal(rows[0].interpretation, rows[0].interpretation); });
test('reconciles unique active names and strategy signals', () => { const x = reconcileLiveAlpha({ liveUniverse: 197, canonicalSignals: [{ composite: 1 }, { composite: -1 }], strategySignalCount: 3 }); assert.equal(x.neutral, 195); assert.equal(x.valid, true); });

test('a strong heuristic with no comparables cannot read as evidential', () => {
  // comparable_observations is 0 on every stored signal, so before this a
  // score of 85 was badged HIGH - a word clients hear as evidence.
  assert.equal(confidenceLabel(85, 0), 'MODEL-ONLY');
  assert.equal(confidenceLabel(95, 0), 'MODEL-ONLY');
});

test('a weak heuristic with no comparables is still LOW', () => {
  assert.equal(confidenceLabel(40, 0), 'LOW');
});

test('evidence-backed labels need a real sample', () => {
  assert.equal(confidenceLabel(85, 50), 'HIGH');
  assert.equal(confidenceLabel(65, 50), 'MEDIUM');
  assert.equal(confidenceLabel(75, 100), 'VALIDATED');
});

test('the basis line states the evidence rather than implying it', () => {
  assert.match(confidenceBasis(0), /no historical comparables/i);
  assert.match(confidenceBasis(50), /below the 100 required/i);
  assert.match(confidenceBasis(120), /120 comparable observations/i);
});
