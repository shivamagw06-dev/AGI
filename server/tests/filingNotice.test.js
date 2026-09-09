import test from 'node:test';
import assert from 'node:assert/strict';
import { noticesFromBlock, filingPosture, postureMessage } from '../services/filingNotice.js';

/** EDGAR's columnar block shape. */
const block = (rows) => ({
  form: rows.map((r) => r[0]),
  accessionNumber: rows.map((_, i) => `000-${i}`),
  reportDate: rows.map((r) => r[1]),
  filingDate: rows.map((r) => r[2] || r[1]),
});

test('only notices come back, newest report first', () => {
  const rows = noticesFromBlock(block([
    ['13F-HR', '2025-12-31'],
    ['13F-NT', '2026-03-31'],
    ['13F-NT', '2026-06-30'],
    ['4', '2026-01-01'],
    ['SC 13G/A', '2026-02-01'],
  ]));
  assert.deepEqual(rows.map((r) => r.report_date), ['2026-06-30', '2026-03-31']);
});

test('a notice without a report date is not a period', () => {
  // EDGAR occasionally carries a blank reportDate. Treating it as a period
  // would compare an empty string against a real date and win, because '' is
  // less than every date - so it would never be newest, but it would also sit
  // in the list claiming to be a notice for no quarter.
  const rows = noticesFromBlock(block([['13F-NT', ''], ['13F-NT', '2026-06-30']]));
  assert.deepEqual(rows.map((r) => r.report_date), ['2026-06-30']);
});

test('amended notices count as notices', () => {
  const rows = noticesFromBlock(block([['13F-NT/A', '2026-06-30']]));
  assert.equal(rows.length, 1);
});

test('a notice newer than the last holdings report means it reports elsewhere', () => {
  // Vanguard: 13F-HR through 2025-12-31, then 13F-NT for 2026-03-31 and
  // 2026-06-30. Not late - reporting through a different filer.
  const result = filingPosture({
    newestHoldingsReport: '2025-12-31',
    notices: [{ report_date: '2026-06-30' }, { report_date: '2026-03-31' }],
  });
  assert.equal(result.posture, 'reports_elsewhere');
  assert.equal(result.notice_period, '2026-06-30');
});

test('no notice at all is simply current, however old the holdings report is', () => {
  // Scion: newest filing of any kind is a 13F-HR for 2025-09-30. It stopped
  // filing. That is a different fact from reporting elsewhere, and the
  // existing staleness rule is the right one to describe it.
  const result = filingPosture({ newestHoldingsReport: '2025-09-30', notices: [] });
  assert.equal(result.posture, 'current');
  assert.equal(result.notice_period, null);
});

test('an older notice does not override a newer holdings report', () => {
  // A manager can file a notice one quarter and resume reporting the next.
  // Reading the stale notice as current would hide a live book.
  const result = filingPosture({
    newestHoldingsReport: '2026-06-30',
    notices: [{ report_date: '2026-03-31' }],
  });
  assert.equal(result.posture, 'current');
});

test('a notice for the same period as a holdings report does not win', () => {
  // Filing both for one quarter means holdings were disclosed and the notice
  // covers some other part of the group. The table is what carries
  // information, so it takes precedence.
  const result = filingPosture({
    newestHoldingsReport: '2026-06-30',
    notices: [{ report_date: '2026-06-30' }],
  });
  assert.equal(result.posture, 'current');
  assert.equal(result.notice_period, null);
});

test('a manager with notices but no holdings report ever is still reports_elsewhere', () => {
  const result = filingPosture({ newestHoldingsReport: null, notices: [{ report_date: '2026-06-30' }] });
  assert.equal(result.posture, 'reports_elsewhere');
});

test('nothing at all is none, not current', () => {
  assert.equal(filingPosture({}).posture, 'none');
  assert.equal(filingPosture({ newestHoldingsReport: null, notices: [] }).posture, 'none');
});

test('the message tells the reader what to do, not just what happened', () => {
  // "Latest available 13F reports 2025-12-31" invites waiting for the next
  // one, which will not come in that form.
  const message = postureMessage({
    posture: 'reports_elsewhere',
    notice_period: '2026-06-30',
    newestHoldingsReport: '2025-12-31',
  });
  assert.match(message, /13F-NT/);
  assert.match(message, /2026-06-30/);
  assert.match(message, /another filer/i);
  assert.match(message, /2025-12-31/);
});

test('a current manager gets no message', () => {
  assert.equal(postureMessage({ posture: 'current', newestHoldingsReport: '2026-06-30' }), null);
});
