import test from 'node:test';
import assert from 'node:assert/strict';
import { firstSeenByCusip, isUnbounded, boundedStart, planBounds } from '../services/mappingBounds.js';

const holdings = [
  { cusip: '512807306', report_date: '2024-12-31' },
  { cusip: '512807306', report_date: '2025-03-31' },
  { cusip: '09290D101', report_date: '2024-09-30' },
];
const firstSeen = firstSeenByCusip(holdings);

test('the first observed quarter is the earliest, not the first row seen', () => {
  assert.equal(firstSeen.get('512807306'), '2024-12-31');
});

test('a mapping claiming a ticker from 1900 is treated as unbounded', () => {
  // The early identifier backfill wrote these. The vendor was answering what a
  // CUSIP maps to now, and storing that as valid from 1900 asserts today's
  // ticker applied to every filing ever made.
  assert.equal(isUnbounded({ valid_from: '1900-01-01' }), true);
  assert.equal(isUnbounded({ valid_from: null }), true);
  assert.equal(isUnbounded({ valid_from: '2023-09-30' }), false);
});

test('an unbounded mapping is bounded to the first quarter its security is held', () => {
  // A mapping cannot have described a holding that did not exist, and the
  // resolver reads mappings as at a report date - so a start on the first
  // observed quarter covers every date that will ever be asked of it.
  const { from } = boundedStart({ cusip: '512807306', valid_from: '1900-01-01' }, firstSeen);
  assert.equal(from, '2024-12-31');
});

test('a mapping for a security never held is left alone', () => {
  // There is no evidence to bound it with, and inventing one is the same
  // fault in the other direction: a narrower claim, equally unsupported.
  const { from, reason } = boundedStart({ cusip: 'UNSEEN123', valid_from: '1900-01-01' }, firstSeen);
  assert.equal(from, null);
  assert.match(reason, /never observed/);
});

test('a mapping that already has a real start is not touched', () => {
  const { from, reason } = boundedStart({ cusip: '512807306', valid_from: '2024-03-31' }, firstSeen);
  assert.equal(from, null);
  assert.equal(reason, 'already bounded');
});

test('the plan reports what it skipped and why', () => {
  const mappings = [
    { cusip: '512807306', valid_from: '1900-01-01', ticker: 'LRCX' },
    { cusip: '09290D101', valid_from: '1900-01-01', ticker: 'BLK' },
    { cusip: 'UNSEEN123', valid_from: '1900-01-01', ticker: 'ZZZ' },
    { cusip: '512807306', valid_from: '2024-12-31', ticker: 'LRCX' },
  ];
  const { plan, skipped } = planBounds(mappings, firstSeen);
  assert.equal(plan.length, 2);
  assert.deepEqual(plan.map((p) => p.from).sort(), ['2024-09-30', '2024-12-31']);
  assert.equal(skipped.neverObserved, 1);
  assert.equal(skipped.alreadyBounded, 1);
});

test('a bounded start never moves later than the security is first held', () => {
  // Narrowing past the evidence would unmap a holding that currently resolves,
  // which is worse than the placeholder it replaces.
  const { plan } = planBounds([{ cusip: '512807306', valid_from: '1900-01-01' }], firstSeen);
  assert.ok(plan[0].from <= firstSeen.get('512807306'));
});
