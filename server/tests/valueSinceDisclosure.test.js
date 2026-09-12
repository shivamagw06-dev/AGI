import test from 'node:test';
import assert from 'node:assert/strict';
import { revaluePosition, revalueBook, foldCloseWindows } from '../services/valueSinceDisclosure.js';

test('a position is revalued by the ratio of two closes, not by share count', () => {
  // Yahoo's close is retroactively split-adjusted, so disclosed shares times
  // today's price is wrong by any split since the filing. The ratio of two
  // closes on the same adjusted basis makes splits cancel and needs no share
  // count at all.
  const r = revaluePosition({ value_usd: 66_000_000_000 }, { at_report_date: 200, at_latest_close: 220 });
  assert.equal(r.current, 72_600_000_000);
  assert.ok(Math.abs(r.changePct - 10) < 1e-9);
});

test('a missing price is not a zero and not a carry-forward', () => {
  // With no close on the report date there is nothing to measure against;
  // with no recent close the security has stopped trading or never matched.
  // Either way the honest output is an absence with a reason.
  const noThen = revaluePosition({ value_usd: 1e9 }, { at_latest_close: 100 });
  assert.equal(noThen.current, null);
  assert.match(noThen.reason, /no price on the report date/);

  const noNow = revaluePosition({ value_usd: 1e9 }, { at_report_date: 100 });
  assert.equal(noNow.current, null);
  assert.match(noNow.reason, /no recent price/);

  assert.equal(revaluePosition({ value_usd: 1e9 }, null).current, null);
});

const keyOf = (row) => row.cusip;
const book = [
  { cusip: 'A', value_usd: 60_000_000_000 },
  { cusip: 'B', value_usd: 30_000_000_000 },
  { cusip: 'C', value_usd: 10_000_000_000 },   // no price
  { cusip: 'P', value_usd: 5_000_000_000, put_call: 'PUT' },
];
const prices = new Map([
  ['A', { at_report_date: 100, at_latest_close: 110 }],
  ['B', { at_report_date: 50, at_latest_close: 45 }],
]);

test('the revalued total covers only what could be priced, and says how much', () => {
  // Scaling the priced part up to the whole book would invent the movement of
  // what it could not see - the same failure as re-weighting a backtest to
  // 100% after discarding the names that went missing.
  const r = revalueBook(book, prices, keyOf);
  assert.equal(r.disclosed_total, 100_000_000_000);
  assert.equal(r.priced_disclosed, 90_000_000_000);
  assert.equal(r.current_total, 60e9 * 1.1 + 30e9 * 0.9);
  assert.equal(r.unpriced_count, 1);
  assert.equal(r.unpriced_value, 10_000_000_000);
  assert.equal(r.priced_share_pct, 90);
});

test('the change is measured against the priced part, not the whole book', () => {
  // Dividing the priced move by the full disclosed total would understate it
  // by whatever share could not be priced.
  const r = revalueBook(book, prices, keyOf);
  assert.ok(Math.abs(r.change_pct - (((66e9 + 27e9) - 90e9) / 90e9) * 100) < 1e-9);
});

test('options are outside the book being revalued', () => {
  const withoutOption = revalueBook(book.filter((h) => !h.put_call), prices, keyOf);
  assert.equal(revalueBook(book, prices, keyOf).disclosed_total, withoutOption.disclosed_total);
});

test('a book with no prices reports no total rather than zero', () => {
  // Zero would read as a portfolio that lost everything.
  const r = revalueBook(book, new Map(), keyOf);
  assert.equal(r.current_total, null);
  assert.equal(r.change_pct, null);
  assert.equal(r.priced_share_pct, 0);
});

test('a fall is reported as a fall', () => {
  const r = revalueBook([{ cusip: 'B', value_usd: 30e9 }], prices, keyOf);
  assert.ok(r.change_pct < 0);
  assert.equal(r.current_total, 27e9);
});

// ---- foldCloseWindows -----------------------------------------------------

const bar = (ticker, price_date, close) => ({ ticker, price_date, close });

test('the last row for a ticker wins, which is what the ordering guarantees', () => {
  // Rows arrive ordered by ticker then date, so the final row seen for each
  // ticker is its latest close in that window.
  const closes = foldCloseWindows({
    atReport: [bar('AAPL', '2026-06-26', 200), bar('AAPL', '2026-06-30', 210), bar('KO', '2026-06-30', 70)],
    atLatest: [bar('AAPL', '2026-09-05', 230), bar('AAPL', '2026-09-08', 235)],
  });
  assert.equal(closes.get('AAPL').at_report_date, 210);
  assert.equal(closes.get('AAPL').at_report_date_on, '2026-06-30');
  assert.equal(closes.get('AAPL').at_latest_close, 235);
  assert.equal(closes.get('AAPL').at_latest_close_on, '2026-09-08');
  assert.equal(closes.get('KO').at_report_date, 70);
});

test('a ticker in one window only keeps what it has', () => {
  // A position priced at the report date but not since is not the same as one
  // with no price at all, and revalueBook distinguishes them.
  const closes = foldCloseWindows({ atReport: [bar('DELISTED', '2026-06-30', 12)], atLatest: [] });
  assert.equal(closes.get('DELISTED').at_report_date, 12);
  assert.equal(closes.get('DELISTED').at_latest_close, undefined);
});

test('an unusable close never overwrites a good one', () => {
  // The last row wins, so a null or zero close arriving after a real one would
  // blank it - and a blanked close reads downstream as a position that could
  // not be priced.
  const closes = foldCloseWindows({
    atLatest: [bar('AAPL', '2026-09-05', 230), bar('AAPL', '2026-09-08', null), bar('AAPL', '2026-09-09', 0)],
  });
  assert.equal(closes.get('AAPL').at_latest_close, 230);
  assert.equal(closes.get('AAPL').at_latest_close_on, '2026-09-05');
});

test('a row with no ticker is ignored rather than keyed on empty', () => {
  const closes = foldCloseWindows({ atLatest: [bar('', '2026-09-08', 100), bar(null, '2026-09-08', 100)] });
  assert.equal(closes.size, 0);
});

test('tickers are matched case-insensitively', () => {
  const closes = foldCloseWindows({ atReport: [bar('aapl', '2026-06-30', 210)] });
  assert.equal(closes.get('AAPL').at_report_date, 210);
});

test('nothing in yields an empty map, not a throw', () => {
  assert.equal(foldCloseWindows().size, 0);
  assert.equal(foldCloseWindows({}).size, 0);
});
