import test from 'node:test';
import assert from 'node:assert/strict';
import { withinWindow, scanOrder, mergeByWindow } from '../services/managerCiks.js';

const filing = (accession, report_date) => ({ accession_number: accession, report_date });
const group = (cik, entry, filings) => ({ entry: { cik, ...entry }, filings });

test('a null bound is open, not closed', () => {
  // The failure this prevents: reading a null effective_from as "nothing
  // qualifies" drops a predecessor's whole history, and an empty result is
  // indistinguishable from a filer that never filed.
  assert.equal(withinWindow({ effective_from: null, effective_to: '2024-06-30' }, '2006-03-30'), true);
  assert.equal(withinWindow({ effective_from: '2024-09-30', effective_to: null }, '2026-06-30'), true);
  assert.equal(withinWindow({ effective_from: null, effective_to: null }, '2015-12-31'), true);
});

test('bounds are inclusive at both ends', () => {
  // BlackRock Finance's last holdings report is 2024-06-30 and its window ends
  // there. An exclusive bound would drop the very filing the boundary names.
  const window = { effective_from: '2006-03-30', effective_to: '2024-06-30' };
  assert.equal(withinWindow(window, '2006-03-30'), true);
  assert.equal(withinWindow(window, '2024-06-30'), true);
  assert.equal(withinWindow(window, '2024-09-30'), false);
  assert.equal(withinWindow(window, '2006-01-01'), false);
});

test('a malformed period is never inside a window', () => {
  assert.equal(withinWindow({}, ''), false);
  assert.equal(withinWindow({}, null), false);
  assert.equal(withinWindow({}, 'sometime in 2024'), false);
});

test('the primary CIK is scanned first', () => {
  // A run cut short by its ceiling should lose the oldest quarters, not the
  // newest - the current book matters more than deep history.
  const order = scanOrder('0002012383', [
    { cik: '0001364742', role: 'predecessor' },
    { cik: '0001086364', role: 'predecessor' },
  ]);
  assert.deepEqual(order.map((e) => e.cik), ['0002012383', '0001364742', '0001086364']);
  assert.equal(order[0].role, 'primary');
});

test('a CIK listed twice is scanned once', () => {
  // The roster CIK also appearing in the extras table would otherwise be
  // fetched and ingested twice.
  const order = scanOrder('0002012383', [{ cik: '0002012383', role: 'primary' }]);
  assert.equal(order.length, 1);
});

test('succession stitches two CIKs into one continuous history', () => {
  // The case this was built for: 69 periods under the predecessor, the current
  // book under the successor, no overlap.
  const { filings, outside, conflicts } = mergeByWindow([
    group('0002012383', { effective_from: '2024-09-30', effective_to: null }, [
      filing('new-1', '2026-06-30'), filing('new-2', '2024-09-30'),
    ]),
    group('0001364742', { effective_from: null, effective_to: '2024-06-30' }, [
      filing('old-1', '2024-06-30'), filing('old-2', '2006-03-30'),
    ]),
  ]);
  assert.deepEqual(filings.map((f) => f.accession_number).sort(), ['new-1', 'new-2', 'old-1', 'old-2']);
  assert.equal(outside.length, 0);
  assert.equal(conflicts.length, 0);
});

test('a filing outside every window is reported, not silently dropped', () => {
  // A predecessor that kept filing past its boundary, or a boundary set a
  // quarter wrong. Dropping it quietly truncates history and looks identical
  // to a filer that stopped.
  const { filings, outside } = mergeByWindow([
    group('0001364742', { effective_to: '2024-06-30' }, [
      filing('old-1', '2024-06-30'), filing('too-new', '2024-09-30'),
    ]),
  ]);
  assert.deepEqual(filings.map((f) => f.accession_number), ['old-1']);
  assert.equal(outside.length, 1);
  assert.equal(outside[0].report_date, '2024-09-30');
  assert.equal(outside[0].cik, '0001364742');
});

test('a period claimed by two CIKs goes to the first in scan order, and is reported', () => {
  // Declared windows should make this impossible, so if it happens the windows
  // are wrong. Deterministic beats arbitrary, and the conflict has to be named
  // or the boundary never gets fixed.
  const { filings, conflicts } = mergeByWindow([
    group('0002012383', { effective_from: null, effective_to: null }, [filing('primary-1', '2024-06-30')]),
    group('0001364742', { effective_from: null, effective_to: null }, [filing('other-1', '2024-06-30')]),
  ]);
  assert.deepEqual(filings.map((f) => f.accession_number), ['primary-1']);
  assert.equal(conflicts.length, 1);
  assert.equal(conflicts[0].kept, '0002012383');
  assert.equal(conflicts[0].dropped, '0001364742');
});

test('the same accession from two blocks is ingested once', () => {
  // A filing appears in both a recent block and an archive file. Ingesting it
  // twice deletes and rewrites the same holdings for no reason.
  const { filings } = mergeByWindow([
    group('0001364742', {}, [filing('dupe', '2020-06-30'), filing('dupe', '2020-06-30')]),
  ]);
  assert.equal(filings.length, 1);
});

test('an amendment for a claimed period is kept, not treated as a conflict', () => {
  // Two filings, one period, same CIK - the original and its 13F-HR/A. Both
  // are needed: the amendment is applied after the filing it restates.
  const { filings, conflicts } = mergeByWindow([
    group('0001364742', {}, [filing('original', '2020-06-30'), filing('amendment', '2020-06-30')]),
  ]);
  assert.deepEqual(filings.map((f) => f.accession_number), ['original', 'amendment']);
  assert.equal(conflicts.length, 0);
});

test('nothing collected yields nothing, without throwing', () => {
  assert.deepEqual(mergeByWindow(), { filings: [], outside: [], conflicts: [] });
  assert.deepEqual(mergeByWindow([]).filings, []);
  assert.deepEqual(scanOrder(null, []), []);
});
