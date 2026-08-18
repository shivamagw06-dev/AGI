import assert from 'node:assert/strict';
import test from 'node:test';
import { buildCanonicalSignals } from './liveAlphaSignalModel.js';
import {
  buildLiveBrief,
  buildMarketBehaviorRows,
  buildMarketMap,
  filterRadarRows,
  marketStateFromBrief,
} from './liveAlphaDashboardModel.js';

const signal = (engine, symbol, score, sector = 'BANKS') => ({
  id: `${engine}-${symbol}`,
  symbol,
  sector,
  engine,
  direction: score > 0 ? 'positive' : 'negative',
  alpha_z: Math.abs(score) / 28,
  signal_quality_score: 80,
  liquidity_ok: true,
  as_of: '2026-08-19T06:00:00Z',
});

test('live brief is deterministic and does not invent missing sectors', () => {
  const rows = buildCanonicalSignals([
    signal('cross_sectional_momentum_v1', 'ICICIBANK', 80, 'BANKS'),
    signal('volume_liquidity_anomaly_v1', 'ICICIBANK', 70, 'BANKS'),
    signal('cross_sectional_momentum_v1', 'INFY', -60, 'IT'),
  ]);
  const brief = buildLiveBrief(rows, { isFresh: true, now: new Date('2026-08-19T06:30:00Z') });
  assert.match(brief.headline, /positive|mixed|negative/i);
  assert.equal(brief.top_positive[0].symbol, 'ICICIBANK');
  assert.equal(brief.evidence_strength, 'LOW');
  assert.ok(['positive', 'warning', 'mixed'].includes(marketStateFromBrief(brief).tone) || marketStateFromBrief(brief).label === 'Mixed');
  assert.equal(marketStateFromBrief(brief).label, 'Mixed');
});

test('market map withholds when sectors are insufficient', () => {
  const rows = buildCanonicalSignals([signal('cross_sectional_momentum_v1', 'A', 50, 'BANKS')]);
  const map = buildMarketMap(rows, { isFresh: true });
  assert.equal(map.available, false);
});

test('market behavior rows expose plain-language intensity', () => {
  const rows = buildCanonicalSignals([
    signal('cross_sectional_momentum_v1', 'A', 50),
    signal('cross_sectional_momentum_v1', 'B', 40),
  ]);
  const behavior = buildMarketBehaviorRows(rows, { cross_sectional_momentum_v1: { stored_signals: 20, status: 'ready' } }, true);
  const leadership = behavior.find((row) => row.engine === 'cross_sectional_momentum_v1');
  assert.equal(leadership.active, 2);
  assert.ok(leadership.intensity.label);
});

test('radar filters preserve research language buckets', () => {
  const rows = buildCanonicalSignals([
    signal('cross_sectional_momentum_v1', 'ICICIBANK', 80),
    signal('volume_liquidity_anomaly_v1', 'ICICIBANK', -70),
  ]);
  assert.equal(filterRadarRows(rows, 'conflicting').length, 1);
  assert.equal(filterRadarRows(rows, 'positive').length, 0);
});
