/**
 * The run record decides what an operator believes about the data. These tests
 * cover the three pure functions behind that judgement - which status a run
 * earns, what its counters mean, and when the next run is due - because each
 * has a failure mode that reads as good news.
 *
 *   node --test server/services/institutionalCollectionRuns.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { deriveStatus, summariseRefresh, nextScheduledAt } from './collectionRunSummary.js';

test('a run where every manager succeeded is a success', () => {
  assert.equal(deriveStatus({ attempted: 51, succeeded: 51 }), 'success');
});

test('a partly successful run is never reported as success', () => {
  // The failure this guards: 3 of 51 managers collected, dashboard shows green,
  // and the gap is discovered weeks later in a client conversation.
  assert.equal(deriveStatus({ attempted: 51, succeeded: 3 }), 'partial');
  assert.equal(deriveStatus({ attempted: 51, succeeded: 50 }), 'partial');
});

test('a run where nothing succeeded is a failure, exception or not', () => {
  assert.equal(deriveStatus({ attempted: 51, succeeded: 0 }), 'failed');
  assert.equal(deriveStatus({ attempted: 51, succeeded: 0, error: 'boom' }), 'failed');
});

test('hitting the time ceiling is aborted, not failed', () => {
  // It says something different: the work was fine, there was too much of it.
  assert.equal(deriveStatus({ attempted: 51, succeeded: 20, aborted: true }), 'aborted');
});

test('a run with nothing to do is a success, not a failure', () => {
  assert.equal(deriveStatus({ attempted: 0, succeeded: 0 }), 'success');
  assert.equal(deriveStatus({ attempted: 0, succeeded: 0, error: 'could not reach EDGAR' }), 'failed');
});

test('the summary counts only what actually happened', () => {
  const summary = summariseRefresh({
    results: [
      { ok: true, filing: { form_type: '13F-HR' }, ingestion: { status: 'ingested', holdings: 120 } },
      { ok: true, filing: { form_type: '13F-HR/A' }, ingestion: { status: 'ingested', holdings: 80 } },
      { ok: true, filing: { form_type: '13F-HR' }, ingestion: { status: 'unchanged', holdings: 0 } },
      { ok: false, manager: { slug: 'bridgewater' }, error: 'no information table found' },
    ],
  });
  assert.equal(summary.managersAttempted, 4);
  assert.equal(summary.managersSucceeded, 3);
  assert.equal(summary.filingsIngested, 2, 'an unchanged filing was not ingested');
  assert.equal(summary.holdingsRows, 200);
  assert.equal(summary.amendmentsDetected, 1, 'only the /A form is an amendment');
  assert.deepEqual(summary.failures, [
    { manager: 'bridgewater', error: 'no information table found' },
  ]);
});

test('a failed refresh summarises to zeroes rather than throwing', () => {
  // The collector calls this after a crash, so it must survive null.
  const summary = summariseRefresh(null);
  assert.equal(summary.managersAttempted, 0);
  assert.equal(summary.managersSucceeded, 0);
  assert.deepEqual(summary.failures, []);
});

test('a manager failure with no reason still names the manager', () => {
  const summary = summariseRefresh({ results: [{ ok: false, manager: { slug: 'citadel' } }] });
  assert.equal(summary.failures[0].manager, 'citadel');
  assert.match(summary.failures[0].error, /no reason recorded/);
});

test('the next scheduled run is the next occurrence, not today when today has passed', () => {
  const before = new Date('2026-09-06T05:00:00Z');
  assert.equal(nextScheduledAt('20 6 * * *', before), '2026-09-06T06:20:00.000Z');
  const after = new Date('2026-09-06T07:00:00Z');
  assert.equal(nextScheduledAt('20 6 * * *', after), '2026-09-07T06:20:00.000Z');
});

test('an expression this parser does not understand returns null, not a guess', () => {
  // A confidently wrong "next run" in an operations panel is worse than a blank.
  for (const expression of ['*/5 * * * *', '0 6 * * 1-5', '0 0 1 * *', '', null, 'nonsense']) {
    assert.equal(nextScheduledAt(expression), null, `${expression} should not parse`);
  }
});

test('an out-of-range time is rejected rather than wrapping', () => {
  assert.equal(nextScheduledAt('70 6 * * *'), null);
  assert.equal(nextScheduledAt('20 25 * * *'), null);
});
