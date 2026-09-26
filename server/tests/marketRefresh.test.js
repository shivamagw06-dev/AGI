import assert from 'node:assert/strict';
import {
  MARKET_REFRESH_MS,
  getMarketCycle,
  oncePerMarketCycle,
  formatMarketUpdatedLabel,
} from '../config/marketRefresh.js';

assert.equal(MARKET_REFRESH_MS, 30 * 60 * 1000);

const cycle = getMarketCycle(1_700_000_000_000);
assert.equal(cycle.cycleId, String(Math.floor(1_700_000_000_000 / MARKET_REFRESH_MS) * MARKET_REFRESH_MS));
assert.ok(cycle.msRemaining >= 0 && cycle.msRemaining <= MARKET_REFRESH_MS);

let runs = 0;
const a = await oncePerMarketCycle('unit-test-key', async () => {
  runs += 1;
  return { ok: true, n: runs };
});
const b = await oncePerMarketCycle('unit-test-key', async () => {
  runs += 1;
  return { ok: true, n: runs };
});
assert.equal(a.n, 1);
assert.equal(b.n, 1);
assert.equal(runs, 1);
assert.equal(a.marketCycleId, getMarketCycle().cycleId);
assert.ok(formatMarketUpdatedLabel(new Date()).startsWith('Updated '));

console.log('marketRefresh.test.js OK');
