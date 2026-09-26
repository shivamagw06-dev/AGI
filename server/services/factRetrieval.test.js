import test from 'node:test';
import assert from 'node:assert/strict';
import { readFacts } from './factExtraction.js';
import { TARGETS, figuresOf, findCandidates, localPlan, recover } from './factRetrieval.js';

/**
 * Pages verbatim from Reliance Industries' Integrated Annual Report 2025-26,
 * shortened to the lines under test. The two cash flow pages are the point of
 * the file: the same words, two scopes, and figures that differ by more than
 * half.
 */
const STANDALONE_CASHFLOW = 'Reliance Industries Limited Integrated Annual Report 2025-26 118 119 Standalone Financial Statements ( H in crore) 2025-26 2024-25 A. Cash Flow from Operating Activities Net Cash Flow from Operating Activities* 79,059 79,392 B. Cash Flow from Investing Activities';
const CONSOLIDATED_CASHFLOW = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 202 203 ( I in crore) 2025-26 2024-25 A. Cash Flow from Operating Activities Net Cash Flow from Operating Activities * 1,92,113 1,78,703 B. Cash Flow from Investing Activities Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets (1,22,916) (1,39,967) Proceeds from disposal';
const CONSOLIDATED_BALANCE = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 196 197 ( I in crore) Notes As at 31 st March, 2026 As at 31 st March, 2025 Balance Sheet Assets Inventories 7 1,66,941 1,46,062 Trade Receivables 9 58,491 42,121 Equity and Liabilities Total Equity 10,85,866 10,09,626 Trade Payables 21 1,58,842 1,86,789 Total Equity and Liabilities 21,78,140 19,50,121';

const PAGES = [STANDALONE_CASHFLOW, CONSOLIDATED_CASHFLOW, CONSOLIDATED_BALANCE];
const document = PAGES.join('\n');
const money = { currency: 'INR', unit: 10000000 };

test('the scope asked for is the scope searched', () => {
  // The failure this prevents: a search for the label alone finds the
  // standalone figure first, writes 79,059 where 1,92,113 belongs, and the
  // citation checks out perfectly.
  const group = findCandidates({ pages: PAGES, definition_id: 'CFO.STATEMENT', accounting_scope: 'consolidated', ...money });
  const company = findCandidates({ pages: PAGES, definition_id: 'CFO.STATEMENT', accounting_scope: 'standalone', ...money });
  assert.equal(group.candidates.find((one) => one.period_end === '2026-03-31').value, 192113);
  assert.equal(company.candidates.find((one) => one.period_end === '2026-03-31').value, 79059);
  assert.equal(group.candidates[0].source_page, 2);
  assert.equal(company.candidates[0].source_page, 1);
});

test('both years on the page are read, from its own header', () => {
  const { candidates } = findCandidates({ pages: PAGES, definition_id: 'CFO.STATEMENT', accounting_scope: 'consolidated', ...money });
  assert.deepEqual(candidates.map((one) => [one.period_end, one.value]),
    [['2026-03-31', 192113], ['2025-03-31', 178703]]);
});

