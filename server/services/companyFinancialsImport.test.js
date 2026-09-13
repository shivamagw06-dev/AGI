import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readPeriod, readFinancials, scaleOf } from './companyFinancialsImport.js';

const good = {
  ticker: 'acme', period_end: '2026-03-31', period_type: 'annual',
  basis: 'consolidated', currency: 'inr', scale: 'crore',
  revenue: '11,400', ebitda: '2,280', capex: '(780)', cash: '1200',
};

describe('reading a row of statements', () => {
  test('a complete row reads back as reported', () => {
    const { row, errors } = readPeriod(good);
    assert.equal(errors, undefined);
    assert.equal(row.ticker, 'ACME');
    assert.equal(row.currency, 'INR');
    assert.equal(row.scale, 1e7);
    assert.equal(row.revenue, 11400);
    // Accounting parentheses are a minus sign, not decoration.
    assert.equal(row.capex, -780);
  });

  test('a blank is not reported, which is not the same as zero', () => {
    // A zero receivables balance is a fact; a blank one is an absence, and a
    // ratio built on the first is real while one built on the second is not.
    const { row } = readPeriod({ ...good, receivables: '', inventories: '-', payables: 'n/a', cost_of_sales: '0' });
    assert.equal(row.receivables, null);
    assert.equal(row.inventories, null);
    assert.equal(row.payables, null);
    assert.equal(row.cost_of_sales, 0);
  });

  test('a scale is never defaulted', () => {
    // "Revenue 11,400" is eleven thousand four hundred crore or eleven
    // thousand four hundred rupees, and the two differ by ten million.
    const { errors } = readPeriod({ ...good, scale: '' });
    assert.ok(errors.some((why) => /scale is missing/.test(why)), errors.join('; '));
  });

  test('scales are read as words or as numbers', () => {
    for (const [written, want] of [['crore', 1e7], ['CRORE', 1e7], ['lakh', 1e5],
      ['million', 1e6], ['mn', 1e6], ['1000', 1e3], ['1', 1], ['bn', 1e9]]) {
      assert.equal(scaleOf(written), want, written);
    }
    for (const bad of ['', null, undefined, 'zillion', '0', '-1']) {
      assert.equal(scaleOf(bad), null, String(bad));
    }
  });

  test('currency, period type and basis are rejected rather than assumed', () => {
    const checks = [
      [{ currency: 'rupees' }, /three-letter code/],
      [{ period_type: 'yearly' }, /annual or quarter/],
      [{ basis: 'group' }, /consolidated or standalone/],
      [{ period_end: '31-03-2026' }, /YYYY-MM-DD/],
      [{ ticker: '' }, /ticker is missing/],
    ];
    for (const [override, expected] of checks) {
      const { errors } = readPeriod({ ...good, ...override });
      assert.ok(errors && errors.some((why) => expected.test(why)),
        `${JSON.stringify(override)} -> ${errors ? errors.join('; ') : 'accepted'}`);
    }
  });

  test('basis defaults to consolidated because that is the reported default', () => {
    // The one default, and it is the statement most filers lead with. Every
    // other field says what it is or the row does not load.
    const { row } = readPeriod({ ...good, basis: undefined });
    assert.equal(row.basis, 'consolidated');
  });

  test('a row with no line items at all is not a period', () => {
    const { errors } = readPeriod({
      ticker: 'ACME', period_end: '2026-03-31', period_type: 'annual',
      currency: 'INR', scale: 'crore',
    });
    assert.ok(errors.some((why) => /no line items/.test(why)), errors.join('; '));
  });

  test('an error names the row it came from', () => {
    const { errors } = readPeriod({ ...good, currency: '' }, { at: 41 });
    assert.match(errors[0], /^row 42:/);
  });
});

describe('reading a whole file', () => {
  test('every problem is reported at once, not one per attempt', () => {
    const { rows, errors } = readFinancials([
      good,
      { ...good, period_end: '2025-03-31', currency: '' },
      { ...good, period_end: '2024-03-31', scale: '' },
    ]);
    assert.equal(rows.length, 1);
    assert.equal(errors.length, 2);
  });

  test('the same period twice is an error, not last-one-wins', () => {
    // The file cannot say which reading of a year was meant, and picking one
    // silently is how a restated year replaces an as-reported one.
    const { rows, errors } = readFinancials([good, { ...good, revenue: '99,999' }]);
    assert.equal(rows.length, 1);
    assert.match(errors[0], /also appears at row 1/);
  });

  test('the same year on a different basis is two periods, not a duplicate', () => {
    const { rows, errors } = readFinancials([good, { ...good, basis: 'standalone' }]);
    assert.deepEqual(errors, []);
    assert.equal(rows.length, 2);
  });

  test('an empty file is empty rather than an error', () => {
    for (const empty of [[], null, undefined]) {
      assert.deepEqual(readFinancials(empty), { rows: [], errors: [] });
    }
  });
});
