import assert from 'node:assert/strict';
import test from 'node:test';
import { buildCrossSectionalFeatureSnapshots, robustScale } from './crossSectionalForecastFeatures.js';

const event = (id, symbol, sector, score) => ({
  id, symbol, sector, captured_at: '2026-08-11T10:10:00Z',
  fundamental_score: score, valuation_score: score, eod_confirmation: score,
  live_confirmation: score, catalyst_score: score, leadership: score,
  activity: score, breakout: score, dislocation: score, positioning: score,
  research_priority: score, classification: 'WATCH', market_regime: 'NEUTRAL',
});

test('robust scaling winsorizes an extreme value and stays finite', () => {
  const score = robustScale([10, 20, 30, 40, 10_000], 10_000);
  assert.equal(Number.isFinite(score), true);
  assert.ok(score < 10);
});

test('creates same-day market and sector-relative point-in-time features', () => {
  const rows = buildCrossSectionalFeatureSnapshots([
    event('a', 'AAA', 'BANKS', 20), event('b', 'BBB', 'BANKS', 50),
    event('c', 'CCC', 'BANKS', 80), event('d', 'DDD', 'IT', 60),
  ]);
  assert.equal(rows.length, 4);
  assert.equal(rows[0].feature_version, 'agi_cross_sectional_daily_v2');
  assert.equal(rows[0].features.cross_sectional.universe_size, 4);
  assert.equal(rows[0].features.cross_sectional.sector_size, 3);
  assert.ok(rows[0].features.cross_sectional.market_z.fundamental < 0);
  assert.ok(rows[2].features.cross_sectional.sector_z.fundamental > 0);
  assert.equal(rows.every((row) => row.point_in_time_safe), true);
});

test('records missing factors instead of imputing future information', () => {
  const missing = event('a', 'AAA', 'BANKS', 20); missing.valuation_score = null;
  const rows = buildCrossSectionalFeatureSnapshots([missing, event('b', 'BBB', 'BANKS', 50), event('c', 'CCC', 'BANKS', 80)]);
  assert.equal(rows[0].features.cross_sectional.missing.valuation, true);
  assert.equal(rows[0].features.cross_sectional.market_z.valuation, null);
  assert.ok(rows[0].completeness < rows[1].completeness);
});
