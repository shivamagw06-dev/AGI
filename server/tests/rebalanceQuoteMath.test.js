import test from 'node:test';
import assert from 'node:assert/strict';
import {
  toDailyRows, averageDailyValue, returnSince, daysOfAdvt, inrToUsdMillions, quoteFor,
} from '../services/rebalanceQuoteMath.js';

/** Upstox shape: [timestamp, open, high, low, close, volume, open_interest]. */
const candle = (date, close, volume) => [`${date}T00:00:00+05:30`, close, close, close, close, volume, 0];

test('candles are sorted, whatever order they arrive in', () => {
  // Upstox returns newest-first today. If that ever changes, an implementation
  // that trusted the order would reverse every return without erroring.
  const newestFirst = [candle('2026-09-03', 110, 100), candle('2026-09-01', 100, 100)];
  const oldestFirst = [candle('2026-09-01', 100, 100), candle('2026-09-03', 110, 100)];
  assert.deepEqual(toDailyRows(newestFirst), toDailyRows(oldestFirst));
  assert.equal(toDailyRows(newestFirst)[0].date, '2026-09-01');
});

test('a candle with no usable close is not a trading day', () => {
  const rows = toDailyRows([
    candle('2026-09-01', 100, 50),
    candle('2026-09-02', 0, 50),
    candle('2026-09-03', null, 50),
    ['not-a-date', 1, 1, 1, 1, 1, 0],
    [],
  ]);
  assert.deepEqual(rows.map((r) => r.date), ['2026-09-01']);
});

test('a zero-volume session is kept, because it is a real observation', () => {
  // A suspended stock genuinely traded nothing. Dropping the day would make
  // the average silently describe a shorter window than it claims.
  const rows = toDailyRows([candle('2026-09-01', 100, 0)]);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].volume, 0);
  assert.equal(rows[0].value, 0);
});

test('the average uses trading sessions, not calendar days', () => {
  // Ten sessions of 1,000 each. Asking for a 30-session window must still
  // divide by the ten that exist - dividing by 30 understates every stock.
  const rows = toDailyRows(
    Array.from({ length: 10 }, (_, i) => candle(`2026-09-${String(i + 1).padStart(2, '0')}`, 100, 10)),
  );
  assert.equal(averageDailyValue(rows, 30), 1000);
});

test('the average covers only the requested window', () => {
  const rows = toDailyRows([
    candle('2026-09-01', 100, 10), // 1,000
    candle('2026-09-02', 100, 10), // 1,000
    candle('2026-09-03', 100, 30), // 3,000
  ]);
  assert.equal(averageDailyValue(rows, 2), 2000);
});

test('a stock that never traded averages to null, not zero', () => {
  // Zero becomes the days-of-ADVT divisor. Reading "no data" as "no liquidity"
  // and then dividing by it is how an unmapped name reaches the top of a
  // most-impactful list.
  const rows = toDailyRows([candle('2026-09-01', 100, 0), candle('2026-09-02', 100, 0)]);
  assert.equal(averageDailyValue(rows), null);
  assert.equal(averageDailyValue([]), null);
});

test('return measures from the last session on or before the announcement', () => {
  // Announcements land on weekends. Requiring an exact date match would return
  // null for most events.
  const rows = toDailyRows([
    candle('2026-09-03', 100, 10),
    candle('2026-09-07', 110, 10),
  ]);
  assert.ok(Math.abs(returnSince(rows, '2026-09-05') - 0.1) < 1e-9);
});

test('return is null when the window does not reach the announcement', () => {
  // Falling back to the earliest available session would measure a different
  // period than the one being reported, and say nothing about it.
  const rows = toDailyRows([candle('2026-09-05', 100, 10), candle('2026-09-07', 110, 10)]);
  assert.equal(returnSince(rows, '2026-08-01'), null);
});

test('return is null when only the announcement session exists', () => {
  const rows = toDailyRows([candle('2026-09-04', 100, 10)]);
  assert.equal(returnSince(rows, '2026-09-04'), null);
});

test('days of ADVT keeps the sign of the flow', () => {
  // An outflow is negative sessions, as the source tables print it. Taking the
  // magnitude would rank a forced seller alongside a forced buyer.
  assert.equal(daysOfAdvt(88, 35), 88 / 35);
  assert.equal(daysOfAdvt(-22, 69), -22 / 69);
});

test('days of ADVT is null rather than Infinity when nothing trades', () => {
  // Infinity sorts to the top of a "most impactful" list on the strength of
  // having no data at all.
  assert.equal(daysOfAdvt(88, 0), null);
  assert.equal(daysOfAdvt(88, null), null);
  assert.equal(daysOfAdvt(null, 35), null);
});

test('a zero flow is a real answer and survives', () => {
  // Distinct from a missing flow. Number(null) is 0, so a guard that tests
  // truthiness would erase the difference.
  assert.equal(daysOfAdvt(0, 35), 0);
});

test('rupees convert to millions of dollars', () => {
  // 8.85bn INR at 88.5 = $100mn.
  assert.equal(inrToUsdMillions(8_850_000_000, 88.5), 100);
  assert.equal(inrToUsdMillions(1000, 0), null);
  assert.equal(inrToUsdMillions(1000, null), null);
});

test('quoteFor produces the moving columns end to end', () => {
  const candles = [
    candle('2026-09-04', 100, 1_000_000),
    candle('2026-09-05', 105, 1_000_000),
    candle('2026-09-08', 110, 1_000_000),
  ];
  // 100mn INR a day at 88.5 is about $1.13mn of ADVT.
  const quote = quoteFor({ candles, announcedOn: '2026-09-04', flowUsdMn: 5, usdInr: 88.5 });

  assert.equal(quote.last_price_inr, 110);
  assert.ok(Math.abs(quote.return_since_announced_pct - 10) < 1e-9);
  assert.ok(quote.advt_3m_usd_mn > 1.1 && quote.advt_3m_usd_mn < 1.3);
  assert.ok(quote.days_of_advt > 3.9 && quote.days_of_advt < 4.5);
  assert.equal(quote.refresh_note, null);
});

test('an unpriceable entry says why rather than going quietly blank', () => {
  // Three different causes need three different fixes, and a blank cell
  // distinguishes none of them.
  assert.match(quoteFor({ candles: [] }).refresh_note, /no candles/i);
  assert.match(
    quoteFor({ candles: [candle('2026-09-01', 100, 0)], usdInr: 88.5 }).refresh_note,
    /no traded volume/i,
  );
});

test('a missing FX rate does not silently mix currencies', () => {
  // Dividing a dollar flow by a rupee ADVT understates the ratio ninety-fold
  // and makes every name look effortlessly tradeable.
  const quote = quoteFor({
    candles: [candle('2026-09-01', 100, 1_000_000), candle('2026-09-02', 100, 1_000_000)],
    flowUsdMn: 5,
    usdInr: null,
  });
  assert.equal(quote.advt_3m_usd_mn, null);
  assert.equal(quote.days_of_advt, null);
  assert.equal(quote.usd_inr, null);
});

test('an announcement newer than the last candle returns null, not a flat 0%', () => {
  // Candles lag: the review is announced this morning, the last close is
  // yesterday's. The base session and the latest session are then the same
  // row, and dividing it by itself yields 0 - which renders as "unchanged
  // since announcement" and is a claim about a period that has not happened.
  const rows = toDailyRows([
    candle('2026-09-01', 100, 10),
    candle('2026-09-03', 110, 10),
  ]);
  assert.equal(returnSince(rows, '2026-09-08'), null);
});
