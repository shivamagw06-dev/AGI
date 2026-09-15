import test from 'node:test';
import assert from 'node:assert/strict';
import {
  credibleValue, summariseTransactions, plausibleFilingDate, PLAUSIBLE_PRICE_CEILING,
} from '../services/insiderValuation.js';

const tx = (over = {}) => ({
  discretionary: true, derivative: false, direction: 'dispose',
  shares: 1000, price_per_share: 250, value_usd: 250_000, ...over,
});

test('a derivative is never counted in the dollar totals', () => {
  // Measured on one real quarter: 295 derivative purchases and sales carried
  // $103tn between them, against 27,936 share transactions with a median of
  // $168,000. A convertible note at face value is a real transaction and not
  // a comparable one - "the CEO bought $2m of stock" has to mean stock.
  const summary = summariseTransactions([
    tx({ direction: 'acquire' }),
    tx({ derivative: true, direction: 'acquire', value_usd: 103_000_000_000_000 }),
  ]);
  assert.equal(summary.discretionary_buy_value, 250_000);
});

test('an implausible price per share is excluded and counted', () => {
  // A real filing: shares=15,000,000 price=15,000,000. The filer put the total
  // in the price field. Thirteen rows like this carried almost the whole
  // $325tn quarterly total.
  const summary = summariseTransactions([
    tx({ direction: 'acquire' }),
    tx({ direction: 'acquire', shares: 15_000_000, price_per_share: 15_000_000, value_usd: 225e12 }),
  ]);
  assert.equal(summary.discretionary_buy_value, 250_000);
  assert.equal(summary.excluded_values, 1);
});

test('the ceiling sits above the highest-priced real share', () => {
  // Berkshire A trades near $700,000. The bound must not exclude it.
  assert.equal(credibleValue(tx({ price_per_share: 700_000, value_usd: 700_000 })), true);
  assert.equal(credibleValue(tx({ price_per_share: PLAUSIBLE_PRICE_CEILING, value_usd: 1 })), true);
  assert.equal(credibleValue(tx({ price_per_share: PLAUSIBLE_PRICE_CEILING + 1, value_usd: 1 })), false);
});

test('a refused value does not erase the decision', () => {
  // An insider who bought at a price we will not believe still made a
  // decision. Reporting no activity would be a stronger and more wrong claim
  // than reporting activity we cannot size.
  const summary = summariseTransactions([
    tx({ direction: 'acquire', price_per_share: 9_000_000, value_usd: 9e12 }),
  ]);
  assert.equal(summary.discretionary_buy_value, 0);
  assert.equal(summary.has_discretionary, true);
});

test('a grant with no price contributes nothing and is not an exclusion', () => {
  // Non-discretionary anyway, and a missing price is normal rather than
  // suspect. Counting it as excluded would make every quarter look doubtful.
  const summary = summariseTransactions([
    tx({ discretionary: false, price_per_share: null, value_usd: null }),
  ]);
  assert.equal(summary.excluded_values, 0);
  assert.equal(summary.has_discretionary, false);
});

test('buys and sells are separated, and both direction vocabularies work', () => {
  // formFour emits acquire/dispose from the filing's own code, and falls back
  // to buy/sell from the transaction-code table. Both reach here.
  const summary = summariseTransactions([
    tx({ direction: 'buy', value_usd: 100 }),
    tx({ direction: 'acquire', value_usd: 200 }),
    tx({ direction: 'sell', value_usd: 400 }),
    tx({ direction: 'dispose', value_usd: 800 }),
  ]);
  assert.equal(summary.discretionary_buy_value, 300);
  assert.equal(summary.discretionary_sell_value, 1200);
});

test('a year-one date is refused', () => {
  // This reached the database from a real filing and became the earliest date
  // in the table, giving any chart an axis two thousand years wide.
  assert.equal(plausibleFilingDate('0001-01-01'), null);
  assert.equal(plausibleFilingDate('1980-06-30'), null);
  assert.equal(plausibleFilingDate('1993-01-01'), '1993-01-01');
});

test('a future date is refused, with a little slack for time zones', () => {
  const asOf = new Date('2026-09-09T12:00:00Z');
  assert.equal(plausibleFilingDate('2026-09-09', { asOf }), '2026-09-09');
  assert.equal(plausibleFilingDate('2026-09-10', { asOf }), '2026-09-10');
  assert.equal(plausibleFilingDate('2027-01-01', { asOf }), null);
});

test('a malformed date is refused rather than passed along', () => {
  assert.equal(plausibleFilingDate(''), null);
  assert.equal(plausibleFilingDate(null), null);
  assert.equal(plausibleFilingDate('not-a-date'), null);
});

test('nothing in yields zeroes, not NaN', () => {
  const summary = summariseTransactions();
  assert.equal(summary.discretionary_buy_value, 0);
  assert.equal(summary.discretionary_sell_value, 0);
  assert.equal(summary.has_discretionary, false);
});
