import test from 'node:test';
import assert from 'node:assert/strict';
import { rowsFromBlock, periodsOf, needsArchive, archiveFiles, selectThirteenF } from '../services/filingHistory.js';

const block = {
  form: ['13F-HR', '10-K', '13F-HR/A', '13F-HR', '13F-HR'],
  accessionNumber: ['a1', 'x1', 'a2', 'a3', 'a4'],
  reportDate: ['2026-06-30', '2026-06-30', '2026-06-30', '2026-03-31', '2025-12-31'],
  filingDate: ['2026-08-14', '2026-02-20', '2026-08-20', '2026-05-15', '2026-02-14'],
  acceptanceDateTime: ['2026-08-14T21:05:00Z', '', '2026-08-20T18:00:00Z', '2026-05-15T20:30:00Z', ''],
};

test('only 13F filings are taken from a mixed index', () => {
  const rows = rowsFromBlock(block);
  assert.equal(rows.length, 4);
  assert.ok(!rows.some((row) => row.form_type === '10-K'));
});

test('a missing acceptance time falls back to a moment no earlier than the truth', () => {
  // The point-in-time rules enter a position after acceptance. Standing in
  // midnight UTC on the filing date is earlier than any real acceptance, so
  // the substitute can never let a backtest trade sooner than it could have.
  const rows = rowsFromBlock(block);
  assert.equal(rows.find((r) => r.accession_number === 'a4').accepted_at, '2026-02-14T00:00:00Z');
  assert.equal(rows.find((r) => r.accession_number === 'a1').accepted_at, '2026-08-14T21:05:00Z');
});

test('an amendment and the filing it restates are both kept, in acceptance order', () => {
  // Both are needed: the amendment restates the original, and applying it
  // before the filing it corrects would restate nothing. EDGAR lists newest
  // first, so the amendment arrives ahead of its original and the order has
  // to be imposed rather than inherited.
  const asEdgarLists = {
    form: ['13F-HR/A', '13F-HR'],
    accessionNumber: ['a2', 'a1'],
    reportDate: ['2026-06-30', '2026-06-30'],
    filingDate: ['2026-08-20', '2026-08-14'],
    acceptanceDateTime: ['2026-08-20T18:00:00Z', '2026-08-14T21:05:00Z'],
  };
  const selected = selectThirteenF(rowsFromBlock(asEdgarLists), 1);
  assert.deepEqual(selected.map((r) => r.accession_number), ['a1', 'a2'],
    'the original must be applied before the amendment that restates it');
});

test('the quarter cap no longer stops at sixteen', () => {
  // The binding limit was here, not in the data. Berkshire has 211 quarters
  // of 13F on EDGAR and this asked for at most 16.
  const many = Array.from({ length: 40 }, (_, i) => ({
    form_type: '13F-HR',
    accession_number: `x${i}`,
    report_date: `${2026 - Math.floor(i / 4)}-${String(((i % 4) + 1) * 3).padStart(2, '0')}-30`,
    accepted_at: `2026-01-0${(i % 9) + 1}T00:00:00Z`,
  }));
  assert.equal(periodsOf(selectThirteenF(many, 40)).length, periodsOf(many).length);
});

test('a request beyond the archive is not an error, just everything there is', () => {
  assert.equal(periodsOf(selectThirteenF(rowsFromBlock(block), 999)).length, 3);
});

test('the archive is only fetched when the recent block cannot answer', () => {
  // A daily run asking for a few quarters must not pay an extra request per
  // manager for history it already has.
  const rows = rowsFromBlock(block);       // three periods
  assert.equal(needsArchive(rows, 3), false);
  assert.equal(needsArchive(rows, 4), true);
});

test('archive files are read newest first', () => {
  const subs = { filings: { files: [
    { name: 'old-002.json', filingTo: '2009-12-31' },
    { name: 'old-001.json', filingTo: '2017-01-08' },
    { name: null },
  ] } };
  assert.deepEqual(archiveFiles(subs).map((f) => f.name), ['old-001.json', 'old-002.json']);
});

test('a filer with no archive is handled without special-casing', () => {
  assert.deepEqual(archiveFiles({}), []);
  assert.deepEqual(archiveFiles({ filings: {} }), []);
});

test('an empty or malformed block yields nothing rather than throwing', () => {
  assert.deepEqual(rowsFromBlock(null), []);
  assert.deepEqual(rowsFromBlock({}), []);
  assert.deepEqual(selectThirteenF(null, 4), []);
});
