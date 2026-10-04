import test from 'node:test';
import assert from 'node:assert/strict';
import { buildLiveAlphaSetups } from './liveAlphaSetupModel.js';

const now = new Date('2026-09-25T05:00:00Z');
const live = { freshness: { stale: false }, runtime: { market_session: { open: true }, feed: { status: 'connected' }, evaluation_status: 'live' }, now };
const signal = (engine, direction, overrides = {}) => ({
  engine, direction, as_of: '2026-09-25T04:59:00Z', price_at_signal: 100,
  liquidity_ok: true, liquidity_verified: true, ...overrides,
});
const row = (signals, overrides = {}) => ({
  symbol: 'TEST', sector: 'IT', active: signals, signal_structure: 'SINGLE-FACTOR POSITIVE',
  newest: '2026-09-25T04:59:00Z', price_as_of: '2026-09-25T04:59:30Z',
  live_price: 101, confidence: 'MODEL-ONLY', composite: 55, ...overrides,
});

test('shows directional setup and a measured range projection with timestamps', () => {
  const setups = buildLiveAlphaSetups([row([
    signal('opening_range_expansion_v1', 'positive', { factor_values: { opening_high: 100, opening_low: 98 } }),
    signal('cross_sectional_momentum_v1', 'positive'),
  ])], live);
  assert.equal(setups.length, 1);
  assert.equal(setups[0].price, 101);
  assert.equal(setups[0].target, 102);
  assert.equal(setups[0].engines.length, 2);
});

test('does not invent targets for engines without a measured opening range', () => {
  const [setup] = buildLiveAlphaSetups([row([signal('cross_sectional_momentum_v1', 'negative')], {
    signal_structure: 'SINGLE-FACTOR NEGATIVE', composite: -40,
  })], live);
  assert.equal(setup.direction, 'negative');
  assert.equal(setup.target, null);
});

test('withholds conflicting, old, unverified, unsynchronized and disconnected setups', () => {
  const base = row([signal('cross_sectional_momentum_v1', 'positive')]);
  const conflicting = row([signal('cross_sectional_momentum_v1', 'positive'), signal('volume_liquidity_anomaly_v1', 'negative')], { signal_structure: 'CONFLICTING' });
  const oldPrice = row(base.active, { price_as_of: '2026-09-25T04:57:00Z' });
  const unverified = row([signal('cross_sectional_momentum_v1', 'positive', { liquidity_verified: null })]);
  const asyncComponents = row([signal('cross_sectional_momentum_v1', 'positive'), signal('volume_liquidity_anomaly_v1', 'positive', { as_of: '2026-09-25T04:50:00Z' })]);
  for (const candidate of [conflicting, oldPrice, unverified, asyncComponents]) {
    assert.equal(buildLiveAlphaSetups([candidate], live).length, 0);
  }
  assert.equal(buildLiveAlphaSetups([base], { ...live, runtime: { ...live.runtime, feed: { status: 'reconnecting' } } }).length, 0);
  assert.equal(buildLiveAlphaSetups([base], { ...live, freshness: { stale: true } }).length, 0);
});
