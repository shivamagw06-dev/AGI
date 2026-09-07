import test from 'node:test';
import assert from 'node:assert/strict';
import { yahooSymbol, planFetches, priceRows, abortReason, coverageProblem } from '../services/pricePlan.js';

test('share-class punctuation is translated to the convention Yahoo answers', () => {
  // BRK.B is a 404 on Yahoo; BRK-B returns history. The failure is silent -
  // the symbol just looks delisted - so it has to be corrected before asking.
  assert.equal(yahooSymbol('BRK.B'), 'BRK-B');
  assert.equal(yahooSymbol('BRK-B'), 'BRK-B');
  assert.equal(yahooSymbol('aapl'), 'AAPL');
});

test('the junk entry in the SEC ticker file is not asked for', () => {
  // company_tickers.json literally contains a row whose ticker is "NONE.".
  assert.equal(yahooSymbol('NONE.'), null);
  assert.equal(yahooSymbol(''), null);
  assert.equal(yahooSymbol(null), null);
  assert.equal(yahooSymbol('NOT A TICKER'), null);
});

const holdings = [
  { ticker: 'AAPL', security_key: '037833100', first_report_date: '2021-03-31' },
  { ticker: 'AAPL', security_key: '037833100', first_report_date: '2019-06-30' },
  { ticker: 'STZ', security_key: '21036P108', first_report_date: '2020-03-31' },
  { ticker: 'STZ', security_key: '21036P207', first_report_date: '2020-03-31' },
];

test('one request per symbol, reaching back to the earliest date it is held', () => {
  const { plans } = planFetches(holdings, { asOf: '2026-09-07', bufferDays: 120 });
  assert.equal(plans.length, 2, 'two symbols, not four holdings');
  const aapl = plans.find((p) => p.symbol === 'AAPL');
  assert.equal(aapl.from, '2019-03-02', 'earliest holding less the buffer');
  assert.equal(aapl.to, '2026-09-07');
});

test('a symbol shared by two identifiers prices both, rather than one being picked', () => {
  // Constellation Brands A and B were separate identifiers that now share
  // STZ. Choosing between them leaves the other silently without prices.
  const { plans } = planFetches(holdings, { asOf: '2026-09-07' });
  const stz = plans.find((p) => p.symbol === 'STZ');
  assert.deepEqual(stz.securityKeys, ['21036P108', '21036P207']);

  const bars = [{ price_date: '2024-01-02', close: 10, adjusted_close: 9, currency: 'USD' }];
  const rows = priceRows(stz, bars, { source: 'yahoo', listingStatus: 'active', sourceAsOf: 'x' });
  assert.equal(rows.length, 2);
  assert.deepEqual(rows.map((r) => r.security_key), ['21036P108', '21036P207']);
});

test('a symbol whose stored history already reaches the run date is not refetched', () => {
  // Without this a run interrupted at symbol 3,000 starts again from zero.
  const freshness = new Map([['AAPL', '2026-09-04']]);
  const { plans, skipped } = planFetches(holdings, { asOf: '2026-09-07', freshness });
  assert.deepEqual(plans.map((p) => p.symbol), ['STZ']);
  assert.equal(skipped.alreadyFresh, 1);
});

test('stale stored history is refetched rather than treated as done', () => {
  const freshness = new Map([['AAPL', '2026-06-30']]);
  const { plans } = planFetches(holdings, { asOf: '2026-09-07', freshness });
  assert.ok(plans.some((p) => p.symbol === 'AAPL'));
});

test('a run stops when current holdings are unknown, because that is a mapping bug', () => {
  // Every live symbol 404ing is not 3,000 delistings; it means the tickers or
  // the symbol convention are wrong, and continuing writes a table of holes.
  const broken = { ok: 10, empty: 0, notFound: 60, failed: 0, live: { done: 60, notFound: 60 } };
  assert.match(abortReason(broken), /unknown to Yahoo/);
  const healthy = { ok: 90, empty: 0, notFound: 10, failed: 0, live: { done: 90, notFound: 2 } };
  assert.equal(abortReason(healthy), null);
});

