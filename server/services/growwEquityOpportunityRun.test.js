import assert from 'node:assert/strict';
import test from 'node:test';
import { analyseEquity, loadEquityUniverse, returnPct, stdev } from './growwEquityOpportunityRun.js';

function syntheticCandles(count, { start = 100, drift = 0.2, volume = 1_000_000 } = {}) {
  const rows = [];
  let price = start;
  for (let i = 0; i < count; i += 1) {
    price += drift;
    rows.push([`2025-01-${String(i + 1).padStart(2, '0')}`, price - 1, price + 1, price - 2, price, volume + i * 1000]);
  }
  return rows;
}

test('returnPct and stdev helpers', () => {
  assert.ok(Math.abs(returnPct([100, 110, 120], 2) - 20) < 0.001);
  assert.ok(stdev([1, 2, 3]) > 0);
});

test('analyseEquity scores a rising series', () => {
  const candles = syntheticCandles(80, { start: 100, drift: 0.5, volume: 2_000_000 });
  const benchmark = { return_20d: 1, return_60d: 2 };
  const result = analyseEquity('RELIANCE', candles, benchmark);
  assert.ok(result);
  assert.equal(result.symbol, 'RELIANCE');
  assert.ok(result.score >= 50);
  assert.equal(result.trend, 'positive');
  assert.ok(Array.isArray(result.reasons));
});

test('analyseEquity returns null for short history', () => {
  const candles = syntheticCandles(40);
  assert.equal(analyseEquity('TCS', candles, { return_20d: 0, return_60d: 0 }), null);
});

test('uses the complete Nifty 200 as the default equity universe', async () => {
  const priorUniverse = process.env.AGI_UNIVERSE;
  const priorLimit = process.env.AGI_MAX_SYMBOLS;
  delete process.env.AGI_UNIVERSE;
  delete process.env.AGI_MAX_SYMBOLS;
  try {
    const symbols = await loadEquityUniverse();
    assert.equal(symbols.length, 200);
    assert.equal(new Set(symbols).size, 200);
  } finally {
    if (priorUniverse === undefined) delete process.env.AGI_UNIVERSE; else process.env.AGI_UNIVERSE = priorUniverse;
    if (priorLimit === undefined) delete process.env.AGI_MAX_SYMBOLS; else process.env.AGI_MAX_SYMBOLS = priorLimit;
  }
});
