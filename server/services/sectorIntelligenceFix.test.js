import test from 'node:test';
import assert from 'node:assert/strict';
import { buildMiDegradedDashboard, buildMiDegradedSector } from './miDegraded.js';
import { growwSymbolForIndex } from './sectorIndexGrowwFallback.js';
import { isUpstoxAuthError } from './upstoxMarketFeedV3.js';

test('buildMiDegradedDashboard returns terminal shell', () => {
  const payload = buildMiDegradedDashboard('engine timeout');
  assert.equal(payload.ok, false);
  assert.equal(payload.degraded, true);
  assert.equal(payload.sectors.length, 0);
  assert.match(payload.error, /timeout/);
});

test('buildMiDegradedSector includes sector name', () => {
  const payload = buildMiDegradedSector('IT', 'offline');
  assert.equal(payload.sector, 'IT');
  assert.equal(payload.degraded, true);
});

test('growwSymbolForIndex maps Nifty Bank', () => {
  assert.equal(growwSymbolForIndex('NSE_INDEX|Nifty Bank'), 'NIFTYBANK');
});

test('isUpstoxAuthError detects 403', () => {
  assert.equal(isUpstoxAuthError(new Error('Unexpected server response: 403')), true);
  assert.equal(isUpstoxAuthError({ code: 'UPSTOX_AUTH_FAILED', message: 'x' }), true);
  assert.equal(isUpstoxAuthError(new Error('network timeout')), false);
});