test('an outflow is stored as a magnitude', () => {
  // A cash flow statement writes capital expenditure in brackets. The store
  // holds 1,22,916 whichever side of the statement it sits on.
  const { candidates } = findCandidates({ pages: PAGES, definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', accounting_scope: 'consolidated', ...money });
  assert.equal(candidates[0].value, 122916);
});

test('a note reference is not a figure', () => {
  // "Trade Receivables 9 58,491 42,121". Reading the 9 as a figure puts every
  // column a place out.
  const { candidates } = findCandidates({ pages: PAGES, definition_id: 'RECEIVABLES.TRADE', accounting_scope: 'consolidated', ...money });
  assert.equal(candidates.find((one) => one.period_end === '2026-03-31').value, 58491);
});

test('a row without a note reference on a page that has them is still read', () => {
  // "Total Equity 10,85,866 10,09,626" carries none. Requiring one refused the
  // totals, and a row on another page then matched the label and wrote a
  // figure from somewhere else entirely.
  const { candidates } = findCandidates({ pages: PAGES, definition_id: 'EQUITY.TOTAL', accounting_scope: 'consolidated', ...money });
  assert.equal(candidates.find((one) => one.period_end === '2026-03-31').value, 1085866);
});

test('figuresOf takes the years and refuses anything else', () => {
  assert.deepEqual(figuresOf({ cells: [58491, 42121] }, 2), [58491, 42121]);
  assert.deepEqual(figuresOf({ cells: [9, 58491, 42121] }, 2), [58491, 42121]);
  // A leading cell that looks like money is not a note reference.
  assert.equal(figuresOf({ cells: [58491, 42121, 1000] }, 2), null);
  assert.equal(figuresOf({ cells: [42121] }, 2), null);
});

test('a label that names two different things is kept apart by its statement', () => {
  // "Inventories" on the balance sheet is a balance of 1,66,941 crore. The
  // same word in the cash flow statement's working capital section is the
  // change in it, (15,709). The label cannot tell them apart and the search
  // reaches the cash flow page first.
  const cashflow = `${CONSOLIDATED_CASHFLOW} Adjusted for: Inventories (15,709) (4,116) Trade and Other Payables 69,234 30,536`;
  const { candidates } = findCandidates({
    pages: [cashflow, CONSOLIDATED_BALANCE], definition_id: 'INVENTORIES.TOTAL',
    accounting_scope: 'consolidated', ...money,
  });
  assert.equal(candidates.find((one) => one.period_end === '2026-03-31').value, 166941);
  assert.ok(candidates.every((one) => one.value !== 15709), 'read a working-capital change as a balance');
});

test('nothing is proposed for a definition with no target', () => {
  const result = findCandidates({ pages: PAGES, definition_id: 'CAPEX.MANAGEMENT', accounting_scope: 'consolidated', ...money });
  assert.deepEqual(result.candidates, []);
  assert.match(result.reason, /no retrieval target/);
});

test('what was searched for and not found is named', () => {
  const { missed } = recover({ pages: [STANDALONE_CASHFLOW], definition_ids: ['EQUITY.TOTAL'], accounting_scope: 'consolidated', ...money });
  assert.equal(missed[0].definition_id, 'EQUITY.TOTAL');
  assert.match(missed[0].reason, /no line matched/);
});

test('every candidate survives the citation check', () => {
  // Retrieval proposes; readFacts decides. A candidate whose value is not in
  // the line it cites, or whose line is not in the document, is refused here
  // exactly as a model's reading would be.
  const { candidates } = recover({ pages: PAGES, definition_ids: [...TARGETS.keys()], accounting_scope: 'consolidated', ...money });
  const { facts, rejected } = readFacts({ payload: { facts: candidates }, document, company: 'RELIANCE', reportedInDocument: 'RIL FY2025-26' });
  assert.equal(rejected.length, 0);
  assert.equal(facts.length, candidates.length);
  const now = facts.filter((fact) => fact.period_end === '2026-03-31');
  assert.deepEqual(
    now.map((fact) => [fact.definition_id, fact.value]).sort((a, b) => a[0].localeCompare(b[0])),
    [
      ['CAPEX.CASH_PPE_INTANGIBLES', 122916],
      ['CFO.STATEMENT', 192113],
      ['EQUITY.TOTAL', 1085866],
      ['INVENTORIES.TOTAL', 166941],
      ['PAYABLES.TRADE', 158842],
      ['RECEIVABLES.TRADE', 58491],
    ],
  );
});

// Verbatim from pages 125, 89 and 5 of the same report.
const CONSOLIDATED_GEARING = 'Consolidated Financial Statements Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 246 247 Notes To the Consolidated Financial Statements for the year ended 31st March, 2026 d) Leverage optimally in order to maximise shareholder returns. The Net Gearing Ratio at the end of the reporting period was as follows: ( I in crore) As at 31 st March, 2026 As at 31 st March, 2025 Gross Debt 3,74,421 3,47,530 Cash and Marketable Securities * 2,49,704 2,30,447 Net Debt (A) 1,24,717 1,17,083 Equity attributable to Owners of the Company (B) 9,04,030 8,43,200 Net Gearing Ratio (A/B) 0.14 0.14';
const STANDALONE_GEARING = 'Reliance Industries Limited Integrated Annual Report 2025-26 174 175 Standalone Financial Statements Notes To the Standalone Financial Statements for the year ended 31st March, 2026 The Net Gearing Ratio at the end of the reporting period was as follows: ( H in crore) Particulars As at 31 st March, 2026 As at 31 st March, 2025 Gross Debt 2,31,381 1,98,813 Cash and Marketable Securities* 1,58,719 1,39,573 Net debt (A) 72,662 59,240 Total Equity (As per Balance Sheet)';
const TEN_YEAR = 'Reliance Industries Limited Integrated Annual Report 2025-26 6 7 Management Discussion and Analysis Financial Performance and Review 10-Year Financial Highlights (Consolidated) ( C in Crore, unless otherwise stated) US$ Million FY 2025-26 FY 2024-25 FY 2023-24 FY 2022-23 *** FY 2021-22 FY 2020-21 FY 2019-20 FY 2018-19 FY 2017-18 FY 2016-17 Value of Sales and Services (Revenue) 123,996 11,75,919 10,71,174 10,00,122 9,74,864 7,88,743 5,39,238 6,59,997 6,25,212 4,30,731 3,30,180 Earnings Before Depreciation, Finance Cost and Tax Expenses (EBITDA) # 21,923 2,07,911 1,83,422 1,78,290 1,53,920 1,23,684 97,580 1,02,280 92,656 74,184 55,529 Depreciation and Amortisation 6,083 57,688';
const at2026 = (candidates) => candidates.find((one) => one.period_end === '2026-03-31');

test('a table with its own column header is read when the page has none', () => {
  // A notes page is headed with the note's title, not with years. The
  // capital management table brings its own - "As at 31st March, 2026 As at
  // 31st March, 2025" - immediately above "Gross Debt 3,74,421 3,47,530".
  const { candidates } = findCandidates({ pages: [CONSOLIDATED_GEARING], definition_id: 'DEBT.GROSS', accounting_scope: 'consolidated', ...money });
  assert.deepEqual(candidates.map((one) => [one.period_end, one.value]), [['2026-03-31', 374421], ['2025-03-31', 347530]]);
});

test('net debt is read from the same table, under its own definition', () => {
  const { candidates } = findCandidates({ pages: [CONSOLIDATED_GEARING], definition_id: 'DEBT.NET', accounting_scope: 'consolidated', ...money });
  assert.equal(at2026(candidates).value, 124717);
  assert.equal(at2026(candidates).as_reported_label, 'Net Debt (A)');
});

test('the group’s debt and the company’s are kept apart by scope', () => {
  // The same table appears twice: 3,74,421 for the group, 2,31,381 for the
  // company, under the same words.
  const pages = [STANDALONE_GEARING, CONSOLIDATED_GEARING];
  const group = findCandidates({ pages, definition_id: 'DEBT.GROSS', accounting_scope: 'consolidated', ...money });
  const company = findCandidates({ pages, definition_id: 'DEBT.GROSS', accounting_scope: 'standalone', ...money });
  assert.equal(at2026(group.candidates).value, 374421);
  assert.equal(at2026(company.candidates).value, 231381);
});

test('a label in a sentence does not stop the search reaching the table', () => {
  // CONSTRUCTED: "net debt" said in prose before it is tabulated. Stopping at
  // the first occurrence read the sentence, found no row, and missed the
  // table below it.
  const page = CONSOLIDATED_GEARING.replace('d) Leverage optimally', 'We reduced net debt during the year. d) Leverage optimally');
  const { candidates } = findCandidates({ pages: [page], definition_id: 'DEBT.NET', accounting_scope: 'consolidated', ...money });
  assert.equal(at2026(candidates).value, 124717);
});

test('a column header is not borrowed across a paragraph of prose', () => {
  // CONSTRUCTED: years stated, then a paragraph, then a row. A header that
  // far back belongs to something else, and taking it would file the row's
  // figures under columns that are not its own.
  const page = 'Consolidated Financial Statements Company 1 2 Notes ( I in crore) As at 31 st March, 2026 As at 31 st March, 2025 Revenue 10 20. The Company manages its capital prudently. It also borrows. Gross Debt 3,74,421 3,47,530';
  assert.deepEqual(localPlan(page.replace(/\s+/g, ' '), page.indexOf('Gross Debt')).years, []);
});

test('EBITDA is read from a table whose title carries the scope', () => {
  // The page is management discussion and declares no scope. The table's
  // title says "(Consolidated)", which is the only place the scope is stated.
  const { candidates } = findCandidates({ pages: [TEN_YEAR], definition_id: 'EBITDA.BEFORE_EXCEPTIONAL', accounting_scope: 'consolidated', ...money });
  assert.equal(at2026(candidates).value, 207911);
  assert.equal(candidates.find((one) => one.period_end === '2025-03-31').value, 183422);
  assert.equal(candidates.find((one) => one.period_end === '2022-03-31').value, 123684);
  assert.match(at2026(candidates).source_section, /\(Consolidated\)/);
});

test('a table titled for the other scope is skipped, not taken for want of anything better', () => {
  const { candidates, reason } = findCandidates({ pages: [TEN_YEAR], definition_id: 'EBITDA.BEFORE_EXCEPTIONAL', accounting_scope: 'standalone', ...money });
  assert.deepEqual(candidates, []);
  assert.match(reason, /no titled table/);
});

test('the dollar column of a titled table is not a year', () => {
  // "US$ Million" leads the header. 21,923 is dollars, and filed under a year
  // it would be the group's EBITDA understated tenfold.
  const { candidates } = findCandidates({ pages: [TEN_YEAR], definition_id: 'EBITDA.BEFORE_EXCEPTIONAL', accounting_scope: 'consolidated', ...money });
  assert.ok(candidates.every((one) => one.value !== 21923));
});
