import test from 'node:test';
import assert from 'node:assert/strict';
import { STATE } from './factResolution.js';
import {
  NEED_CONCEPTS, answersFromFacts, blockedBy, neededConcepts, periodEndsFor, periodFromResolutions,
} from './annualReportFromFacts.js';

/** Pages verbatim from Reliance Industries' Integrated Annual Report 2025-26. */
const CASHFLOW = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 202 203 ( I in crore) 2025-26 2024-25 A. Cash Flow from Operating Activities Net Cash Flow from Operating Activities * 1,92,113 1,78,703 B. Cash Flow from Investing Activities Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets (1,22,916) (1,39,967) Proceeds';
const PROFIT_LOSS = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 198 199 ( I in crore) Notes 2025-26 2024-25 Statement of Profit and Loss Revenue from Operations 25 10,75,675 9,80,136 Total Income 11,04,637 9,98,114 Finance Costs 27,061 24,269 Depreciation / Amortisation and Depletion Expense 57,688 53,136';
const PAGES = [CASHFLOW, PROFIT_LOSS];

const ask = (over) => ({
  periodEnds: ['2026-03-31', '2025-03-31'], facts: [], pages: PAGES,
  document: PAGES.join('\n'), company: 'RELIANCE', reportedInDocument: 'RIL FY2025-26',
  currency: 'INR', unit: 10000000, purpose: 'any_disclosed',
  prefer: { revenue: 'REVENUE.OPERATIONS_NET' }, ...over,
});

test('the questions name things the ontology names differently', () => {
  assert.equal(NEED_CONCEPTS.get('operating_cash_flow'), 'cfo');
  assert.equal(NEED_CONCEPTS.get('gross_debt'), 'debt');
  const concepts = neededConcepts();
  assert.ok(concepts.includes('cfo'), 'operating_cash_flow did not resolve to a concept');
  assert.ok(!concepts.includes('operating_cash_flow'), 'a question name leaked through as a concept');
});

test('a figure is written under every name a formula might ask for', () => {
  // One formula asks for operating_cash_flow and another for cfo. Both must
  // read the same resolved figure rather than one of them finding nothing.
  const resolutions = new Map([['cfo', {
    state: STATE.RECOVERED_FROM_DOCUMENT,
    selection: { status: 'only_one_observation', chosen: { value: 192113, definition_id: 'CFO.STATEMENT', source_page: 1 }, caveats: [] },
  }]]);
  const { period, provenance } = periodFromResolutions(resolutions, { period_end: '2026-03-31', currency: 'INR', unit: 10000000 });
  assert.equal(period.cfo, 192113);
  assert.equal(period.operating_cash_flow, 192113);
  assert.equal(provenance.cfo.definition_id, 'CFO.STATEMENT');
  assert.equal(provenance.cfo.source_page, 1);
});

test('an answer carries the definition and page behind every input', () => {
  // 0.4693 is worth little without knowing which capital expenditure is under
  // it, and the old shape had no room to say.
  const { answers } = answersFromFacts(ask({}));
  const fcf = answers.get(42);
  assert.equal(fcf.value, 69197);
  assert.equal(fcf.used.operating_cash_flow.definition_id, 'CFO.STATEMENT');
  assert.equal(fcf.used.capex.definition_id, 'CAPEX.CASH_PPE_INTANGIBLES');
  assert.equal(fcf.used.capex.source_page, 1);
  assert.equal(fcf.used.operating_cash_flow.state, STATE.RECOVERED_FROM_DOCUMENT);
});

test('a question is answered from the document with nothing in the store', () => {
  const { answers, recovered } = answersFromFacts(ask({}));
  assert.equal(answers.get(41).value, 192113);
  assert.equal(answers.get(72).value, 122916);
  assert.ok(recovered.length > 0, 'nothing was recovered');
});

test('growth reads the periods newest first', () => {
  // Assembled the other way round, every change is reported with its sign
  // reversed. Reliance grew revenue from 9,80,136 to 10,75,675.
  const { answers } = answersFromFacts(ask({}));
  assert.equal(Number(answers.get(11).value.toFixed(4)), 0.0975);
});

