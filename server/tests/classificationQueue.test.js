import test from 'node:test';
import assert from 'node:assert/strict';
import { classificationQueue } from '../services/classificationQueue.js';

const asOf = new Date('2026-09-10T00:00:00Z');
const daysAgo = (n) => new Date(asOf.getTime() - n * 86_400_000).toISOString();
const sec = (key) => ({ key, ticker: key });
const keys = (rows) => rows.map((r) => r.key);

test('the bug this exists to fix: a second night classifies different securities', () => {
  // The old code sliced the first N of holdings order every night. Holdings
  // order does not change, so night two did exactly what night one did and the
  // table never grew past the first batch.
  const securities = Array.from({ length: 10 }, (_, i) => sec(`S${i}`));

  const night1 = classificationQueue({ securities, classified: [], limit: 4, asOf });
  assert.deepEqual(keys(night1), ['S0', 'S1', 'S2', 'S3']);

  const afterNight1 = night1.map((s) => ({ security_key: s.key, source_as_of: daysAgo(1) }));
  const night2 = classificationQueue({ securities, classified: afterNight1, limit: 4, asOf });
  assert.deepEqual(keys(night2), ['S4', 'S5', 'S6', 'S7']);

  const afterNight2 = [...afterNight1, ...night2.map((s) => ({ security_key: s.key, source_as_of: daysAgo(1) }))];
  const night3 = classificationQueue({ securities, classified: afterNight2, limit: 4, asOf });
  assert.deepEqual(keys(night3), ['S8', 'S9']);
});

test('nothing left to do returns nothing, rather than redoing recent work', () => {
  const securities = [sec('A'), sec('B')];
  const classified = securities.map((s) => ({ security_key: s.key, source_as_of: daysAgo(1) }));
  assert.deepEqual(classificationQueue({ securities, classified, limit: 60, asOf }), []);
});

test('an unclassified security always outranks a stale one', () => {
  // Refreshing an old row while something has never been classified at all
  // is how the backlog stops draining.
  const securities = [sec('OLD'), sec('NEW')];
  const classified = [{ security_key: 'OLD', source_as_of: daysAgo(3650) }];
  assert.deepEqual(keys(classificationQueue({ securities, classified, limit: 1, asOf })), ['NEW']);
});

test('once the backlog is clear the oldest are refreshed first', () => {
  const securities = [sec('RECENT'), sec('ANCIENT'), sec('MIDDLE')];
  const classified = [
    { security_key: 'RECENT', source_as_of: daysAgo(200) },
    { security_key: 'ANCIENT', source_as_of: daysAgo(900) },
    { security_key: 'MIDDLE', source_as_of: daysAgo(400) },
  ];
  assert.deepEqual(keys(classificationQueue({ securities, classified, limit: 3, asOf })), ['ANCIENT', 'MIDDLE', 'RECENT']);
});

test('a security is only as stale as its freshest row', () => {
  // Classifications are keyed by valid_from, so one security carries several
  // rows. Reading the oldest would put a security that was re-classified last
  // night back at the front of the queue every night.
  const classified = [
    { security_key: 'A', source_as_of: daysAgo(900) },
    { security_key: 'A', source_as_of: daysAgo(2) },
  ];
  assert.deepEqual(classificationQueue({ securities: [sec('A')], classified, limit: 5, asOf }), []);
});

test('a classification with no usable date is stale, not fresh', () => {
  // Not knowing when something was classified is not evidence that it was
  // classified recently, and guessing fresh would strand the row forever.
  for (const value of [null, undefined, '', 'not a date']) {
    const out = classificationQueue({ securities: [sec('A')], classified: [{ security_key: 'A', source_as_of: value }], limit: 5, asOf });
    assert.deepEqual(keys(out), ['A'], `source_as_of ${JSON.stringify(value)} should be treated as stale`);
  }
});

test('an undated row still loses to one that has never been classified', () => {
  const securities = [sec('UNDATED'), sec('NEVER')];
  const classified = [{ security_key: 'UNDATED', source_as_of: null }];
  assert.deepEqual(keys(classificationQueue({ securities, classified, limit: 1, asOf })), ['NEVER']);
});

