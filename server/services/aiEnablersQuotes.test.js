import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LAST_GOOD_MAX_AGE_MS, LastGoodPrices, instrumentKeyFor, quoteBook, quoteFor,
  sessionElapsedFraction, universeInstrumentKeys, volumeRatio,
} from './aiEnablersQuotes.js';

/** A stand-in for SynchronizedSnapshotStore: the same get(), nothing else. */
const storeOf = (rows) => ({ get: (key) => rows[key] || null });
const row = (ltp, previousClose, atMs, extra = {}) => ({
  ltp, previous_close: previousClose,
  effective_timestamp: new Date(atMs).toISOString(),
  ...extra,
});

const NOW = Date.parse('2026-09-17T06:00:00Z');   // 11:30 IST, mid-session

test('an instrument key is taken as given, or built from the ISIN', () => {
  assert.equal(instrumentKeyFor({ instrumentKey: 'NSE_EQ|INE067A01029' }).key, 'NSE_EQ|INE067A01029');
  assert.equal(instrumentKeyFor({ isin: 'INE067A01029' }).key, 'NSE_EQ|INE067A01029');
});

test('a key that cannot be built says why, instead of becoming undefined', () => {
  assert.equal(instrumentKeyFor({ isin: 'NOTANISIN' }).reason, 'NO_ISIN');
  assert.equal(instrumentKeyFor({}).reason, 'NO_ISIN');
  // "NSE_EQ" with no pipe would be accepted by a truthiness check and then
  // silently never match a feed key.
  assert.equal(instrumentKeyFor({ instrumentKey: 'NSE_EQ' }).reason, 'MALFORMED_INSTRUMENT_KEY');
});

test('the subscription list carries the benchmark and names what it could not key', () => {
  const universe = {
    benchmarkKey: 'NSE_INDEX|Nifty 50',
    members: [
      { symbol: 'CGPOWER', isin: 'INE067A01029' },
      { symbol: 'GHOST' },
      { symbol: 'DROPPED', isin: 'INE067A01029', admitted: false },
    ],
  };
  const resolved = universeInstrumentKeys(universe);
  assert.deepEqual(resolved.keys, ['NSE_EQ|INE067A01029', 'NSE_INDEX|Nifty 50']);
  assert.deepEqual(resolved.unresolved, [{ symbol: 'GHOST', reason: 'NO_ISIN' }]);
  assert.equal(resolved.bySymbol.has('DROPPED'), false);
});

test('a fresh tick is live, and is remembered as the last good price', () => {
  const lastGood = new LastGoodPrices();
  const store = storeOf({ K: row(110, 100, NOW - 1_000) });
  const quote = quoteFor('K', { store, lastGood, now: NOW, staleMs: 60_000 });
  assert.equal(quote.source, 'live');
  assert.equal(quote.ltp, 110);
  assert.equal(lastGood.size(), 1);
});

test('a stale tick falls back to last good, and says so', () => {
  const lastGood = new LastGoodPrices();
  lastGood.remember('K', { ltp: 108, previousClose: 100, at: NOW - 90_000 });
  const store = storeOf({ K: row(110, 100, NOW - 120_000) });
  const quote = quoteFor('K', { store, lastGood, now: NOW, staleMs: 60_000 });
  assert.equal(quote.source, 'last_good');
  assert.equal(quote.ltp, 108);
});

test('last good expires, so a dead feed stops looking alive', () => {
  // The whole point of the fallback is to cover the gap between ticks. If it
  // never expired, coverage would stay at 100% through a total outage and the
  // index would keep printing a level off prices from an hour ago.
  const lastGood = new LastGoodPrices();
  lastGood.remember('K', { ltp: 108, previousClose: 100, at: NOW - LAST_GOOD_MAX_AGE_MS - 1 });
  const quote = quoteFor('K', { store: storeOf({}), lastGood, now: NOW, staleMs: 60_000 });
  assert.equal(quote, null);
});

