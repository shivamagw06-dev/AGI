import test from 'node:test';
import assert from 'node:assert/strict';
import {
  RECIPES, calculate, calculateAll, isStale, lineage, propagatedSlack, resolveInput,
} from './factCalculation.js';

/**
 * Every figure and sentence below is from Reliance Industries' Integrated
 * Annual Report 2025-26. Fixtures marked CONSTRUCTED alter one of them to
 * reach a branch the filing does not exhibit - a restatement needs a second
 * document, and Reliance's EBITDA is not zero.
 */
const RELIANCE = 'RIL FY2025-26';
const PERIOD = '2026-03-31';

const fact = (over) => ({
  company: 'RELIANCE', period_end: PERIOD, period_type: 'annual',
  accounting_scope: 'consolidated', entity_scope: 'group', currency: 'INR', unit: 10000000,
  reported_in_document: RELIANCE, segment: null, verdict: 'stated', ...over,
});

const CFO = fact({
  concept: 'cfo', definition_id: 'CFO.STATEMENT', measurement_basis: 'cash', value: 192113,
  as_reported_label: 'Cash Flow from Operating Activities',
  source_sentence: 'Cash   Flow   from   Operating   Activities   *   1,92,113   1,78,703',
});
const CASH_CAPEX = fact({
  concept: 'capex', definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash', value: 122916,
  as_reported_label: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets',
  source_sentence: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets   (1,22,916)   (1,39,967)',
});
const MANAGEMENT_CAPEX = fact({
  concept: 'capex', definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual', value: 144271,
  as_reported_label: 'capital expenditure',
  source_sentence: 'RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.',
});
const EBITDA = fact({
  concept: 'ebitda', definition_id: 'EBITDA.REPORTED', measurement_basis: 'management_adjusted', value: 207911,
  as_reported_label: 'EBITDA',
  source_sentence: 'EBITDA for FY 2025-26 was at  H   2,07,911 crore (US$ 21.9 billion), expanding 13.4% Y-o-Y, boosted by strong performances in Digital Services and O2C segments.',
});
const REVENUE_GROSS = fact({
  concept: 'revenue', definition_id: 'REVENUE.VALUE_OF_SALES_AND_SERVICES', measurement_basis: 'statutory', value: 1175919,
  as_reported_label: 'Value of Sales and Services',
  source_sentence: 'Consolidated revenue grew by 9.8% Y-o-Y, at   H   11,75,919 crore (US$ 124.0 billion), driven by robust double-digit growth in Digital Services, Retail and Media & Entertainment businesses.',
});
const REVENUE_NET = fact({
  concept: 'revenue', definition_id: 'REVENUE.OPERATIONS_NET', measurement_basis: 'statutory', value: 1075675,
  as_reported_label: 'Revenue from Operations (Net of GST)',
  source_sentence: 'Revenue from Operations  (Net of GST)  6,40,972   23,837   3,28,202   1,49,965   70,813   -   10,75,675',
});
const DEBT_SENTENCE = 'Gross debt as on March 31, 2026 was  H   3,74,421 crore (US$ 39.5 billion) and Net debt stood at   H   1,24,717 crore (US$ 13.2 billion).';
const NET_DEBT = fact({
  concept: 'debt', definition_id: 'DEBT.NET', measurement_basis: 'statutory', value: 124717,
  as_reported_label: 'Net debt', source_sentence: DEBT_SENTENCE,
});
const GROSS_DEBT = fact({
  concept: 'debt', definition_id: 'DEBT.GROSS', measurement_basis: 'statutory', value: 374421,
  as_reported_label: 'Gross debt', source_sentence: DEBT_SENTENCE,
});

const CONSOLIDATED = [CFO, CASH_CAPEX, MANAGEMENT_CAPEX, EBITDA, REVENUE_GROSS, REVENUE_NET, NET_DEBT, GROSS_DEBT];

