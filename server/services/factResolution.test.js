import test from 'node:test';
import assert from 'node:assert/strict';
import { STATE, resolveConcept, resolveConcepts, searchableDefinitions, tally } from './factResolution.js';

/**
 * Pages verbatim from Reliance Industries' Integrated Annual Report 2025-26,
 * shortened to the lines under test.
 */
const CONSOLIDATED_CASHFLOW = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 202 203 ( I in crore) 2025-26 2024-25 A. Cash Flow from Operating Activities Net Cash Flow from Operating Activities * 1,92,113 1,78,703 B. Cash Flow from Investing Activities Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets (1,22,916) (1,39,967) Proceeds';
const CONSOLIDATED_BALANCE = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 196 197 ( I in crore) Notes As at 31 st March, 2026 As at 31 st March, 2025 Balance Sheet Assets Inventories 7 1,66,941 1,46,062 Cash and Cash Equivalents 10 1,45,977 1,06,502 Equity and Liabilities Total Equity 10,85,866 10,09,626';
const PAGES = [CONSOLIDATED_CASHFLOW, CONSOLIDATED_BALANCE];
const document = PAGES.join('\n');

const ask = (over) => ({
  pages: PAGES, document, company: 'RELIANCE', reportedInDocument: 'RIL FY2025-26',
  period_end: '2026-03-31', currency: 'INR', unit: 10000000, facts: [], ...over,
});

test('a missing input is searched for before the filing is called silent', () => {
  // The failure this replaces: "operating_cash_flow not reported", said about
  // a filing that reports 1,92,113 crore of it on page 103.
  const result = resolveConcept(ask({ concept: 'cfo', purpose: 'cash_basis' }));
  assert.equal(result.state, STATE.RECOVERED_FROM_DOCUMENT);
  assert.equal(result.selection.chosen.value, 192113);
  assert.equal(result.selection.chosen.source_page, 1);
});

test('what is already held is not searched for again', () => {
  const held = [{
    company: 'RELIANCE', period_end: '2026-03-31', period_type: 'annual',
    accounting_scope: 'consolidated', entity_scope: 'group', concept: 'cfo',
    definition_id: 'CFO.STATEMENT', measurement_basis: 'cash', segment: null,
    currency: 'INR', unit: 10000000, value: 192113, verdict: 'stated',
    reported_in_document: 'RIL FY2025-26', source_sentence: 'x',
  }];
  const result = resolveConcept(ask({ concept: 'cfo', purpose: 'cash_basis', facts: held }));
  assert.equal(result.state, STATE.FOUND_IN_STORE);
  assert.deepEqual(result.searched, []);
  assert.deepEqual(result.recovered, []);
});

test('nothing known to look for is not the same as nothing disclosed', () => {
  // Reliance reports a segment result before interest and taxes of 1,39,828
  // crore. Saying the report is silent about EBIT because nothing searches for
  // it would be the old error wearing a better word.
  const result = resolveConcept(ask({ concept: 'ebit', purpose: 'as_management_reports' }));
  assert.equal(result.state, STATE.NO_WAY_TO_LOOK);
  assert.match(result.reason, /nothing knows where ebit is found/);
  assert.deepEqual(searchableDefinitions('ebit'), []);
});

test('a concept searched for and absent from these pages is not disclosed in them', () => {
  // EBITDA is looked for in a ten-year highlights table. These pages have
  // none, so the answer is that it was searched for and not found - not that
  // nothing knows where to look.
  const result = resolveConcept(ask({ concept: 'ebitda', purpose: 'as_management_reports' }));
  assert.equal(result.state, STATE.NOT_DISCLOSED);
  assert.deepEqual(result.searched, ['EBITDA.BEFORE_EXCEPTIONAL']);
});

test('a search that ran and found nothing is what licenses "not disclosed"', () => {
  // CONSTRUCTED: the cash flow page alone, asked for a balance sheet figure.
  const result = resolveConcept(ask({ concept: 'equity', purpose: 'statutory_basis', pages: [CONSOLIDATED_CASHFLOW] }));
  assert.equal(result.state, STATE.NOT_DISCLOSED);
  assert.deepEqual(result.searched, ['EQUITY.TOTAL']);
  assert.match(result.reason, /1 place in the filing were searched|searched and none disclosed/);
});

