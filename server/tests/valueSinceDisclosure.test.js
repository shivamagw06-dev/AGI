import test from 'node:test';
import assert from 'node:assert/strict';
import { revaluePosition, revalueBook } from '../services/valueSinceDisclosure.js';

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