// Reliance's Retail business states its own EBITDA margin and, in a footnote,
// which revenue it divided by.
const RETAIL_ROW = 'Revenue from Operations   3,28,202   2,91,043   12.8% EBITDA   27,034   25,094   7.7% EBITDA margin*   8.2%   8.6%   (40 bps)  *EBITDA margin is calculated on Revenue from Operations';
const RETAIL = [
  fact({ concept: 'ebitda', definition_id: 'EBITDA.REPORTED', measurement_basis: 'management_adjusted',
    entity_scope: 'segment', segment: 'Retail', value: 27034, as_reported_label: 'EBITDA',
    source_sentence: 'EBITDA for the year stood at   H   27,034 crore, translating into an EBITDA margin of 8.2%, slight moderation due to growing contribution of hyper-local commerce.' }),
  fact({ concept: 'revenue', definition_id: 'REVENUE.OPERATIONS_NET', measurement_basis: 'statutory',
    entity_scope: 'segment', segment: 'Retail', value: 328202,
    as_reported_label: 'Revenue from Operations', source_sentence: RETAIL_ROW }),
  fact({ concept: 'ebitda_margin', definition_id: 'EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET',
    measurement_basis: 'derived_ratio', entity_scope: 'segment', segment: 'Retail', value: 0.082,
    currency: null, unit: 1, as_reported_label: 'EBITDA margin', source_sentence: RETAIL_ROW }),
];

const at = (definition_id, over = {}) => ({ definition_id, period_end: PERIOD, ...over });

test('free cash flow is computed twice because it is two figures', () => {
  const cash = calculate(CONSOLIDATED, at('FCF.CFO_MINUS_CASH_CAPEX'));
  const management = calculate(CONSOLIDATED, at('FCF.CFO_MINUS_MANAGEMENT_CAPEX'));
  assert.equal(cash.value, 69197);
  assert.equal(management.value, 47842);
  assert.equal(cash.verdict, 'derived');
  // The definition is not chosen. It follows from which capex was consumed.
  assert.match(cash.input_fact_ids.capex, /CAPEX\.CASH_PPE_INTANGIBLES/);
  assert.match(management.input_fact_ids.capex, /CAPEX\.MANAGEMENT/);
});

test('a computed figure never travels without its inputs', () => {
  const computed = calculate(CONSOLIDATED, at('FCF.CFO_MINUS_CASH_CAPEX'));
  assert.equal(computed.formula, 'cfo - capex');
  assert.deepEqual(Object.keys(computed.input_fact_ids).sort(), ['capex', 'cfo']);
  assert.equal(computed.measurement_basis, 'cash');
});

test('a missing input is a stated absence, not a partial answer', () => {
  const computed = calculate([CFO, REVENUE_NET], at('FCF.CFO_MINUS_CASH_CAPEX'));
  assert.equal(computed.value, null);
  assert.equal(computed.verdict, 'unsupported');
  assert.equal(computed.reason, 'CAPEX.CASH_PPE_INTANGIBLES is not disclosed');
});

test('an input that resolves two ways is refused, not picked from', () => {
  // CONSTRUCTED: the FY26 operating cash flow as two documents report it.
  const restated = { ...CFO, value: 190000, reported_in_document: 'RIL FY2026-27', original_or_restated: 'restated' };
  const computed = calculate([CFO, restated, CASH_CAPEX], at('FCF.CFO_MINUS_CASH_CAPEX'));
  assert.equal(computed.verdict, 'unsupported');
  assert.match(computed.reason, /192113 and 190000/);
});

test('ambiguity is not laundered by computing through it', () => {
  // CONSTRUCTED. The free cash flow below the margin is ambiguous, so the
  // margin must be too - a derivable input is not licence to derive one.
  const restated = { ...CFO, value: 190000, reported_in_document: 'RIL FY2026-27' };
  const computed = calculate([CFO, restated, CASH_CAPEX, REVENUE_NET],
    at('FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET'));
  assert.equal(computed.value, null);
  assert.match(computed.reason, /192113 and 190000/);
});

test('the same EBITDA over two revenues is two margins, both real', () => {
  assert.equal(calculate(CONSOLIDATED, at('EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET')).value, 0.193284);
  assert.equal(calculate(CONSOLIDATED, at('EBITDA_MARGIN.ON_VALUE_OF_SALES_AND_SERVICES')).value, 0.176807);
});

