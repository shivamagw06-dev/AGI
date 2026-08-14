import test from 'node:test';
import assert from 'node:assert/strict';
import { enrichStrategyLabWithLiveMarket } from './strategyLabLiveMarket.js';

test('live enrichment preserves EOD prices and adds a separately labelled quote', () => {
  const payload = { session_health: { latest_completed_session: '2026-08-13' }, signals: [{ ticker: 'RADICO', entry: 4340.8, prices: { signal_price: 4340.8 } }] };
  const liveSnapshot = { provider: 'upstox', status: 'connected', quotes: { RADICO: { ltp: 4617, source: 'upstox', received_at: '2026-08-14T06:31:00.000Z', quote_age_ms: 1000, data_quality: 'PASS', reason_codes: [] } } };
  const result = enrichStrategyLabWithLiveMarket(payload, { now: new Date('2026-08-14T06:31:01.000Z'), liveSnapshot });
  assert.equal(result.signals[0].entry, 4340.8);
  assert.equal(result.signals[0].prices.signal_price, 4340.8);
  assert.equal(result.signals[0].prices.live_price, 4617);
  assert.equal(result.clocks.signal.completed_session, '2026-08-13');
  assert.equal(result.clocks.market.local_time, '12:01:01 IST');
});