test('a run stops when requests are being refused, not just when they 404', () => {
  assert.match(abortReason({ ok: 40, empty: 0, notFound: 0, failed: 40 }), /refusing traffic/);
});

test('a small sample cannot trip the abort', () => {
  // Three failures at the start of a run is noise, not a broken mapping.
  assert.equal(abortReason({ ok: 0, empty: 0, notFound: 3, failed: 0 }), null);
});

test('a reassigned ticker is rejected rather than priced off another company', () => {
  // Facebook became META in 2022 and a different, live company now holds the
  // ticker FB. Yahoo answers a request for FB with that company's history and
  // marks the handover nowhere. Against a 2019 Facebook position it would
  // produce prices that are wrong and look perfectly healthy.
  const plan = { symbol: 'FB', earliestHeld: '2019-06-30' };
  const reused = [{ price_date: '2025-06-26' }, { price_date: '2026-09-04' }];
  assert.match(coverageProblem(plan, reused), /reassigned to another company/);
});

test('history that reaches the position is accepted', () => {
  const plan = { symbol: 'AAPL', earliestHeld: '2019-06-30' };
  assert.equal(coverageProblem(plan, [{ price_date: '2019-03-04' }]), null);
  // A holiday or a data edge a few days short is not a reassignment.
  assert.equal(coverageProblem(plan, [{ price_date: '2019-07-02' }]), null);
});

test('an empty history is a coverage problem, not a silent pass', () => {
  assert.match(coverageProblem({ earliestHeld: '2019-06-30' }, []), /no history/);
});

test('the plan carries the date held, not only the buffered request start', () => {
  const { plans } = planFetches(holdings, { asOf: '2026-09-07', bufferDays: 120 });
  const aapl = plans.find((p) => p.symbol === 'AAPL');
  assert.equal(aapl.earliestHeld, '2019-06-30');
  assert.equal(aapl.from, '2019-03-02');
});

test('delisted symbols do not abort a run; broken current holdings do', () => {
  // Yahoo serves no history at all for TWTR, ATVI, VMW or SIVBQ. A seven-year
  // holdings file is full of such names, so a high unknown rate overall is
  // normal. The same rate among securities still held is not.
  const manyDelisted = { ok: 60, empty: 0, notFound: 40, failed: 0, live: { done: 60, notFound: 1 } };
  assert.equal(abortReason(manyDelisted), null);

  const brokenMapping = { ok: 60, empty: 0, notFound: 40, failed: 0, live: { done: 60, notFound: 30 } };
  assert.match(abortReason(brokenMapping), /currently-held symbols unknown/);
});

test('a security still held at the latest report date is marked as such', () => {
  const rows = [
    { ticker: 'AAPL', security_key: 'A', first_report_date: '2019-06-30', last_report_date: '2026-06-30' },
    { ticker: 'TWTR', security_key: 'B', first_report_date: '2019-06-30', last_report_date: '2022-03-31' },
  ];
  const { plans } = planFetches(rows, { asOf: '2026-09-07' });
  assert.equal(plans.find((p) => p.symbol === 'AAPL').heldNow, true);
  assert.equal(plans.find((p) => p.symbol === 'TWTR').heldNow, false);
});

test('without a current-holdings sample, unknown symbols are not judged at all', () => {
  // Deliberate: a delisting wave and a broken mapping are indistinguishable
  // from the overall rate alone, so the run continues rather than guessing.
  assert.equal(abortReason({ ok: 10, empty: 0, notFound: 60, failed: 0 }), null);
  // Failures are still judged, because they do not depend on that split.
  assert.match(abortReason({ ok: 10, empty: 0, notFound: 0, failed: 60 }), /refusing traffic/);
});