test('leverage is computed on both debt definitions', () => {
  assert.equal(calculate(CONSOLIDATED, at('LEVERAGE.NET_DEBT_TO_EBITDA')).value, 0.599858);
  assert.equal(calculate(CONSOLIDATED, at('LEVERAGE.GROSS_DEBT_TO_EBITDA')).value, 1.800872);
});

test('a figure the filing already states is reported beside it, not instead', () => {
  const computed = calculate(RETAIL, at('EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET', { segment: 'Retail' }));
  // 27,034 over 3,28,202 is 8.237%. Reliance prints 8.2%. Both survive.
  assert.equal(computed.value, 0.08237);
  assert.equal(computed.also_stated.value, 0.082);
  assert.equal(computed.also_stated.difference, 0.00037);
  assert.equal(computed.also_stated.within_rounding, true);
});

test('rounding slack divides, it does not add', () => {
  // Two figures rounded to the crore can each be half a crore out, so their
  // difference can be one crore out. Their quotient cannot be anything like
  // that far out, and a check that added the slack would accept nonsense.
  const money = calculate(CONSOLIDATED, at('FCF.CFO_MINUS_CASH_CAPEX'));
  const ratio = calculate(CONSOLIDATED, at('EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET'));
  assert.equal(money.tolerance, 1);
  assert.ok(ratio.tolerance < 1e-6, `ratio tolerance was ${ratio.tolerance}`);
  assert.equal(propagatedSlack({ produces: 'money', value: 1, inputs: { a: CFO, b: CASH_CAPEX } }), 1);
});

test('lineage runs down to what the filing says', () => {
  const computed = calculate(CONSOLIDATED, at('FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET'));
  assert.equal(computed.value, 0.064329);
  const tree = lineage(computed, CONSOLIDATED);
  assert.equal(tree.inputs.fcf.verdict, 'derived');
  assert.equal(tree.inputs.fcf.inputs.cfo.verdict, 'stated');
  assert.match(tree.inputs.fcf.inputs.cfo.source_sentence, /1,92,113/);
  assert.match(tree.inputs.fcf.inputs.capex.source_sentence, /1,22,916/);
  assert.equal(tree.inputs.revenue.value, 1075675);
});

test('a figure computed from current facts is not stale', () => {
  const computed = calculate(CONSOLIDATED, at('FCF.CFO_MINUS_CASH_CAPEX'));
  assert.deepEqual(isStale(computed, CONSOLIDATED), { stale: false, reasons: [] });
});

test('a restatement invalidates what was computed from it', () => {
  // CONSTRUCTED: next year's report restates the operating cash flow.
  const computed = calculate(CONSOLIDATED, at('FCF.CFO_MINUS_CASH_CAPEX'));
  const later = CONSOLIDATED.map((row) => (row === CFO
    ? { ...CFO, value: 190000, reported_in_document: 'RIL FY2026-27', original_or_restated: 'restated' }
    : row));
  const check = isStale(computed, later);
  assert.equal(check.stale, true);
  assert.deepEqual(check.reasons, ['cfo now resolves to a different fact']);
});

test('a restatement two levels down invalidates the figure above it', () => {
  // CONSTRUCTED. The margin's own inputs are a free cash flow and a revenue,
  // and neither changed name. Only the value underneath did.
  const margin = calculate(CONSOLIDATED, at('FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET'));
  const later = CONSOLIDATED.map((row) => (row === CFO
    ? { ...CFO, value: 190000, reported_in_document: 'RIL FY2026-27', original_or_restated: 'restated' }
    : row));
  const check = isStale(margin, later);
  assert.equal(check.stale, true);
  assert.deepEqual(check.reasons, ['fcf now resolves to a different fact']);
});

test('a zero denominator is refused rather than returned as infinity', () => {
  // CONSTRUCTED.
  const flat = CONSOLIDATED.map((row) => (row === EBITDA ? { ...EBITDA, value: 0 } : row));
  const computed = calculate(flat, at('LEVERAGE.NET_DEBT_TO_EBITDA'));
  assert.equal(computed.value, null);
  assert.equal(computed.reason, 'the denominator is zero');
});

