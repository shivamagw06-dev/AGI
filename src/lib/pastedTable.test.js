import assert from 'node:assert/strict';
import test from 'node:test';

import { delimiterOf, parseDelimited, parsePaste } from './pastedTable.js';

// The real shape of the insider export: a post-transaction holding written as a
// quoted field with newlines and padding inside it.
const HOLDING = '"0\n                \n                \n                    (0%)"';
const HEADER = ['Stock', 'Client Name', 'Action*', 'Quantity',
  'Post Transaction Holding', 'Mode'];
const PANACEA = ['Panacea Biotec', 'Nosheen Sheikh', 'Disposal', '3000',
  HOLDING, 'Market Sale'];
const KDDL = ['KDDL', 'PRANAV SHANKAR SABOO', 'Disposal', '246000', '518511',
  'Market Sale'];

const block = (...rows) => [HEADER, ...rows].map((r) => r.join('\t')).join('\n') + '\n';

test('a trade spanning several lines stays one row', () => {
  // Splitting on newlines first cut this trade in two and turned its tail into
  // a phantom row whose first column was (0%)". That is the bug this guards.
  const rows = parsePaste(block(PANACEA, KDDL));
  assert.equal(rows.length, 3, 'header plus two trades');
  assert.ok(!rows.some((r) => String(r[0]).includes('(0%)')), 'no phantom row');
});

test('columns stay aligned when a field contains newlines', () => {
  // The damage from a torn row is not a missing row, it is every later column
  // shifting left, so a quantity is read out of the mode column.
  const rows = parsePaste(block(PANACEA));
  assert.deepEqual([...new Set(rows.map((r) => r.length))], [HEADER.length]);
  const panacea = rows[1];
  assert.equal(panacea[3], '3000');
  assert.equal(panacea[5], 'Market Sale');
});

test('the newlines inside the field are kept, not silently dropped', () => {
  const [, panacea] = parsePaste(block(PANACEA));
  assert.ok(panacea[4].includes('\n'), 'field keeps its own newlines');
  assert.ok(panacea[4].includes('(0%)'));
  assert.ok(!panacea[4].startsWith('"'), 'surrounding quotes are consumed');
});

test('a quoted comma does not split a company name', () => {
  const rows = parsePaste('Stock,Client\n"Tata Motors, Ltd",Someone\n');
  assert.deepEqual(rows[1], ['Tata Motors, Ltd', 'Someone']);
});

test('a doubled quote is one literal quote', () => {
  const rows = parsePaste('A\tB\n"x""y"\tplain\n');
  assert.equal(rows[1][0], 'x"y');
});

test('the delimiter comes from the header, not the whole block', () => {
  // A tab-separated block whose data holds more commas than the header does.
  assert.equal(delimiterOf('Stock\tClient'), '\t');
  assert.equal(delimiterOf('Stock,Client'), ',');
  assert.equal(delimiterOf('Stock;Client;Mode'), ';');
});

test('blank lines between rows are ignored, empty paste yields nothing', () => {
  assert.equal(parsePaste('').length, 0);
  assert.equal(parsePaste('   \n  \n').length, 0);
  assert.equal(parsePaste(block(KDDL) + '\n\n').length, 2);
});

test('carriage returns from a Windows clipboard do not enter the fields', () => {
  const rows = parseDelimited('A\tB\r\nx\ty\r\n', '\t');
  assert.deepEqual(rows[1], ['x', 'y']);
});
