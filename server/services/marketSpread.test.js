import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeSpreadBps, spreadWithinLimit } from './marketSpread.js';

test('a normal book gives a positive spread in bps', () => {
  // 100/101 is a 1 rupee spread on a 100.5 mid.
  assert.equal(normalizeSpreadBps(100, 101), 99.5025);
});

test('a crossed book is unknown, not negative', () => {
  // The Upstox feed computed this inline without the guard, so stale one-sided
  // quotes around the open and close produced negative spreads: 624 of 1,698
  // stored signals on 2026-08-19, bottoming at -599.99 bps.
  assert.equal(normalizeSpreadBps(101, 100), null);
});

test('a locked book has a spread of exactly zero', () => {
  assert.equal(normalizeSpreadBps(100, 100), 0);
});

test('missing or non-positive prices are unknown', () => {
  for (const [bid, ask] of [[null, 100], [100, null], [0, 100], [100, 0], [-5, 100], ['x', 100]]) {
    assert.equal(normalizeSpreadBps(bid, ask), null, `${bid}/${ask} should be null`);
  }
});

test('numeric strings are accepted', () => {
  assert.equal(normalizeSpreadBps('100', '101'), 99.5025);
});

test('a measured spread inside the limit passes and is verified', () => {
  assert.deepEqual(spreadWithinLimit(10, 35), { ok: true, verified: true, reason: 'within_limit' });
});

test('a measured spread beyond the limit fails', () => {
  assert.deepEqual(spreadWithinLimit(80, 35), { ok: false, verified: true, reason: 'spread_too_wide' });
});

test('an unmeasurable spread still passes but is not verified', () => {
  // Roughly a quarter of the universe has no usable quote at any moment.
  // Failing them closed would empty the board rather than improve it, but
  // unknown liquidity must not be reported as good liquidity.
  assert.deepEqual(spreadWithinLimit(null, 35), { ok: true, verified: false, reason: 'spread_unknown' });
});

test('a negative spread from stored history is never treated as tight', () => {
  // Rows written before the guard exist in the database. -599 bps would
  // otherwise sail through `spreadBps <= maximum`, so the widest books were
  // the most likely to clear the liquidity filter.
  const gate = spreadWithinLimit(-599.99, 35);
  assert.equal(gate.verified, false);
  assert.equal(gate.reason, 'spread_invalid');
});
