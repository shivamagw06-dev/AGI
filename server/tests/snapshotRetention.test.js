import test from 'node:test';
import assert from 'node:assert/strict';
import {
  cutoff, dayWindows, refuseReason, plannedSteps, RAW_FACTORS_KEEP_DAYS, ROW_KEEP_DAYS,
} from '../services/snapshotRetention.js';

test('the row cutoff clears the longest reader with margin', () => {
  // The longest reader is the 20-day confluence horizon, whose settlement
  // window runs eight hours past due. An outcome that settles late must still
  // find its price.
  assert.ok(ROW_KEEP_DAYS > 20 + 1, `${ROW_KEEP_DAYS} days must exceed the 20-day horizon and its window`);
});

test('raw_factors is kept far longer than anything reads it', () => {
  // The deepest reader of that column is loadRecentSnapshots at 90 minutes.
  assert.ok(RAW_FACTORS_KEEP_DAYS >= 2, 'a session boundary must not fall inside the kept window');
});

test('work is split into day-sized windows, oldest first', () => {
  // A single statement across four million rows writes a WAL record for each
  // and builds a temp footprint large enough to exhaust the disk - which is
  // what happened when this table was scanned in one go.
  const w = dayWindows('2026-08-09T04:00:00Z', '2026-08-13T00:00:00Z');
  assert.equal(w.length, 4);
  assert.ok(w[0].from < w[1].from, 'oldest first');
  assert.ok(w.at(-1).to <= '2026-08-13T00:00:00Z', 'never past the cutoff');
});

test('no window extends past the cutoff', () => {
  const w = dayWindows('2026-08-09T00:00:00Z', '2026-08-10T06:30:00Z');
  assert.equal(w.at(-1).to, '2026-08-10T06:30:00.000Z');
});

test('nothing to do when the oldest row is already inside the window', () => {
  assert.deepEqual(dayWindows('2026-09-08T00:00:00Z', '2026-08-13T00:00:00Z'), []);
  assert.deepEqual(dayWindows('bad', '2026-08-13T00:00:00Z'), []);
});

test('a cutoff in the future is refused', () => {
  // The guard against a miscomputed window taking live data with it.
  const r = refuseReason({ cutoffAt: '2027-01-01T00:00:00Z', newest: '2026-09-08T00:00:00Z', asOf: '2026-09-08T12:00:00Z' });
  assert.match(r, /not in the past/);
});

test('a cutoff past the newest row is refused, not run', () => {
  // That would clear the entire table, including the rows the engines are
  // reading right now.
  const r = refuseReason({ cutoffAt: '2026-09-08T00:00:00Z', newest: '2026-09-07T00:00:00Z', asOf: '2026-09-09T00:00:00Z' });
  assert.match(r, /would clear the whole table/);
});

test('a sane cutoff is allowed', () => {
  assert.equal(refuseReason({ cutoffAt: '2026-08-15T00:00:00Z', newest: '2026-09-08T00:00:00Z', asOf: '2026-09-09T00:00:00Z' }), null);
});

test('the cutoff is computed backwards from the run time', () => {
  assert.equal(cutoff(25, '2026-09-09T10:00:00Z'), '2026-08-15T10:00:00.000Z');
  assert.equal(cutoff(3, '2026-09-09T10:00:00Z'), '2026-09-06T10:00:00.000Z');
});

test('delete runs before blanking, so rows about to be removed are not rewritten first', () => {
  const names = plannedSteps(new Date('2026-09-09T00:00:00Z')).map((s) => s.name);
  assert.deepEqual(names, ['delete', 'blank-factors']);
});

test('the delete step cuts further back than the blanking step', () => {
  const [remove, blank] = plannedSteps(new Date('2026-09-09T00:00:00Z'));
  assert.ok(
    Date.parse(remove.cutoffAt) < Date.parse(blank.cutoffAt),
    'deleting must never reach rows the blanking step still leaves readable',
  );
});