test('a blocked question says which input stopped it and what happened to it', () => {
  // "not reported", said about a filing that reports it, was the whole
  // complaint. EBIT is disclosed by Reliance and nothing knows where to look.
  const { answers } = answersFromFacts(ask({}));
  const margin = answers.get(24);
  assert.equal(margin.value, null);
  const [blocked] = margin.blocked_by.filter((one) => one.concept === 'ebit');
  assert.equal(blocked.state, STATE.NO_WAY_TO_LOOK);
  assert.match(blocked.reason, /nothing knows where ebit is found/);
});

test('a concept disclosed two ways blocks until the definition is named', () => {
  const named = answersFromFacts(ask({}));
  const unnamed = answersFromFacts(ask({ prefer: {} }));
  assert.equal(named.answers.get(11).value !== null, true);
  const [blocked] = unnamed.answers.get(11).blocked_by;
  assert.equal(blocked.concept, 'revenue');
  assert.equal(blocked.status, 'needs_a_definition');
  assert.deepEqual(blocked.candidates.sort(), ['REVENUE.OPERATIONS_NET', 'REVENUE.TOTAL_INCOME']);
});

test('blockedBy reports nothing for a question whose inputs all resolved', () => {
  const provenance = {
    cfo: { state: STATE.RECOVERED_FROM_DOCUMENT, status: 'only_one_observation' },
    capex: { state: STATE.FOUND_IN_STORE, status: 'selected' },
  };
  assert.deepEqual(blockedBy({ needs: ['operating_cash_flow', 'capex'] }, provenance), []);
});

test('an input never asked for is not reported as undisclosed', () => {
  assert.deepEqual(blockedBy({ needs: ['cost_of_capital'] }, {}),
    [{ need: 'cost_of_capital', concept: 'cost_of_capital', state: 'not_asked_for' }]);
});

test('the provenance on an answer is the current year’s, not the comparative’s', () => {
  // computedAnswers sorts the periods itself, so the order here decides only
  // which year's provenance decorates the answers - and an answer about
  // FY2026 labelled with where FY2025 was found is a quiet kind of wrong.
  // The two years are made to differ: FY2025 is already stored, FY2026 is not.
  const stored = [{
    company: 'RELIANCE', period_end: '2025-03-31', period_type: 'annual',
    accounting_scope: 'consolidated', entity_scope: 'group', concept: 'cfo',
    definition_id: 'CFO.STATEMENT', measurement_basis: 'cash', segment: null,
    currency: 'INR', unit: 10000000, value: 178703, verdict: 'stated',
    reported_in_document: 'RIL FY2024-25', source_sentence: 'x',
  }];
  const { answers } = answersFromFacts(ask({ facts: stored }));
  assert.equal(answers.get(41).value, 192113);
  assert.equal(answers.get(41).used.operating_cash_flow.state, STATE.RECOVERED_FROM_DOCUMENT);
  assert.equal(answers.get(41).used.operating_cash_flow.source_page, 1);
});

test('periods are chosen newest first and bounded', () => {
  // A filing carries ten years in its highlights table. Resolving all of them
  // costs a search of the document per year for nothing a reader asked about,
  // and a question about growth wants this year and last.
  const held = ['2019-03-31', '2020-03-31', '2021-03-31', '2022-03-31',
    '2023-03-31', '2024-03-31', '2025-03-31'].map((period_end) => ({ period_end }));
  assert.deepEqual(periodEndsFor({ held, requested: ['2026-03-31'], limit: 3 }),
    ['2026-03-31', '2025-03-31', '2024-03-31']);
});

test('a period asked for is kept even when nothing is stored', () => {
  assert.deepEqual(periodEndsFor({ held: [], requested: ['2026-03-31'] }), ['2026-03-31']);
  assert.deepEqual(periodEndsFor({ held: [], requested: ['', '  '] }), []);
  assert.deepEqual(periodEndsFor(), []);
});

test('a period stored and asked for is not resolved twice', () => {
  const held = [{ period_end: '2026-03-31' }, { period_end: '2026-03-31' }];
  assert.deepEqual(periodEndsFor({ held, requested: ['2026-03-31'] }), ['2026-03-31']);
});

