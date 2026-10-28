import test from 'node:test';
import assert from 'node:assert/strict';
import { parseScreenerTable, parseScreenerTables, compareScreenerSnapshots, sortScreenerRows } from './screenerTable.js';
const header = 'Stock Name\tNSE Code\tISIN\tCurrent Price\tMarket Capitalization\tMarket Capitalization';
const first = 'Example, Ltd.\tEXAMPLE\tINE123A01011\t100\t1,234.50\t1234.5';
const second = 'Other Ltd.\tOTHER\tINE123A01012\t200\t2000\t2000';
test('preserves arbitrary fields and blanks, combines agreeing duplicate headers and prefers ISIN', () => {
  const parsed = parseScreenerTable(`${header}\r\n${first.replace('EXAMPLE','')}`);
  assert.equal(parsed.identityHeader, 'ISIN'); assert.equal(parsed.rowCount, 1); assert.equal(parsed.repeatedColumnsCollapsed, 1);
  assert.equal(parsed.rows[0][0], 'Example, Ltd.'); assert.equal(parsed.rows[0][1], ''); assert.equal(parsed.rows[0][4], '1,234.50');
});
test('supports quoted CSV with multiline text and a user-selected identity column', () => {
  const p = parseScreenerTable('Security,Notes,Code\n"Example, Ltd.","line 1\nline 2",A', 'Code');
  assert.equal(p.identityColumn, 2); assert.equal(p.rows[0][1], 'line 1\nline 2');
});
test('rejects duplicates, missing identities, bad ISINs, conflicting headers and malformed widths', () => {
  assert.throws(() => parseScreenerTable(`${header}\n${first}\n${first}`), /duplicate stock identifier/);
  assert.throws(() => parseScreenerTable(`${header}\n${first.replace('INE123A01011','')}`), /ISIN is missing/);
  assert.throws(() => parseScreenerTable(`${header}\n${first.replace('INE123A01011','BAD')}`), /invalid ISIN/);
  assert.throws(() => parseScreenerTable(`${header}\n${first.replace('1234.5','999')}`), /repeated Market Capitalization/);
  assert.throws(() => parseScreenerTable(`${header}\n${first}\textra`), /expected 6 columns/);
  assert.throws(() => parseScreenerTable('Metric\tValue\nPE\t10'), /Choose a unique/);
  assert.throws(() => parseScreenerTable('Stock\t\nX\t1'), /non-empty column headers/);
  assert.throws(() => parseScreenerTable('Stock,Symbol\n"Example,A'), /unclosed quoted field/);
});
test('merges two reordered parts without shifting values and rejects repeated identities across parts', () => {
  const a = 'Stock\tSymbol\tPrice\nOne\tA\t10', b = 'Price\tSymbol\tStock\n20\tB\tTwo';
  assert.deepEqual(parseScreenerTables([a,b]).rows, [['One','A','10'], ['Two','B','20']]);
  assert.throws(() => parseScreenerTables([a,a]), /across the two table parts/);
  assert.throws(() => parseScreenerTables([a,'Stock\tSymbol\tPE\nTwo\tB\t5']), /same column headers/);
});
test('tracks entries and exits by identifiers and refuses incomparable identity changes', () => {
  const p = { id: 1, as_of: '2026-10-27', columns: ['Stock','Symbol','Price'], identity_column: 1, rows: [['One','A','10'],['Two','B','20']] };
  const n = { ...p, id:2, as_of:'2026-10-28', rows:[['Renamed Two','B','21'],['Three','C','30']] };
  const changes = compareScreenerSnapshots(n,p);
  assert.equal(changes.addedCount,1); assert.equal(changes.removedCount,1); assert.equal(changes.retainedCount,1);
  assert.equal(changes.added[0].identifier,'C'); assert.equal(changes.removed[0].identifier,'A');
  assert.equal(compareScreenerSnapshots(n,null).available,false);
  assert.equal(compareScreenerSnapshots({...n,identity_column:0},p).available,false);
});
test('sorts formatted numeric columns numerically without mutating snapshot data', () => {
  const rows = [['A','₹1,000'],['B','90'],['C','12.5%']];
  assert.deepEqual(sortScreenerRows(rows,1).map(r=>r[0]), ['C','B','A']); assert.equal(rows[0][0],'A');
});