test('a last good price never moves backwards', () => {
  // Ticks can arrive out of order across a reconnect. Accepting an older one
  // would rewind the fallback to a price that has already been superseded.
  const lastGood = new LastGoodPrices();
  lastGood.remember('K', { ltp: 110, previousClose: 100, at: NOW - 1_000 });
  lastGood.remember('K', { ltp: 105, previousClose: 100, at: NOW - 5_000 });
  assert.equal(lastGood.get('K', { now: NOW }).ltp, 110);
});

test('a zero previous close is refused rather than dividing by it', () => {
  const store = storeOf({ K: row(110, 0, NOW - 1_000) });
  assert.equal(quoteFor('K', { store, lastGood: new LastGoodPrices(), now: NOW, staleMs: 60_000 }), null);
});

test('the quote book is the shape the index reads, plus how real it is', () => {
  const universe = {
    benchmarkKey: 'NSE_INDEX|Nifty 50',
    members: [
      { symbol: 'AAA', instrumentKey: 'NSE_EQ|INE000A01001' },
      { symbol: 'BBB', instrumentKey: 'NSE_EQ|INE000A01002' },
      { symbol: 'CCC', instrumentKey: 'NSE_EQ|INE000A01003' },
    ],
  };
  const lastGood = new LastGoodPrices();
  lastGood.remember('NSE_EQ|INE000A01002', { ltp: 105, previousClose: 100, at: NOW - 90_000 });
  const store = storeOf({
    'NSE_EQ|INE000A01001': row(110, 100, NOW - 1_000),
    'NSE_EQ|INE000A01002': row(120, 100, NOW - 200_000),
    'NSE_INDEX|Nifty 50': row(25_250, 25_000, NOW - 1_000),
  });
  const book = quoteBook(universe, { store, lastGood, now: NOW, staleMs: 60_000 });

  assert.deepEqual(Object.keys(book.quotes).sort(), ['AAA', 'BBB']);
  assert.deepEqual(book.quotes.AAA, { ltp: 110, previousClose: 100, at: NOW - 1_000, source: 'live' });
  assert.deepEqual(book.sources.live, ['AAA']);
  assert.deepEqual(book.sources.last_good, ['BBB']);
  assert.deepEqual(book.sources.missing, ['CCC']);
  assert.equal(book.benchmark.ltp, 25_250);
});

test('the session fraction tracks the NSE clock, not the wall clock', () => {
  const at = (iso) => sessionElapsedFraction(Date.parse(iso));
  assert.equal(at('2026-09-17T03:00:00Z'), 0);          // 08:30 IST, pre-open
  assert.equal(at('2026-09-17T10:30:00Z'), 1);          // 16:00 IST, after close
  assert.equal(Number(at('2026-09-17T06:52:30Z').toFixed(2)), 0.5);  // 12:22:30 IST, half
});

test('the volume ratio is time-adjusted, so 10am is not always quiet', () => {
  // Half the session gone, half a normal day's volume done: that is a normal
  // day, and must read as 1.0 rather than 0.5.
  const half = volumeRatio({
    cumulativeVolume: 500_000, averageDailyVolume: 1_000_000,
    now: Date.parse('2026-09-17T06:52:30Z'),
  });
  assert.equal(half.ratio, 1);
});

test('the volume ratio refuses when the comparison would be noise', () => {
  const noBaseline = volumeRatio({ cumulativeVolume: 500_000, averageDailyVolume: null, now: NOW });
  assert.equal(noBaseline.ratio, null);
  assert.equal(noBaseline.reason, 'NO_BASELINE');

  // Two minutes into a 375-minute session, one block trade reads as 40x.
  const young = volumeRatio({
    cumulativeVolume: 10_000, averageDailyVolume: 1_000_000,
    now: Date.parse('2026-09-17T03:47:00Z'),
  });
  assert.equal(young.ratio, null);
  assert.equal(young.reason, 'SESSION_TOO_YOUNG');
});