test('inputs in different money are not subtracted', () => {
  // CONSTRUCTED: the dollar equivalent Reliance prints beside the rupee figure.
  const inDollars = { ...CASH_CAPEX, currency: 'USD', unit: 1000000, value: 12960 };
  const computed = calculate([CFO, inDollars], at('FCF.CFO_MINUS_CASH_CAPEX'));
  assert.equal(computed.verdict, 'unsupported');
  assert.match(computed.reason, /INR.*USD|USD.*INR/);
});

test('a ratio carries no currency and a money figure keeps one', () => {
  const ratio = calculate(CONSOLIDATED, at('LEVERAGE.NET_DEBT_TO_EBITDA'));
  const money = calculate(CONSOLIDATED, at('FCF.CFO_MINUS_CASH_CAPEX'));
  assert.equal(ratio.currency, null);
  assert.equal(ratio.unit, 1);
  assert.equal(money.currency, 'INR');
  assert.equal(money.unit, 10000000);
});

test('a definition with no recipe is not computed', () => {
  const computed = calculate(CONSOLIDATED, at('CAPEX.MANAGEMENT'));
  assert.equal(computed.verdict, 'unsupported');
  assert.equal(computed.reason, 'no recipe for CAPEX.MANAGEMENT');
});

test('a recipe that depends on itself is refused, not followed', () => {
  RECIPES.set('LEVERAGE.NET_DEBT_TO_EBITDA', {
    inputs: { debt: 'LEVERAGE.NET_DEBT_TO_EBITDA', ebitda: 'EBITDA.REPORTED' },
    expression: 'debt / ebitda', formula: ({ debt, ebitda }) => debt / ebitda, produces: 'ratio',
  });
  const original = {
    inputs: { debt: 'DEBT.NET', ebitda: 'EBITDA.REPORTED' },
    expression: 'debt / ebitda', formula: ({ debt, ebitda }) => debt / ebitda, produces: 'ratio',
  };
  try {
    const computed = calculate(CONSOLIDATED, at('LEVERAGE.NET_DEBT_TO_EBITDA'));
    assert.equal(computed.value, null);
    assert.match(computed.reason, /depends on itself/);
  } finally {
    RECIPES.set('LEVERAGE.NET_DEBT_TO_EBITDA', original);
  }
});

test('resolveInput takes the document it is told to take', () => {
  const restated = { ...CFO, value: 190000, reported_in_document: 'RIL FY2026-27' };
  const picked = resolveInput([CFO, restated],
    { definition_id: 'CFO.STATEMENT', period_end: PERIOD, accounting_scope: 'consolidated', segment: null,
      reported_in_document: 'RIL FY2026-27' });
  assert.equal(picked.fact.value, 190000);
});

test('everything the facts support, and a reason for everything they do not', () => {
  const { derived, unsupported } = calculateAll([CFO, CASH_CAPEX, REVENUE_NET], { period_end: PERIOD });
  assert.deepEqual(derived.map((row) => row.definition_id).sort(), [
    'FCF.CFO_MINUS_CASH_CAPEX', 'FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET',
  ]);
  assert.ok(unsupported.every((row) => row.value === null && row.reason));
  assert.ok(unsupported.some((row) => row.reason === 'EBITDA.REPORTED is not disclosed'));
});

test('calculation never alters the facts it was given', () => {
  const before = JSON.stringify(CONSOLIDATED);
  calculateAll(CONSOLIDATED, { period_end: PERIOD });
  assert.equal(JSON.stringify(CONSOLIDATED), before);
});

test('a derivable input that is stated twice is refused, not re-derived', () => {
  // CONSTRUCTED: two documents state a free cash flow and disagree. It is also
  // derivable, and deriving it would replace a disagreement the reader needs
  // to see with a figure that looks settled.
  const stated = fact({
    concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', measurement_basis: 'cash',
    value: 69197, as_reported_label: 'Free cash flow', source_sentence: 'Free cash flow was 69,197 crore.',
  });
  const disagrees = { ...stated, value: 68000, reported_in_document: 'RIL FY2026-27' };
  const computed = calculate([CFO, CASH_CAPEX, REVENUE_NET, stated, disagrees],
    at('FCF_MARGIN.CASH_CAPEX_ON_REVENUE_OPERATIONS_NET'));
  assert.equal(computed.value, null);
  assert.match(computed.reason, /69197 and 68000/);
});
