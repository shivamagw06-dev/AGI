import test from 'node:test';
import assert from 'node:assert/strict';
import { isoDate } from '../services/insiderScanPlan.js';

test('a blank EDGAR date is null, not an empty string', () => {
  // The bug this fixes. EDGAR leaves reportDate blank on most Form 4 filings,
  // and "" reaches a date column as `invalid input syntax for type date: ""`,
  // which aborted the nightly sweep on its first issuer every time.
  assert.equal(isoDate(''), null);
  assert.equal(isoDate('   '), null);
  assert.equal(isoDate(null), null);
  assert.equal(isoDate(undefined), null);
});

test('a real date survives, timestamp suffix and all', () => {
  assert.equal(isoDate('2026-09-09'), '2026-09-09');
  assert.equal(isoDate('2026-09-09T14:22:00Z'), '2026-09-09');
});

test('a partial date is refused rather than completed', () => {
  // new Date('2026') is a valid Date - the first of January. Parsing and
  // checking for validity would store a stub as a real period, which is worse
  // than storing nothing because nothing downstream can tell.
  assert.equal(isoDate('2026'), null);
  assert.equal(isoDate('2026-09'), null);
});

test('a nonsense date is refused', () => {
  assert.equal(isoDate('n/a'), null);
  assert.equal(isoDate('2026-13-45'), null);
  assert.equal(isoDate('0000-00-00'), null);
});
