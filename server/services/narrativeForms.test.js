import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { baseForm, formKind, summariseForms } from './narrativeForms.js';

/**
 * The intelligence layer reads publications, so the first question is which
 * filings contain any. A 13F-HR is a table of positions with no prose in it;
 * an ARS is the annual report where Berkshire's letter lives. Sorting one from
 * the other is the whole job of this file, and getting it wrong either hands
 * an extractor a spreadsheet or hides the only document worth reading.
 */
describe('what a form is worth to a reader', () => {
  test('the forms that carry a manager writing at length', () => {
    // ARS is the one that matters most and is easiest to overlook: Berkshire's
    // 2025 letter was filed as an annual report to shareholders, not as part
    // of the 10-K, and nothing about the form name says "letter".
    for (const form of ['ARS', '10-K', '20-F', 'N-CSR', 'DEF 14A']) {
      assert.equal(formKind(form), 'narrative', form);
    }
  });

  test('13D is intent and 13F is not', () => {
    // Schedule 13D Item 4 states what the holder means to do with the stake.
    // A 13F states only what was held on one date.
    assert.equal(formKind('SC 13D'), 'intent');
    assert.equal(formKind('SC 13G'), 'intent');
    assert.equal(formKind('13F-HR'), 'positions');
    assert.equal(formKind('4'), 'positions');
  });

  test('an amendment is the same kind of document as what it amends', () => {
    assert.equal(baseForm('13F-HR/A'), '13F-HR');
    assert.equal(formKind('SC 13D/A'), 'intent');
    assert.equal(formKind('10-K/A'), 'narrative');
    assert.equal(baseForm('  sc 13d/a  '), 'SC 13D');
  });

  test('an unfamiliar form is unclassified, not assumed', () => {
    // Guessing would hide it. Left null, it appears in the report as a
    // question - which is what a form type nobody has looked at should be.
    assert.equal(formKind('N-CEN'), null);
    assert.equal(formKind('UPLOAD'), null);
    assert.equal(formKind(''), null);
    assert.equal(formKind(null), null);
  });
});

describe('summarising a filer', () => {
  test('amendments fold into the base form but every filing is counted', () => {
    // A manager that amends constantly is telling you something, so the count
    // is of filings rather than of distinct forms.
    const { rows } = summariseForms(['13F-HR', '13F-HR/A', '13F-HR', 'SC 13D']);
    assert.deepEqual(rows.find((row) => row.form === '13F-HR'),
      { form: '13F-HR', count: 3, kind: 'positions' });
  });

  test('a filer with nothing to read is visibly separate from one with plenty', () => {
    // Citadel files positions and stakes; Berkshire files an annual report.
    // The page treats them differently and this is where that divides.
    const quiet = summariseForms(['13F-HR', '13F-HR', 'SC 13G']);
    assert.equal(quiet.narrative.length, 0);
    assert.equal(quiet.intent.length, 1);

    const loud = summariseForms(['ARS', '10-K', '13F-HR', 'SC 13D']);
    assert.deepEqual(loud.narrative.map((row) => row.form).sort(), ['10-K', 'ARS']);
  });

  test('unfamiliar forms are surfaced rather than dropped', () => {
    const { unclassified, total } = summariseForms(['N-CEN', 'N-CEN', '13F-HR']);
    assert.deepEqual(unclassified, [{ form: 'N-CEN', count: 2, kind: null }]);
    // Total counts every filing handed in, so a form silently vanishing from
    // the classification cannot also vanish from the arithmetic.
    assert.equal(total, 3);
  });

  test('nothing in produces nothing out', () => {
    assert.deepEqual(summariseForms([]).rows, []);
    assert.deepEqual(summariseForms().rows, []);
  });
});