// Page 125 of the same report: the capital management note.
const GEARING = 'Consolidated Financial Statements Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 246 247 Notes To the Consolidated Financial Statements The Net Gearing Ratio at the end of the reporting period was as follows: ( I in crore) As at 31 st March, 2026 As at 31 st March, 2025 Gross Debt 3,74,421 3,47,530 Cash and Marketable Securities * 2,49,704 2,30,447 Net Debt (A) 1,24,717 1,17,083 Equity attributable to Owners of the Company (B) 9,04,030 8,43,200';
const BALANCE = 'Consolidated Financial Statements Reliance Industries Limited Integrated Annual Report 2025-26 196 197 ( I in crore) Notes As at 31 st March, 2026 As at 31 st March, 2025 Balance Sheet Assets Cash and Cash Equivalents 10 1,45,977 1,06,502';
const withDebt = (over = {}) => ask({
  pages: [...PAGES, GEARING, BALANCE], document: [...PAGES, GEARING, BALANCE].join('\n'), ...over,
});

test('gross debt is answered without asking which debt was meant', () => {
  // Reliance discloses gross and net debt. Resolved by concept, that is two
  // definitions and a question nobody asking for gross debt needs answered.
  const { answers } = answersFromFacts(withDebt());
  assert.equal(answers.get(61).value, 374421);
  assert.equal(answers.get(61).used.gross_debt.definition_id, 'DEBT.GROSS');
  assert.equal(answers.get(61).used.gross_debt.source_page, 3);
});

test('net debt is the filing’s, not a rebuild from the cash line', () => {
  const { answers } = answersFromFacts(withDebt());
  const net = answers.get(63);
  assert.equal(net.value, 124717);
  assert.equal(net.formula, 'net_debt (as stated)');
  // What the answer used is what it cites. The cash line was never used.
  assert.deepEqual(Object.keys(net.used), ['net_debt']);
  assert.equal(net.used.net_debt.definition_id, 'DEBT.NET');
});

test('an answered question carries nothing blocking it', () => {
  const { answers } = answersFromFacts(withDebt());
  assert.equal(answers.get(63).blocked_by, null);
});

test('net debt is never written under the gross debt name', () => {
  // CONSTRUCTED: a filing stating only net debt. By concept alone, the only
  // debt figure would have been taken as gross debt.
  const netOnly = GEARING.replace('Gross Debt 3,74,421 3,47,530 ', '');
  const { answers, periods } = answersFromFacts(ask({ pages: [...PAGES, netOnly], document: [...PAGES, netOnly].join('\n') }));
  assert.equal(periods[0].gross_debt, null);
  assert.equal(periods[0].net_debt, 124717);
  assert.equal(answers.get(61).value, null);
  const [blocked] = answers.get(61).blocked_by;
  assert.equal(blocked.state, STATE.NOT_DISCLOSED);
  assert.match(blocked.reason, /DEBT\.GROSS was not found, though debt was/);
});

test('a question answered without a need does not report it as blocking', () => {
  // Net debt is stated, so the answer never reaches for the cash line. With
  // no balance sheet page here, cash is undisclosed - and saying so on an
  // answered question describes a problem the answer does not have.
  const pages = [...PAGES, GEARING];
  const { answers } = answersFromFacts(ask({ pages, document: pages.join('\n') }));
  assert.equal(answers.get(63).value, 124717);
  assert.equal(answers.get(63).blocked_by, null);
});

test('a need that resolved is not listed among what blocked a question', () => {
  // Leverage needs debt and EBITDA. These pages hold the debt and no ten-year
  // table, so only EBITDA is missing - and a reader told gross debt was also
  // missing would go looking for a figure that is on page 3.
  const pages = [...PAGES, GEARING, BALANCE];
  const { answers } = answersFromFacts(ask({ pages, document: pages.join('\n') }));
  const leverage = answers.get(64);
  assert.equal(leverage.value, null);
  assert.deepEqual(leverage.blocked_by.map((one) => one.concept), ['ebitda']);
});