test('where a figure came from and whether it can be used are separate answers', () => {
  // The mistake an earlier version of this made. Operating cash flow is found
  // on page 103 and is still no use to a reader who asked for a statutory
  // basis, because it is a cash measurement. Reporting that as "not found"
  // would be false, and reporting it as usable would be worse.
  const cash = resolveConcept(ask({ concept: 'cfo', purpose: 'cash_basis' }));
  const statutory = resolveConcept(ask({ concept: 'cfo', purpose: 'statutory_basis' }));
  assert.equal(cash.state, statutory.state);
  // Usable: one observation, on a basis the purpose admits.
  assert.equal(cash.selection.status, 'only_one_observation');
  assert.equal(cash.selection.chosen.value, 192113);
  // Same figure, same provenance, no use for this question.
  assert.equal(statutory.selection.status, 'no_fit');
  assert.equal(statutory.selection.chosen, null);
});

test('a concept with one definition never reports needing a definition', () => {
  // CFO has exactly one. An earlier version returned needs_a_definition for
  // it, which cannot be true of a concept that has only one.
  const result = resolveConcept(ask({ concept: 'cfo', purpose: 'statutory_basis' }));
  assert.notEqual(result.selection.status, 'needs_a_definition');
});

test('the comparative year is kept, not thrown away and searched for again', () => {
  const result = resolveConcept(ask({ concept: 'cfo', purpose: 'cash_basis' }));
  assert.deepEqual(result.recovered.map((fact) => [fact.period_end, fact.value]),
    [['2026-03-31', 192113], ['2025-03-31', 178703]]);
});

test('a document is searched once for a definition however many concepts want it', () => {
  const { resolutions, recovered, facts } = resolveConcepts(ask({
    concepts: ['cfo', 'capex', 'cash', 'equity'], purpose: 'cash_basis',
  }));
  assert.equal(resolutions.get('cash').selection.chosen.value, 145977);
  assert.equal(resolutions.get('equity').selection.chosen.value, 1085866);
  // Every recovered fact appears once.
  const keys = recovered.map((fact) => `${fact.definition_id}|${fact.period_end}`);
  assert.equal(new Set(keys).size, keys.length);
  assert.equal(facts.length, recovered.length);
});

test('resolving writes nothing; the facts it found are handed back', () => {
  const facts = [];
  const result = resolveConcept(ask({ concept: 'cfo', purpose: 'cash_basis', facts }));
  assert.deepEqual(facts, []);
  assert.ok(result.recovered.length > 0);
});

test('a tally counts every state, including the ones at zero', () => {
  const { resolutions } = resolveConcepts(ask({ concepts: ['cfo', 'ebit'], purpose: 'cash_basis' }));
  const counted = tally(resolutions);
  assert.equal(counted[STATE.RECOVERED_FROM_DOCUMENT], 1);
  assert.equal(counted[STATE.NO_WAY_TO_LOOK], 1);
  assert.equal(counted[STATE.NOT_DISCLOSED], 0);
  assert.deepEqual(Object.keys(counted).sort(), Object.values(STATE).sort());
});

test('a year already held is not handed back as newly recovered', () => {
  // The store has FY2026 operating cash flow and the question asks for FY2025.
  // The page carries both, so the search returns both - and handing back the
  // year already stored would have a caller write it a second time.
  const held = [{
    company: 'RELIANCE', period_end: '2026-03-31', period_type: 'annual',
    accounting_scope: 'consolidated', entity_scope: 'group', concept: 'cfo',
    definition_id: 'CFO.STATEMENT', measurement_basis: 'cash', segment: null,
    currency: 'INR', unit: 10000000, value: 192113, verdict: 'stated',
    reported_in_document: 'RIL FY2025-26', source_sentence: 'x',
  }];
  const { recovered } = resolveConcepts(ask({
    concepts: ['cfo'], purpose: 'cash_basis', period_end: '2025-03-31', facts: held,
  }));
  assert.deepEqual(recovered.map((fact) => [fact.period_end, fact.value]), [['2025-03-31', 178703]]);
});

test('a figure lands on the year-end the document states', () => {
  // CONSTRUCTED: a December filer. A search that assumed 31 March would put
  // its operating cash flow under a period it does not report.
  const december = 'Consolidated Financial Statements Company 1 2 ( in millions) 2025-26 2024-25 A. Cash Flow from Operating Activities Net Cash Flow from Operating Activities 5,000 4,000 B. Cash Flow';
  const result = resolveConcept(ask({
    concept: 'cfo', purpose: 'cash_basis', pages: [december], document: december,
    period_end: '2026-12-31', month_end: '12-31',
  }));
  assert.equal(result.state, STATE.RECOVERED_FROM_DOCUMENT);
  assert.equal(result.selection.chosen.period_end, '2026-12-31');
});
