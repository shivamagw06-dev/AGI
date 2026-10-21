import test from 'node:test';
import assert from 'node:assert/strict';
import { planScans, newFilings, abortReason } from '../services/insiderScanPlan.js';

const companies = new Map([
  ['AAPL', { cik: '0000320193', title: 'Apple Inc.' }],
  ['MSFT', { cik: '0000789019', title: 'Microsoft' }],
  ['NOCIK', {}],
]);

test('a ticker with no CIK is not asked about', () => {
  const { plans, skipped } = planScans(['AAPL', 'NOCIK', 'UNKNOWN'], { companies, asOf: '2026-09-08' });
  assert.deepEqual(plans.map((p) => p.ticker).sort(), ['AAPL']);
  assert.equal(skipped.noCik, 2);
});

test('a ticker scanned recently is left alone', () => {
  // Form 4s arrive within two business days of a trade, so a week-old scan
  // misses little and a daily sweep of the whole universe wastes most of its
  // requests.
  const scannedAt = new Map([['AAPL', '2026-09-05']]);
  const { plans, skipped } = planScans(['AAPL', 'MSFT'], { companies, scannedAt, asOf: '2026-09-08' });
  assert.deepEqual(plans.map((p) => p.ticker), ['MSFT']);
  assert.equal(skipped.recentlyScanned, 1);
});

test('a stale scan is picked up again', () => {
  const scannedAt = new Map([['AAPL', '2026-08-01']]);
  const { plans } = planScans(['AAPL'], { companies, scannedAt, asOf: '2026-09-08' });
  assert.equal(plans.length, 1);
});

test('scan order does not follow the alphabet', () => {
  // A limited run must look like the universe rather than the front of the
  // alphabet; the price backfill aborted on a sample of digit-leading junk
  // before that was fixed.
  const many = new Map(['AAA', 'AAB', 'AAC', 'ZZA', 'ZZB', 'ZZC'].map((t) => [t, { cik: '1' }]));
  const { plans } = planScans([...many.keys()], { companies: many, asOf: '2026-09-08' });
  const order = plans.map((p) => p.ticker);
  assert.notDeepEqual(order, [...order].sort());
  assert.deepEqual([...order].sort(), [...many.keys()].sort());
});

const filings = [
  { form: '4', accession: 'a1', filedAt: '2026-09-01' },
  { form: '4/A', accession: 'a2', filedAt: '2026-08-20' },
  { form: '4', accession: 'a3', filedAt: '2026-07-01' },
  { form: '13F-HR', accession: 'x1', filedAt: '2026-08-14' },
];

test('a filing already stored is not fetched again', () => {
  // A ticker that has filed nothing new costs one index request and no
  // document fetches at all.
  const known = new Set(['a1', 'a3']);
  assert.deepEqual(newFilings(filings, known).map((r) => r.accession), ['a2']);
});

test('amendments are collected in their own right', () => {
  assert.ok(newFilings(filings, new Set()).some((r) => r.form === '4/A'));
});

test('other forms are ignored', () => {
  assert.ok(!newFilings(filings, new Set()).some((r) => r.form === '13F-HR'));
});

test('newest first, so a capped run takes the most recent', () => {
  // EDGAR does not guarantee an order, and a cap applied to an arbitrary one
  // keeps whichever filings happened to come first rather than the latest.
  const shuffled = [filings[2], filings[3], filings[0], filings[1]];
  assert.deepEqual(newFilings(shuffled, new Set(), { limit: 2 }).map((r) => r.accession), ['a1', 'a2']);
});

test('a run stops when documents stop parsing', () => {
  // Continuing produces a table of filings nobody can read, indistinguishable
  // from issuers that simply did not file.
  assert.match(abortReason({ parsed: 10, unreadable: 60 }), /could not be parsed/);
  assert.equal(abortReason({ parsed: 90, unreadable: 10 }), null);
});

test('a small sample cannot trip the abort', () => {
  assert.equal(abortReason({ parsed: 0, unreadable: 5 }), null);
});
