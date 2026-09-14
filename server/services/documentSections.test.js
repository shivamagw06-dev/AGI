import test from 'node:test';
import assert from 'node:assert/strict';
import { columnPlan, columnYears, mapSections, pagesFor, sectionOf } from './documentSections.js';

/**
 * Page headers verbatim from Reliance Industries' Integrated Annual Report
 * 2025-26, as the PDF flattens them.
 */
const STANDALONE_CASHFLOW = 'Reliance Industries Limited Integrated Annual Report 2025-26 118 119 Standalone Financial Statements ( H in crore) 2025-26 2024-25 A. Cash Flow from Operating Activities';
const CONSOLIDATED_CASHFLOW = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 202 203 ( I in crore) 2025-26 2024-25 A. Cash Flow from Operating Activities';
const CONSOLIDATED_BALANCE = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 196 197 ( I in crore) Notes As at 31 st March, 2026 As at 31 st March, 2025 Assets Non-Current Assets';
const MDA = 'Reliance Industries Limited   Integrated Annual Report 2025-26 6   7 Management Discussion and Analysis  Financial Performance and Review';

test('the running header says which statements a page belongs to', () => {
  // Reliance states operating cash flow twice under the same words: 79,059
  // crore standalone and 1,92,113 consolidated. Scope is the difference
  // between them and it is printed at the top of every page.
  assert.deepEqual(sectionOf(STANDALONE_CASHFLOW), { scope: 'standalone', kind: 'statements' });
  assert.deepEqual(sectionOf(CONSOLIDATED_CASHFLOW), { scope: 'consolidated', kind: 'statements' });
  assert.deepEqual(sectionOf(MDA), { scope: null, kind: 'mda' });
});

test('a header naming two sections resolves to the one it leads with', () => {
  const both = 'Consolidated Financial Statements Reliance Industries Limited 200 201 Standalone Financial Statements';
  assert.equal(sectionOf(both).scope, 'consolidated');
});

test('a cross-reference deep in a page is not where the page is', () => {
  const body = `${MDA} ... refer to the Consolidated Financial Statements for details`;
  assert.equal(sectionOf(body).kind, 'mda');
});

test('a statement page declares its own column years', () => {
  assert.deepEqual(columnYears(CONSOLIDATED_CASHFLOW), [2026, 2025]);
});

test('the running title is not a column', () => {
  // "Integrated Annual Report 2025-26" carries a year, and counting it adds a
  // column the page does not have.
  assert.equal(columnPlan(CONSOLIDATED_CASHFLOW).years.length, 2);
  assert.equal(columnPlan(CONSOLIDATED_CASHFLOW).cells, 2);
});

test('a balance sheet dates its columns differently and adds a note column', () => {
  // "Notes  As at 31st March, 2026  As at 31st March, 2025" is three columns,
  // the first of which is a reference and not a figure. A reader that knows
  // only the "2025-26" form finds one year here and skips every row.
  const plan = columnPlan(CONSOLIDATED_BALANCE);
  assert.deepEqual(plan.years, [2026, 2025]);
  assert.equal(plan.notes, true);
  assert.equal(plan.cells, 3);
});

test('pages are selected by scope and kind together', () => {
  const sections = mapSections([MDA, STANDALONE_CASHFLOW, CONSOLIDATED_CASHFLOW, CONSOLIDATED_BALANCE]);
  assert.deepEqual(pagesFor(sections, { accounting_scope: 'consolidated', kind: 'statements' })
    .map((entry) => entry.page), [3, 4]);
  assert.deepEqual(pagesFor(sections, { accounting_scope: 'standalone' }).map((entry) => entry.page), [2]);
  assert.deepEqual(pagesFor(sections, { kind: 'mda' }).map((entry) => entry.page), [1]);
});

test('a page with no header the reader knows belongs nowhere', () => {
  assert.deepEqual(sectionOf('some continuation of a table with no title'), { scope: null, kind: null });
  assert.deepEqual(columnPlan('').years, []);
});

test('a title year the columns do not share is still not a column', () => {
  // CONSTRUCTED: a report whose running title names a year outside its own
  // columns. Reliance's title year happens to equal its first column, so the
  // duplicate is absorbed - but counting the title adds a third column here,
  // and then every two-figure row on the page is refused as malformed.
  const header = 'Consolidated Financial Statements Integrated Annual Report 2026-27 ( I in crore) 2025-26 2024-25 A. Cash Flow';
  const plan = columnPlan(header);
  assert.deepEqual(plan.years, [2026, 2025]);
  assert.equal(plan.cells, 2);
});
