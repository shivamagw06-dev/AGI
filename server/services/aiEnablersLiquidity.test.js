import test from 'node:test';
import assert from 'node:assert/strict';
import { candleRows, liquidityFrom, liquidityForUniverse, volumeBaselines } from './aiEnablersLiquidity.js';

/** Upstox daily candles: [ts, open, high, low, close, volume, oi]. */
const candles = (rows) => ({ data: { candles: rows } });
const day = (n, close, volume) => [
  `2026-0${1 + Math.floor(n / 28)}-${String((n % 28) + 1).padStart(2, '0')}T00:00:00+05:30`,
  close, close, close, close, volume, 0,
];

test('candles are flattened and sorted oldest first', () => {
  const rows = candleRows(candles([day(3, 100, 10), day(1, 100, 10), day(2, 100, 10)]));
  assert.equal(rows.length, 3);
  assert.ok(rows[0].at < rows[1].at && rows[1].at < rows[2].at);
});

test('a malformed candle is skipped rather than poisoning the average', () => {
  const rows = candleRows(candles([day(1, 100, 10), ['not-a-date', 1, 1, 1, 1, 1, 0], [1, 2]]));
  assert.equal(rows.length, 1);
});

test('too little history returns a reason, not a number', () => {
  const short = liquidityFrom(candles([day(1, 100, 10), day(2, 100, 10)]));
  assert.equal(short.averageDailyVolume, null);
  assert.equal(short.reason, 'INSUFFICIENT_HISTORY');
  assert.equal(short.sessions, 2);
});

test('average volume and median turnover are computed over the window', () => {
  const rows = Array.from({ length: 20 }, (unused, i) => day(i, 100, 1_000));
  const liquidity = liquidityFrom(candles(rows));
  assert.equal(liquidity.averageDailyVolume, 1_000);
  assert.equal(liquidity.medianDailyTurnover, 100_000);
  assert.equal(liquidity.sessions, 20);
  assert.equal(liquidity.lastClose, 100);
});

test('turnover uses the median, so one block trade cannot carry a thin name', () => {
  // Nineteen quiet days and one enormous one. The mean turnover clears a
  // 1,000,000 floor; the median correctly does not.
  const rows = Array.from({ length: 19 }, (unused, i) => day(i, 100, 1_000));
  rows.push(day(19, 100, 5_000_000));
  const liquidity = liquidityFrom(candles(rows));
  const meanTurnover = rows.reduce((sum, r) => sum + r[4] * r[5], 0) / rows.length;
  assert.ok(meanTurnover > 1_000_000, 'the mean would have passed a 1M floor');
  assert.equal(liquidity.medianDailyTurnover, 100_000);
});

test('only the most recent sessions are used', () => {
  const rows = [
    ...Array.from({ length: 20 }, (unused, i) => day(i, 100, 9_000)),
    ...Array.from({ length: 20 }, (unused, i) => day(20 + i, 100, 1_000)),
  ];
  assert.equal(liquidityFrom(candles(rows), { sessions: 20 }).averageDailyVolume, 1_000);
});

test('a member whose fetch fails is recorded, not omitted in silence', async () => {
  const universe = { members: [
    { symbol: 'AAA', instrumentKey: 'NSE_EQ|INE000A01001' },
    { symbol: 'BBB', instrumentKey: 'NSE_EQ|INE000A01002' },
    { symbol: 'GHOST' },
  ] };
  const liquidity = await liquidityForUniverse(universe, {
    to: '2026-09-17',
    fetchCandles: async (key) => {
      if (key.endsWith('002')) throw new Error('Upstox HTTP 429');
      return candles(Array.from({ length: 20 }, (unused, i) => day(i, 100, 1_000)));
    },
  });
  assert.deepEqual(Object.keys(liquidity.bySymbol), ['AAA']);
  assert.deepEqual(liquidity.failures, [
    { symbol: 'BBB', error: 'Upstox HTTP 429' },
    { symbol: 'GHOST', error: 'MALFORMED_INSTRUMENT_KEY' },
  ]);
});

test('baselines carry only members with a real average', async () => {
  const universe = { members: [
    { symbol: 'AAA', instrumentKey: 'NSE_EQ|INE000A01001' },
    { symbol: 'BBB', instrumentKey: 'NSE_EQ|INE000A01002' },
  ] };
  const liquidity = await liquidityForUniverse(universe, {
    to: '2026-09-17',
    fetchCandles: async (key) => candles(
      key.endsWith('002')
        ? [day(1, 100, 10)]                                                    // too short
        : Array.from({ length: 20 }, (unused, i) => day(i, 100, 1_000)),
    ),
  });
  assert.deepEqual(volumeBaselines(liquidity), { AAA: 1_000 });
});

test('a null volume is missing history, not a zero-volume day', () => {
  // Number(null) === 0 would drag the average down with days that never
  // reported, making a liquid name look thin enough to fail a turnover floor.
  const rows = [
    ...Array.from({ length: 19 }, (unused, i) => day(i, 100, 1_000)),
    ['2026-02-01T00:00:00+05:30', 100, 100, 100, 100, null, 0],
  ];
  const liquidity = liquidityFrom(candles(rows));
  assert.equal(liquidity.sessions, 19);
  assert.equal(liquidity.averageDailyVolume, 1_000);
});
