import assert from 'node:assert/strict';
import test from 'node:test';
import { CandlePriceBook, candleKey, parseMinuteCandles } from './candlePriceBook.js';

// Upstox returns the newest candle first, stamped with its start minute.
const payload = {
  status: 'success',
  data: {
    candles: [
      ['2026-09-17T15:29:00+05:30', 1243.9, 1243.9, 1243.9, 1243.9, 0, 0],
      ['2026-09-17T09:24:00+05:30', 1250, 1251, 1249, 1250.5, 100, 0],
      ['2026-09-17T09:15:00+05:30', 1244.8, 1253.4, 1244.5, 1250.8, 274429, 0],
    ],
  },
};

function book(overrides = {}) {
  const calls = [];
  const sleeps = [];
  let clock = Date.parse('2026-09-19T06:00:00Z');
  const instance = new CandlePriceBook({
    fetchCandles: async (key, date) => { calls.push([key, date]); return payload; },
    requestsPerSecond: 0.5,
    sleep: async (ms) => { sleeps.push(ms); clock += ms; },
    clock: () => clock,
    ...overrides,
  });
  return { instance, calls, sleeps };
}

test('parses candles oldest first, keyed by the minute they end', () => {
  const rows = parseMinuteCandles(payload);
  assert.equal(rows.length, 3);
  assert.equal(new Date(rows[0][0]).toISOString(), '2026-09-17T03:46:00.000Z');
  assert.equal(rows[2][1], 1243.9);
});

test('prices an instant from the last candle finished by then', async () => {
  const { instance } = book();
  const at = (time) => instance.priceAt('NSE_EQ|INE002A01018', `2026-09-17T${time}+05:30`);
  assert.equal((await at('09:25:00')).price, 1250.5);
  assert.equal((await at('09:24:59')).price, 1250.8);
  assert.equal((await at('15:30:00')).price, 1243.9);
  assert.equal((await at('18:00:00')).price, 1243.9);
  assert.equal((await at('09:15:30')).reason, 'before_first_candle');
});

test('does not price a session whose history is not yet published', async () => {
  const { instance, calls } = book();
  const result = await instance.priceAt('NSE_EQ|INE002A01018', '2026-09-19T10:00:00+05:30');
  assert.equal(result.reason, 'session_not_published');
  assert.equal(calls.length, 0);
});

test('caches each instrument-day and spaces out requests', async () => {
  const { instance, calls, sleeps } = book();
  await instance.priceAt('NSE_EQ|A', '2026-09-17T10:00:00+05:30');
  await instance.priceAt('NSE_EQ|A', '2026-09-17T11:00:00+05:30');
  await instance.priceAt('NSE_EQ|B', '2026-09-17T11:00:00+05:30');
  assert.equal(calls.length, 2);
  assert.deepEqual(sleeps, [2000]);
  assert.equal(instance.stats.cache_hits, 1);
});

test('an empty history reads as no candles, and old sector keys map to Upstox keys', async () => {
  const { instance } = book({ fetchCandles: async () => ({ data: { candles: [] } }) });
  assert.equal((await instance.priceAt('NSE_EQ|A', '2026-09-17T10:00:00+05:30')).reason, 'no_candles');
  assert.equal(candleKey('NSE_INDEX|Nifty Financial Services'), 'NSE_INDEX|Nifty Fin Service');
  assert.equal(candleKey('NSE_INDEX|Nifty 50'), 'NSE_INDEX|Nifty 50');
});

test('a refused key is that row\'s problem; throttling still stops the caller', async () => {
  const refuse = (status, message) => async () => { const error = new Error(message); error.status = status; throw error; };
  const { instance } = book({ fetchCandles: refuse(400, 'Invalid Instrument key') });
  assert.equal((await instance.priceAt('NSE_FO|12345', '2026-08-10T10:00:00+05:30')).reason, 'invalid_instrument_key');
  const throttled = book({ fetchCandles: refuse(429, 'Too many requests') }).instance;
  await assert.rejects(throttled.priceAt('NSE_EQ|A', '2026-08-10T10:00:00+05:30'), /Too many/);
});