test('keys match case-insensitively', () => {
  // security_key is upper-cased on the way into the table by keyOf, but the
  // caller's own key need not be, and a case mismatch would make every
  // security look unclassified forever.
  const out = classificationQueue({
    securities: [{ key: 'us0378331005' }],
    classified: [{ security_key: 'US0378331005', source_as_of: daysAgo(1) }],
    limit: 5, asOf,
  });
  assert.deepEqual(out, []);
});

test('the limit is respected and nonsense limits yield nothing', () => {
  const securities = Array.from({ length: 100 }, (_, i) => sec(`S${i}`));
  assert.equal(classificationQueue({ securities, limit: 7, asOf }).length, 7);
  for (const limit of [0, -1, NaN, null, 'ten']) {
    assert.deepEqual(classificationQueue({ securities, limit, asOf }), [], `limit ${JSON.stringify(limit)}`);
  }
});

test('a security without a key is skipped rather than queued', () => {
  const out = classificationQueue({ securities: [{ key: '' }, { key: null }, sec('REAL')], limit: 5, asOf });
  assert.deepEqual(keys(out), ['REAL']);
});

test('nothing in yields nothing out, without throwing', () => {
  assert.deepEqual(classificationQueue(), []);
  assert.deepEqual(classificationQueue({}), []);
});

test('the staleness window is honoured at its edges', () => {
  const just = (days) => classificationQueue({
    securities: [sec('A')], classified: [{ security_key: 'A', source_as_of: daysAgo(days) }],
    limit: 5, asOf, staleAfterDays: 180,
  });
  assert.deepEqual(just(181), [{ key: 'A', ticker: 'A' }]);
  assert.deepEqual(just(179), []);
});

test('a row saying Unclassified is a failed attempt, not a result', () => {
  // How SPY sat at $326bn outside every sector. It was classified before
  // there was any way to recognise a fund; the attempt produced Unclassified;
  // the row then looked fresh for ever, so the fund logic that arrived later
  // never saw it.
  const securities = [sec('SPY')];
  const failed = [{ security_key: 'SPY', sector: 'Unclassified', source_as_of: daysAgo(1) }];
  assert.deepEqual(keys(classificationQueue({ securities, classified: failed, limit: 5, asOf })), ['SPY']);

  const succeeded = [{ security_key: 'SPY', sector: 'Funds & ETFs', source_as_of: daysAgo(1) }];
  assert.deepEqual(classificationQueue({ securities, classified: succeeded, limit: 5, asOf }), []);
});

test('a real classification outranks an Unclassified one for the same security', () => {
  // Both rows exist: the failed attempt and the later success. The security
  // is classified, and retrying it every night would waste the whole limit.
  const classified = [
    { security_key: 'SPY', sector: 'Unclassified', source_as_of: daysAgo(400) },
    { security_key: 'SPY', sector: 'Funds & ETFs', source_as_of: daysAgo(1) },
  ];
  assert.deepEqual(classificationQueue({ securities: [sec('SPY')], classified, limit: 5, asOf }), []);
});

test('a success stands whichever order the rows arrive in', () => {
  // Rows come back ordered by key then date, but nothing guarantees a failed
  // attempt precedes the success that replaced it - a later re-attempt can
  // fail on a network error. Taking whichever row happens to be last would
  // then retry a security whose sector is perfectly well known.
  const success = { security_key: 'SPY', sector: 'Funds & ETFs', source_as_of: daysAgo(1) };
  const failure = { security_key: 'SPY', sector: 'Unclassified', source_as_of: daysAgo(400) };
  assert.deepEqual(classificationQueue({ securities: [sec('SPY')], classified: [failure, success], limit: 5, asOf }), []);
  assert.deepEqual(classificationQueue({ securities: [sec('SPY')], classified: [success, failure], limit: 5, asOf }), []);
});

test('retrying failures never starves work never attempted', () => {
  // The stall this must not reintroduce. A thousand permanently unresolvable
  // securities would otherwise fill every slot of a sixty-a-night limit.
  const securities = [sec('FAILED'), sec('NEW')];
  const classified = [{ security_key: 'FAILED', sector: 'Unclassified', source_as_of: daysAgo(1) }];
  assert.deepEqual(keys(classificationQueue({ securities, classified, limit: 1, asOf })), ['NEW']);
});
