import test from 'node:test';
import assert from 'node:assert/strict';
import { CASH_FLOW_HEADERS, parseCashFlowTables } from './manualCashFlowScreener.js';

const header = CASH_FLOW_HEADERS.join('\t');
const cells = ['Example Ltd', '', '500001', 'EXAMPLE', 'INE123A01011', 'Industrial', 'Industrials', '100', '1000', '0', '-2.5', '3', '4', '5', '6', 'Industrials', 'Industrial'];
const parse = (row) => parseCashFlowTables([`${header}\n${row.join('\t')}`]);

test('preserves zero, negative values and annual order for BSE-only rows', () => {
  const [row] = parse(cells);
  assert.deepEqual(row.fcf, [0, -2.5, 3, 4, 5, 6]);
  assert.equal(row.nseCode, '');
  assert.equal(row.industryCopy, undefined);
});

test('rejects missing cash flow and conflicting repeated classifications', () => {
  const missing = [...cells]; missing[10] = '';
  assert.throws(() => parse(missing), /required/);
  const conflict = [...cells]; conflict[15] = 'Other';
  assert.throws(() => parse(conflict), /disagree/);
});

test('rejects duplicate securities and shifted column headers', () => {
  assert.throws(() => parseCashFlowTables([`${header}\n${cells.join('\t')}\n${cells.join('\t')}`]), /Duplicate ISIN/);
  assert.throws(() => parseCashFlowTables([`${header.replace('Free Cash Flow Annual Cr', 'Wrong')}\n${cells.join('\t')}`]), /17-column header/);
});
