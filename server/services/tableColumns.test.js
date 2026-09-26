import test from 'node:test';
import assert from 'node:assert/strict';
import { alignRow, cellEndingIn, headerColumns, rowCells, splitRows } from './tableColumns.js';

/**
 * Rows are verbatim from the 10-Year Financial Highlights table in Reliance
 * Industries' Integrated Annual Report 2025-26, as the PDF flattens them.
 */
const HEADER = 'US$ Million FY 2025-26 FY 2024-25 FY 2023-24 FY 2022-23 *** FY 2021-22 FY 2020-21 FY 2019-20 FY 2018-19 FY 2017-18 FY 2016-17';
const REVENUE = 'Value of Sales and Services (Revenue)  123,996   11,75,919   10,71,174   10,00,122   9,74,864   7,88,743   5,39,238   6,59,997   6,25,212   4,30,731   3,30,180';
const EXCEPTIONAL = 'Exceptional Items Gain/(Loss)   -   -   -   -   -   2,836   5,642   (4,444)   -   1,087   -';
const DIVIDEND = 'Equity Dividend (%) ##   -   110   100   90   80   70   65   65   60   110   -';
const DEPRECIATION = 'Depreciation and Amortisation   6,083   57,688   53,136   50,832   40,303   29,782   26,572   22,203   20,934   16,706   11,646';
const EBITDA = 'Earnings Before Depreciation, Finance Cost and Tax Expenses (EBITDA) #  21,923   2,07,911   1,83,422   1,78,290   1,53,920   1,23,684   97,580   1,02,280   92,656   74,184   55,529';

test('a footnote marker in a header is not a column', () => {
  const columns = headerColumns(HEADER);
  assert.equal(columns.length, 11);
  assert.deepEqual(columns.slice(0, 3).map((column) => column.label),
    ['US$ Million', 'FY 2025-26', 'FY 2024-25']);
});

test('the first column is returned, not quietly dropped', () => {
  // It is dollars where the rest are crore. A reader that never sees it cannot
  // decide to skip it, and one that mistakes it for a year reads 1,23,996
  // crore of revenue that does not exist.
  const [first] = headerColumns(HEADER);
  assert.equal(first.label, 'US$ Million');
  assert.equal(first.ends_in, null);
});

test('a fiscal year ends in the later of the two years it names', () => {
  const columns = headerColumns(HEADER);
  assert.equal(columns.find((column) => column.label === 'FY 2025-26').ends_in, 2026);
  assert.equal(columns.find((column) => column.label === 'FY 2021-22').ends_in, 2022);
});

test('a figure is read by position, not by being somewhere in the line', () => {
  const aligned = alignRow(HEADER, REVENUE);
  assert.equal(aligned.problem, null);
  assert.equal(aligned.label, 'Value of Sales and Services (Revenue)');
  assert.equal(cellEndingIn(aligned, 2026).value, 1175919);
  assert.equal(cellEndingIn(aligned, 2022).value, 788743);
  // 7,88,743 is in the line whichever year it is claimed for. Position is what
  // makes the year a reading rather than an assertion.
  assert.equal(cellEndingIn(aligned, 2023).value, 974864);
});

test('a dash holds its column', () => {
  // Reliance reports no exceptional items for four years and 2,836 crore in
  // FY 2021-22. Skipping the dashes would shift that figure four years later.
  const aligned = alignRow(HEADER, EXCEPTIONAL);
  assert.equal(aligned.problem, null);
  assert.equal(cellEndingIn(aligned, 2026).value, null);
  assert.equal(cellEndingIn(aligned, 2022).value, 2836);
  assert.equal(cellEndingIn(aligned, 2021).value, 5642);
});

test('accounting parentheses are a minus sign', () => {
  assert.equal(cellEndingIn(alignRow(HEADER, EXCEPTIONAL), 2020).value, -4444);
});

test('dashes at both ends still hold their columns', () => {
  const aligned = alignRow(HEADER, DIVIDEND);
  assert.equal(aligned.problem, null);
  assert.equal(cellEndingIn(aligned, 2026).value, 110);
  assert.equal(cellEndingIn(aligned, 2017).value, null);
});

test('a row with the wrong number of cells is refused, not stretched', () => {
  // The guard that matters. Ten figures against eleven columns shifts every
  // one of them by a year and produces a table that reads perfectly.
  const short = 'Value of Sales and Services (Revenue)  11,75,919   10,71,174   10,00,122   9,74,864   7,88,743   5,39,238   6,59,997   6,25,212   4,30,731   3,30,180';
  const aligned = alignRow(HEADER, short);
  assert.deepEqual(aligned.cells, []);
  assert.equal(aligned.problem, 'the row has 10 cells and the header has 11 columns');
  assert.equal(cellEndingIn(aligned, 2026), null);
});

test('a slice holding two rows is refused, not resolved to one of them', () => {
  // The bug this replaces: taking the last run of figures returned the
  // exceptional items row for a slice that began at depreciation - eleven
  // cells against eleven columns, aligned perfectly, every figure a line item
  // and a year away from what it claimed to be.
  const two = `${DEPRECIATION}  ${EXCEPTIONAL}`;
  const { cells, problem } = rowCells(two);
  assert.deepEqual(cells, []);
  assert.equal(problem, 'the text holds 2 runs of figures, so more than one row');
  assert.equal(alignRow(HEADER, two).problem, problem);
});

test('a comma in a label is not a cell', () => {
  // A pattern of [digits and commas] matches a lone comma, which split
  // "Earnings Before Depreciation, Finance Cost and Tax Expenses" into two
  // rows and lost the EBITDA line entirely.
  const rows = splitRows(EBITDA);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].label, 'Earnings Before Depreciation, Finance Cost and Tax Expenses (EBITDA) #');
  assert.equal(cellEndingIn(alignRow(HEADER, EBITDA), 2022).value, 123684);
});

test('a region splits into every row it holds, including unwanted ones', () => {
  // Slicing from one wanted label to the next skips the rows between them and
  // takes their figures.
  const rows = splitRows(`${DEPRECIATION}  ${EXCEPTIONAL}  ${DIVIDEND}`);
  assert.deepEqual(rows.map((row) => row.label), [
    'Depreciation and Amortisation', 'Exceptional Items Gain/(Loss)', 'Equity Dividend (%) ##',
  ]);
  assert.equal(rows[0].cells[1], 57688);
  assert.equal(rows[1].cells[5], 2836);
});

test('a header with no years declares no columns', () => {
  assert.deepEqual(headerColumns('Particulars Standalone Consolidated'), []);
  assert.equal(alignRow('Particulars Standalone Consolidated', REVENUE).problem,
    'the header declares no columns');
});
