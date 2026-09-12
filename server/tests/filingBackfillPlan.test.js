import test from 'node:test';
import assert from 'node:assert/strict';
import { ingestPlan, isIngested } from '../services/filingBackfillPlan.js';

const filing = (accession, report_date = '2026-06-30') => ({ accession_number: accession, report_date });

test('a filing already stored with holdings is not fetched again', () => {
  const plan = ingestPlan({
    available: [filing('0001-A'), filing('0002-B')],
    stored: [{ accession_number: '0001-A', holdings_count: 1_482 }],
  });
  assert.deepEqual(plan.fetch.map((f) => f.accession_number), ['0002-B']);
  assert.equal(plan.skipped, 1);
});

test('a stored filing with zero holdings is fetched again', () => {
  // A previous run wrote the filing row and then failed to parse its table.
  // Counting that as done makes the gap permanent, because nothing else in the
  // system ever revisits a filing it believes it has.
  const plan = ingestPlan({
    available: [filing('0001-A')],
    stored: [{ accession_number: '0001-A', holdings_count: 0 }],
  });
  assert.equal(plan.fetch.length, 1);
  assert.equal(plan.skipped, 0);
});

test('a null holdings_count is fetched again rather than trusted', () => {
  // Number(null) is 0 and Number.isFinite(0) is true, so the obvious guard
  // reads null as a real count. Whichever way that lands it must land on
  // fetching: a wasted request costs seconds, a skipped filing is a hole.
  assert.equal(isIngested({ accession_number: 'x', holdings_count: null }), false);
  assert.equal(isIngested({ accession_number: 'x' }), false);
  assert.equal(isIngested({ accession_number: 'x', holdings_count: 'many' }), false);
});

test('an amendment is fetched even when the original for that period is stored', () => {
  // A 13F-HR/A carries its own accession, so it is simply not among the stored
  // ones. This is the case that must never regress: an amendment restates a
  // quarter, and skipping it leaves the superseded numbers on the page.
  const plan = ingestPlan({
    available: [filing('0001-A'), filing('0001-A-AMENDED')],
    stored: [{ accession_number: '0001-A', holdings_count: 900 }],
  });
  assert.deepEqual(plan.fetch.map((f) => f.accession_number), ['0001-A-AMENDED']);
});

test('refetch ignores the cache entirely', () => {
  // The escape hatch for when the stored rows are wrong in a way holdings_count
  // cannot show - a parser fix, a scale correction.
  const plan = ingestPlan({
    available: [filing('0001-A'), filing('0002-B')],
    stored: [
      { accession_number: '0001-A', holdings_count: 1_482 },
      { accession_number: '0002-B', holdings_count: 900 },
    ],
    refetch: true,
  });
  assert.equal(plan.fetch.length, 2);
  assert.equal(plan.skipped, 0);
});

test('a manager whose filings are all stored plans no fetches but still reports a total', () => {
  // The distinction the run record depends on. Zero fetches with a non-zero
  // total is "already complete"; zero of both is a manager with no 13F at all,
  // which is an error the collector raises.
  const plan = ingestPlan({
    available: [filing('0001-A')],
    stored: [{ accession_number: '0001-A', holdings_count: 12 }],
  });
  assert.equal(plan.fetch.length, 0);
  assert.equal(plan.total, 1);
});

test('nothing available plans nothing, without throwing on missing arguments', () => {
  assert.deepEqual(ingestPlan(), { fetch: [], skipped: 0, total: 0 });
  assert.equal(ingestPlan({ available: [filing('a')] }).fetch.length, 1);
});

test('the backfill converges: a truncated run advances instead of redoing its head', () => {
  // The failure this exists to prevent. Managers are ordered by display_name
  // and a ceiling-truncated run abandons the tail, so without a skip the next
  // run spends its whole budget re-fetching the same head forever.
  const available = ['q1', 'q2', 'q3', 'q4'].map((q) => filing(q));
  let stored = [];

  // Two filings per run, which is what a tight ceiling allows.
  for (let run = 0; run < 2; run += 1) {
    const plan = ingestPlan({ available, stored });
    for (const f of plan.fetch.slice(0, 2)) {
      stored = stored.concat({ accession_number: f.accession_number, holdings_count: 500 });
    }
  }

  assert.deepEqual(stored.map((s) => s.accession_number), ['q1', 'q2', 'q3', 'q4']);
  assert.equal(ingestPlan({ available, stored }).fetch.length, 0);
});
