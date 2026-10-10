import assert from 'node:assert/strict';
import test from 'node:test';
import { analyseSector, classifyRotation, returnPct } from './growwSectorRotationRun.js';

function syntheticCandles(count, { start = 100, drift = 0.15 } = {}) {
  const rows = [];
  let price = start;
  for (let i = 0; i < count; i += 1) {
    price += drift;
    rows.push([`2025-01-${String(i + 1).padStart(2, '0')}`, price - 1, price + 1, price - 2, price, 1_000_000]);
  }
  return rows;
}

test('classifyRotation maps relative strength quadrants', () => {
  assert.equal(classifyRotation(2, 3), 'leading');
  assert.equal(classifyRotation(2, -1), 'improving');
  assert.equal(classifyRotation(-2, 3), 'weakening');
  assert.equal(classifyRotation(-2, -3), 'lagging');
});

test('analyseSector returns ingest-compatible sector rows', () => {
  const candles = syntheticCandles(140, { start: 100, drift: 0.2 });
  const benchmark = { return_20d: 1, return_60d: 2 };
  const result = analyseSector('NIFTYBANK', candles, benchmark);
  assert.ok(result);
  assert.equal(result.sector, 'NIFTYBANK');
  assert.ok(['leading', 'improving', 'weakening', 'lagging'].includes(result.rotation));
  assert.ok(result.score >= 0 && result.score <= 100);
  assert.ok(result.max_drawdown <= 0);
});

test('analyseSector returns null for short history', () => {
  assert.equal(analyseSector('NIFTYIT', syntheticCandles(80), { return_20d: 0, return_60d: 0 }), null);
});

test('returnPct helper', () => {
  assert.ok(Math.abs(returnPct([100, 110, 120], 2) - 20) < 0.001);
});
