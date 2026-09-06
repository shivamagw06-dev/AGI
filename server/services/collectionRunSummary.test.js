/**
 * The run record decides what an operator believes about the data. These tests
 * cover the three pure functions behind that judgement - which status a run
 * earns, what its counters mean, and when the next run is due - because each
 * has a failure mode that reads as good news.
 *
 *   node --test server/services/collectionRunSummary.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
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

// ---------------------------------------------------------------------------
// The shape the scheduled collector actually produces
// ---------------------------------------------------------------------------

test('a bulk refresh result is counted, not read as empty', () => {
  // performInstitutionalRefresh returns { filings: [...] } per manager, while a
  // single-manager refresh returns { filing, ingestion }. Only the second shape
  // was handled, so every completed scheduled run reported filings: 0,
  // holdings rows: 0, amendments: 0 however much it had written.
  const summary = summariseRefresh({
    results: [
      { ok: true, slug: 'berkshire-hathaway', filings: [
        { status: 'ingested', holdings: 45, form_type: '13F-HR' },
        { status: 'ingested', holdings: 44, form_type: '13F-HR/A' },
      ] },
      { ok: true, slug: 'citadel-advisors', filings: [
        { status: 'ingested', holdings: 13572, form_type: '13F-HR' },
      ] },
      { ok: false, manager: { slug: 'norges-bank' }, error: 'no information table' },
    ],
  });

  assert.equal(summary.managersAttempted, 3);
  assert.equal(summary.managersSucceeded, 2);
  assert.equal(summary.filingsIngested, 3);
  assert.equal(summary.holdingsRows, 45 + 44 + 13572);
  assert.equal(summary.amendmentsDetected, 1, 'the /A filing must be counted');
  assert.equal(summary.failures[0].manager, 'norges-bank');
});

test('the single-manager shape still works', () => {
  const summary = summariseRefresh({
    results: [{ ok: true, filing: { form_type: '13F-HR/A' }, ingestion: { status: 'ingested', holdings: 8 } }],
  });
  assert.equal(summary.filingsIngested, 1);
  assert.equal(summary.holdingsRows, 8);
  assert.equal(summary.amendmentsDetected, 1);
});

test('a run cut short still reports the managers that finished', () => {
  // The ceiling abandons the refresh promise, so the collector summarises what
  // it watched complete. Reporting zeroes for committed work is the failure
  // this guards: someone reads the record and concludes nothing ran.
  const partial = summariseRefresh({
    results: [
      { ok: true, slug: 'akre-capital', filings: [{ status: 'ingested', holdings: 22, form_type: '13F-HR' }] },
      { ok: true, slug: 'appaloosa',    filings: [{ status: 'ingested', holdings: 38, form_type: '13F-HR' }] },
    ],
  });
  assert.equal(partial.managersSucceeded, 2);
  assert.equal(partial.holdingsRows, 60);
});

test('a filing that was not ingested is not counted as one', () => {
  const summary = summariseRefresh({
    results: [{ ok: true, filings: [
      { status: 'ingested', holdings: 10, form_type: '13F-HR' },
      { status: 'needs_review', holdings: 0, form_type: '13F-HR/A' },
    ] }],
  });
  assert.equal(summary.filingsIngested, 1);
  assert.equal(summary.holdingsRows, 10);
});

test('the collector accumulates progress instead of trusting the final result', () => {
  // A ceiling abandons the refresh promise. If the script only summarises that
  // result, an aborted run reports zeroes for work already written.
  const script = readFileSync(new URL('../scripts/collectInstitutionalFilings.mjs', import.meta.url), 'utf8');
  assert.match(script, /onManagerDone:/,
    'the collector must be told as each manager finishes');
  assert.match(script, /summariseRefresh\(refresh \|\| \{ results: completed \}/,
    'on abort it must summarise what it observed completing, not the abandoned result');
});

// ---------------------------------------------------------------------------
// The run that reported success after a database timeout
// ---------------------------------------------------------------------------

test('a run cut short by an error is never a success', () => {
  // Observed in production: "failed after 2592.6s: canceling statement due to
  // statement timeout", then "status=success". `attempted` counts only the
  // managers that reported finishing, so on a truncated run it always equals
  // `succeeded` and 48/48 looked complete while three of fifty-one never ran.
  assert.equal(deriveStatus({
    attempted: 48, succeeded: 48, roster: 51, error: 'canceling statement due to statement timeout',
  }), 'partial');
});

test('an error is not a success even when the whole roster was covered', () => {
  // Isolates the error branch. The previous case had 48 of 51 covered, so the
  // roster check returned partial on its own and deleting the error check
  // changed nothing - the test passed while asserting nothing.
  assert.equal(deriveStatus({
    attempted: 51, succeeded: 51, roster: 51, error: 'canceling statement due to statement timeout',
  }), 'partial');
});

test('covering fewer managers than the roster is partial, error or not', () => {
  assert.equal(deriveStatus({ attempted: 48, succeeded: 48, roster: 51 }), 'partial');
  assert.equal(deriveStatus({ attempted: 51, succeeded: 51, roster: 51 }), 'success');
});

test('a clean full run is still a success', () => {
  assert.equal(deriveStatus({ attempted: 51, succeeded: 51, roster: 51, error: null }), 'success');
  // And with no roster known, the old behaviour stands rather than failing shut
  // on every manual single-manager refresh.
  assert.equal(deriveStatus({ attempted: 1, succeeded: 1 }), 'success');
});

test('the summary carries what the run was asked to cover', () => {
  const summary = summariseRefresh({ results: [
    { ok: true, filings: [{ status: 'ingested', holdings: 10, form_type: '13F-HR' }] },
  ] }, 51);
  assert.equal(summary.managersInRoster, 51);
  assert.equal(summary.managersAttempted, 1, 'attempted is what reported back');
  assert.equal(summary.managersSucceeded, 1);
});

test('the collector reports against the roster, not against what finished', () => {
  const script = readFileSync(new URL('../scripts/collectInstitutionalFilings.mjs', import.meta.url), 'utf8');
  assert.match(script, /onRoster:/, 'the collector must be told the roster size before work starts');
  assert.match(script, /roster: work\.managersInRoster/, 'the status must be derived against the roster');
  assert.match(script, /not reached/, 'the log must say how many managers were never reached');
});
