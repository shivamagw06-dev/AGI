import test from 'node:test';
import assert from 'node:assert/strict';
import { coverageFor, blockersFor, disclosuresFor } from '../services/coverageGate.js';

const priced = new Set(['AAPL', 'MSFT', 'BRK-B']);

// A realistic book: three large positions that price, and one tiny holding
// with no ticker - a small fund or a preferred line, which every real 13F has.
const realistic = [
  { security_key: 'A', ticker: 'AAPL', value_usd: 40_000_000_000 },
  { security_key: 'B', ticker: 'MSFT', value_usd: 30_000_000_000 },
  { security_key: 'C', ticker: 'BRK-B', value_usd: 29_900_000_000 },
  { security_key: 'D', ticker: null, value_usd: 200_000 },
];

test('one unresolved odd-lot does not withhold a manager', () => {
  // The old gate blocked outright on any unmapped holding. Counting treats a
  // $200k line as equal to a $40bn one, and a real book always has one.
  const cov = coverageFor(realistic, priced);
  assert.equal(cov.securities_unmapped, 1);
  assert.ok(cov.value_coverage > 0.999);
  assert.deepEqual(blockersFor({ periods: 8, coverage: cov }), []);
});

test('the unresolved holding is still disclosed, with its weight', () => {
  // Not withheld and not hidden. The reader gets the fact and its size.
  const notes = disclosuresFor(coverageFor(realistic, priced));
  assert.match(notes[0], /1 holding\(s\) have no resolved ticker/);
  assert.match(notes[0], /0\.00% of the book by value/);
});

test('a book that is mostly unpriceable is still withheld', () => {
  // The gate has to keep doing its job. This is the case it exists for: a
  // league table built on the liquid half of a book is a table of who holds
  // large caps.
  const thin = [
    { security_key: 'A', ticker: 'AAPL', value_usd: 1_000_000 },
    { security_key: 'B', ticker: 'NOPRICE', value_usd: 9_000_000 },
  ];
  const cov = coverageFor(thin, priced);
  assert.ok(cov.value_coverage < 0.2);
  assert.match(blockersFor({ periods: 8, coverage: cov })[0], /priced value 10\.0% of the book/);
});

test('count coverage can look poor while the book is fully measurable', () => {
  // Fifty tiny unpriced lines against one large priced position. By count
  // this reads as 2% covered; by value it is essentially complete, and the
  // return computed from it is sound.
  const longTail = [{ security_key: 'A', ticker: 'AAPL', value_usd: 50_000_000_000 }];
  for (let i = 0; i < 50; i += 1) longTail.push({ security_key: `T${i}`, ticker: null, value_usd: 1000 });
  const cov = coverageFor(longTail, priced);
  assert.ok(cov.price_coverage < 0.03, 'by count it looks empty');
  assert.ok(cov.value_coverage > 0.999, 'by value it is complete');
  assert.deepEqual(blockersFor({ periods: 8, coverage: cov }), []);
});

test('too few filed periods still blocks, whatever the coverage', () => {
  const cov = coverageFor(realistic, priced);
  assert.match(blockersFor({ periods: 1, coverage: cov })[0], /only 1 filed period/);
});

test('a security held twice is counted once', () => {
  const dup = [
    { security_key: 'A', ticker: 'AAPL', value_usd: 100 },
    { security_key: 'A', ticker: 'AAPL', value_usd: 100 },
  ];
  assert.equal(coverageFor(dup, priced).securities_held, 1);
});

test('an empty book is not silently evaluable', () => {
  const cov = coverageFor([], priced);
  assert.equal(cov.value_coverage, null);
  assert.match(blockersFor({ periods: 8, coverage: cov })[0], /no holdings recorded/);
});

test('a book with holdings but no reported value is not evaluable', () => {
  // Zero value cannot be weighted, and dividing by it would read as complete.
  const cov = coverageFor([{ security_key: 'A', ticker: 'AAPL', value_usd: 0 }], priced);
  assert.equal(cov.value_coverage, null);
  assert.match(blockersFor({ periods: 8, coverage: cov })[0], /no reported value/);
});
