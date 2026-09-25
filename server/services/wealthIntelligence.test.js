import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeWealthQuote, getWealthUniverse } from './wealthIntelligence.js';
const now = Date.parse('2026-09-24T05:00:00Z');
const member = { symbol: 'TEST', name: 'Test Company', sector: 'CAPITAL_GOODS', instrumentKey: 'NSE_EQ|INE000000001' };
test('missing, stale, future and disconnected quotes cannot claim to be live', () => {
  const base = { ltp: 100, previous_close: 80, effective_timestamp: new Date(now).toISOString(), data_quality: 'PASS', source: 'upstox' };
  assert.equal(normalizeWealthQuote(member, base, now).status, 'live');
  assert.equal(normalizeWealthQuote(member, base, now).changePct, 25);
  for (const changes of [{ data_quality: 'BLOCKED' }, { effective_timestamp: null }, { effective_timestamp: '2026-09-23T05:00:00Z' }, { effective_timestamp: '2026-09-25T05:00:00Z' }]) {
    assert.equal(normalizeWealthQuote(member, { ...base, ...changes }, now).status, 'stale');
  }
  const missing = normalizeWealthQuote(member, { ltp: null }, now);
  assert.equal(missing.price, null); assert.equal(missing.status, 'unavailable');
});
test('searches existing universe and calls shared snapshot with its actual symbols', async () => {
  const result = await getWealthUniverse({ q: 'capital', limit: 25, offset: 0 }, {
    now: () => now, getUniverse: async () => [member], getSnapshot: symbols => {
      assert.deepEqual(symbols, ['TEST']); return { provider: 'upstox', status: 'disabled', quotes: {} };
    },
  });
  assert.equal(result.total, 1); assert.equal(result.items[0].status, 'unavailable');
  assert.equal(result.items[0].name, 'Test Company');
});
test('old published NAV remains stale even if successfully fetched today', async () => {
  const result = await getWealthUniverse({ assetClass: 'mutual_fund' }, {
    now: () => now, getNav: async () => ({ status: 'available', fetchedAt: new Date(now).toISOString(), rows: [{ name: 'Fund', asOf: '2026-09-01' }] }),
  });
  assert.equal(result.items[0].status, 'stale');
});
