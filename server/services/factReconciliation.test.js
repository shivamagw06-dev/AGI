import test from 'node:test';
import assert from 'node:assert/strict';
import { calculate } from './factCalculation.js';
import {
  PURPOSES, coherenceOf, observationsFor, reconcileFamily, reconcileFor,
} from './factReconciliation.js';

/**
 * Figures and sentences are from Reliance Industries' Integrated Annual Report
 * 2025-26. Fixtures marked CONSTRUCTED reach branches the filing does not
 * exhibit - it states no free cash flow, and one document cannot restate
 * another.
 */
const PERIOD = '2026-03-31';
const RELIANCE = 'RIL FY2025-26';

const fact = (over) => ({
  company: 'RELIANCE', period_end: PERIOD, period_type: 'annual',
  accounting_scope: 'consolidated', entity_scope: 'group', currency: 'INR', unit: 10000000,
  reported_in_document: RELIANCE, segment: null, verdict: 'stated', ...over,
});

const MANAGEMENT_CAPEX = fact({
  concept: 'capex', definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual', value: 144271,
  as_reported_label: 'capital expenditure',
  source_sentence: 'RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.',
});
const CASH_CAPEX = fact({
  concept: 'capex', definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash', value: 122916,
  as_reported_label: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets',
  source_sentence: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets   (1,22,916)   (1,39,967)',
});
const SEGMENT_CAPEX = fact({
  concept: 'capex', definition_id: 'CAPEX.SEGMENT', measurement_basis: 'segment_reporting', value: 144271,
  as_reported_label: 'Capital Expenditure',
  source_sentence: 'Capital Expenditure   32,365   1,756   21,131   33,101   52,521   3,397   1,44,271',
});
const CFO = fact({
  concept: 'cfo', definition_id: 'CFO.STATEMENT', measurement_basis: 'cash', value: 192113,
  as_reported_label: 'Cash Flow from Operating Activities',
  source_sentence: 'Cash   Flow   from   Operating   Activities   *   1,92,113   1,78,703',
});
const REVENUE_GROSS = fact({
  concept: 'revenue', definition_id: 'REVENUE.VALUE_OF_SALES_AND_SERVICES', measurement_basis: 'statutory',
  value: 1175919, as_reported_label: 'Value of Sales and Services',
  source_sentence: 'Consolidated revenue grew by 9.8% Y-o-Y, at   H   11,75,919 crore (US$ 124.0 billion), driven by robust double-digit growth in Digital Services, Retail and Media & Entertainment businesses.',
});
const REVENUE_NET = fact({
  concept: 'revenue', definition_id: 'REVENUE.OPERATIONS_NET', measurement_basis: 'statutory',
  value: 1075675, as_reported_label: 'Revenue from Operations (Net of GST)',
  source_sentence: 'Revenue from Operations  (Net of GST)  6,40,972   23,837   3,28,202   1,49,965   70,813   -   10,75,675',
});
const TOTAL_INCOME = fact({
  concept: 'revenue', definition_id: 'REVENUE.TOTAL_INCOME', measurement_basis: 'statutory',
  value: 1104637, as_reported_label: 'Total Income',
  source_sentence: 'Total Income   116,480   11,04,637   9,98,114   9,30,529',
});

const CAPEX_FAMILY = [MANAGEMENT_CAPEX, CASH_CAPEX, SEGMENT_CAPEX];
const REVENUE_FAMILY = [REVENUE_GROSS, REVENUE_NET, TOTAL_INCOME];
const ALL = [...CAPEX_FAMILY, ...REVENUE_FAMILY, CFO];

const forConcept = (facts, concept, over = {}) => reconcileFamily({
  facts, concept, period_end: PERIOD, ...over,
});

test('a cash calculation takes the cash capex, and says why', () => {
  const picked = forConcept(CAPEX_FAMILY, 'capex', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'selected');
  assert.equal(picked.chosen.definition_id, 'CAPEX.CASH_PPE_INTANGIBLES');
  assert.equal(picked.chosen.value, 122916);
  assert.equal(picked.chosen_at_rank, 0);
  assert.deepEqual(picked.caveats, []);
  // Never a bare choice. The reason travels with it.
  assert.match(picked.rule, /cash calculation takes cash measurements/);
});

test('what the choice gives up is named against both sides', () => {
  const picked = forConcept(CAPEX_FAMILY, 'capex', { purpose: 'cash_basis' });
  const management = picked.forgone.find((row) => row.definition_id === 'CAPEX.MANAGEMENT');
  assert.equal(management.value, 144271);
  assert.equal(management.difference, -21355);
  // 17.4% of the figure taken, 14.8% of the one left. Both are the same gap.
  assert.equal(management.as_share_of_chosen, -0.173737);
  assert.equal(management.as_share_of_alternative, -0.14802);
  assert.equal(picked.forgone.length, 2);
});

test('a different purpose reaches a different figure from the same facts', () => {
  const segment = forConcept(CAPEX_FAMILY, 'capex', { purpose: 'segment_basis' });
  assert.equal(segment.chosen.definition_id, 'CAPEX.SEGMENT');
  assert.equal(segment.chosen_at_rank, 0);
  const accrual = forConcept(CAPEX_FAMILY, 'capex', { purpose: 'accrual_basis' });
  assert.equal(accrual.chosen.definition_id, 'CAPEX.MANAGEMENT');
});

test('a substitution is allowed and never silent', () => {
  // CONSTRUCTED: capex disclosed on an accrual and a segment basis but not a
  // cash one, used for a cash calculation because there is nothing else.
  // Two observations, so this is the ranked path and not the single-figure one.
  const picked = forConcept([MANAGEMENT_CAPEX, SEGMENT_CAPEX], 'capex', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'selected');
  assert.equal(picked.chosen.definition_id, 'CAPEX.MANAGEMENT');
  assert.equal(picked.chosen_at_rank, 1);
  assert.equal(picked.forgone.length, 1);
  assert.match(picked.caveats[0], /no cash observation was disclosed/);
  assert.match(picked.caveats[0], /measured accrual, which is not the same thing/);
});

test('a lone figure on the wrong basis is a substitution too', () => {
  // CONSTRUCTED: the same swap where there is nothing to rank against.
  const picked = forConcept([MANAGEMENT_CAPEX], 'capex', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'only_one_observation');
  assert.equal(picked.chosen_at_rank, 1);
  assert.match(picked.caveats[0], /no cash observation was disclosed/);
});

test('a purpose that admits nothing disclosed refuses rather than reaches', () => {
  const picked = forConcept(CAPEX_FAMILY, 'capex', { purpose: 'statutory_basis' });
  assert.equal(picked.status, 'no_fit');
  assert.equal(picked.chosen, null);
  assert.match(picked.reason, /nothing disclosed is measured on a basis the statutory accounts admits/);
});

test('three revenues on one basis need a definition, not a tiebreak', () => {
  // Reliance discloses revenue three ways and all three are statutory. A rule
  // about measurement cannot separate them, and inventing one would make the
  // answer depend on the order the facts were extracted.
  const picked = forConcept(REVENUE_FAMILY, 'revenue', { purpose: 'statutory_basis' });
  assert.equal(picked.status, 'needs_a_definition');
  assert.equal(picked.chosen, null);
  assert.deepEqual(picked.candidates.map((row) => row.definition_id).sort(), [
    'REVENUE.OPERATIONS_NET', 'REVENUE.TOTAL_INCOME', 'REVENUE.VALUE_OF_SALES_AND_SERVICES',
  ]);
  assert.equal(picked.spread.difference, 100244);
});

test('a caller naming a definition is recorded as the caller, not as a rule', () => {
  const picked = forConcept(REVENUE_FAMILY, 'revenue', {
    purpose: 'statutory_basis', prefer: { revenue: 'REVENUE.OPERATIONS_NET' },
  });
  assert.equal(picked.status, 'selected');
  assert.equal(picked.chosen.value, 1075675);
  assert.equal(picked.rule, 'named by the caller');
  assert.equal(picked.forgone.length, 2);
});

test('naming a definition the filing does not disclose is refused', () => {
  const picked = forConcept(REVENUE_FAMILY, 'revenue', { prefer: { revenue: 'REVENUE.SOMETHING_ELSE' } });
  assert.equal(picked.status, 'no_fit');
  assert.match(picked.reason, /not among the disclosed observations/);
});

test('without a purpose or a name, nothing is chosen', () => {
  const picked = forConcept(CAPEX_FAMILY, 'capex', {});
  assert.equal(picked.status, 'no_purpose');
  assert.equal(picked.chosen, null);
  // The differences are still reported. Refusing to choose is not refusing to
  // say what the choice is between.
  assert.equal(picked.forgone.length, 2);
  assert.equal(picked.spread.difference, 21355);
});

test('one observation is reported as one observation', () => {
  const picked = forConcept([CFO], 'cfo', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'only_one_observation');
  assert.equal(picked.chosen.value, 192113);
  assert.deepEqual(picked.forgone, []);
  assert.equal(picked.spread, null);
});

test('a concept the filing does not cover is not disclosed', () => {
  const picked = forConcept(ALL, 'ebitda', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'not_disclosed');
  assert.equal(picked.chosen, null);
});

test('observations in different money are not ranked against each other', () => {
  // CONSTRUCTED: the dollar equivalent Reliance prints beside the rupee figure.
  const inDollars = { ...CASH_CAPEX, currency: 'USD', unit: 1000000, value: 12960 };
  const picked = forConcept([MANAGEMENT_CAPEX, inDollars], 'capex', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'not_comparable');
  assert.equal(picked.chosen, null);
});

test('a stated figure outranks one computed from it', () => {
  // CONSTRUCTED: an issuer that states free cash flow, alongside the same
  // figure derived. Both are cash; only standing separates them.
  const derived = calculate([CFO, CASH_CAPEX], { definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', period_end: PERIOD });
  const stated = fact({
    concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', measurement_basis: 'cash', value: 69197,
    as_reported_label: 'Free cash flow', source_sentence: 'Free cash flow was 69,197 crore.',
  });
  // The derived one comes first, so position cannot be what decides it.
  const picked = forConcept([CFO, CASH_CAPEX, derived, stated], 'fcf', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'selected');
  assert.equal(picked.chosen.verdict, 'stated');
  assert.equal(picked.forgone[0].definition_id, 'FCF.CFO_MINUS_CASH_CAPEX');
});

test('a computed figure whose inputs have moved is not an alternative', () => {
  // CONSTRUCTED: next year's report restates the operating cash flow, so the
  // free cash flow computed from the old one should already have been
  // withdrawn. It is left out, and the reason is given.
  const derived = calculate([CFO, CASH_CAPEX], { definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', period_end: PERIOD });
  const restated = { ...CFO, value: 190000, reported_in_document: 'RIL FY2026-27', original_or_restated: 'restated' };
  const picked = forConcept([restated, CASH_CAPEX, derived], 'fcf', { purpose: 'cash_basis' });
  assert.equal(picked.status, 'not_disclosed');
  assert.match(picked.caveats[0], /FCF\.CFO_MINUS_CASH_CAPEX was left out/);
  assert.match(picked.caveats[0], /cfo now resolves to a different fact/);
});

test('a purpose applied across concepts is checked for coherence', () => {
  const across = reconcileFor({ facts: ALL, purpose: 'cash_basis', period_end: PERIOD });
  const byConcept = Object.fromEntries(across.selections.map((row) => [row.concept, row]));
  assert.equal(byConcept.capex.chosen.definition_id, 'CAPEX.CASH_PPE_INTANGIBLES');
  assert.equal(byConcept.cfo.chosen.definition_id, 'CFO.STATEMENT');
  // Capex and operating cash flow are both cash. Revenue has no cash
  // measurement at all, so the set cannot be used as it stands.
  assert.equal(across.coherence.coherent, false);
  assert.deepEqual(across.coherence.bases, ['cash']);
  assert.deepEqual(across.coherence.unresolved, [{
    concept: 'revenue', status: 'needs_a_definition',
    reason: across.coherence.unresolved[0].reason,
  }]);
});

test('naming the revenue makes the set coherent', () => {
  const across = reconcileFor({
    facts: ALL, purpose: 'cash_basis', period_end: PERIOD,
    prefer: { revenue: 'REVENUE.OPERATIONS_NET' },
  });
  assert.equal(across.coherence.coherent, true);
  assert.deepEqual(across.coherence.substituted, []);
  assert.deepEqual(across.coherence.unresolved, []);
});

test('a substitution anywhere in the set makes the set incoherent', () => {
  // CONSTRUCTED: capex only on an accrual basis, in a cash calculation.
  const across = reconcileFor({
    facts: [MANAGEMENT_CAPEX, CFO], purpose: 'cash_basis', period_end: PERIOD,
  });
  assert.equal(across.coherence.coherent, false);
  assert.deepEqual(across.coherence.substituted, [{
    concept: 'capex', definition_id: 'CAPEX.MANAGEMENT', measurement: 'accrual',
  }]);
});

test('coherence over an unknown purpose is not asserted', () => {
  assert.equal(coherenceOf([], 'making it up').coherent, false);
});

test('every purpose names a rule and an ordered preference', () => {
  for (const [name, purpose] of PURPOSES) {
    assert.ok(purpose.rule.length > 20, `${name} has no rule`);
    assert.ok(purpose.prefer.length >= 1 && purpose.prefer.every((bases) => bases.length >= 1), name);
  }
});

test('observations respect segment and scope', () => {
  const standalone = { ...CASH_CAPEX, accounting_scope: 'standalone' };
  const retail = { ...CASH_CAPEX, segment: 'Retail' };
  assert.equal(observationsFor([CASH_CAPEX, standalone, retail],
    { concept: 'capex', period_end: PERIOD }).length, 1);
  assert.equal(observationsFor([CASH_CAPEX, standalone, retail],
    { concept: 'capex', period_end: PERIOD, segment: 'Retail' }).length, 1);
});

test('reconciliation never alters the facts it was given', () => {
  const before = JSON.stringify(ALL);
  reconcileFor({ facts: ALL, purpose: 'cash_basis', period_end: PERIOD });
  assert.equal(JSON.stringify(ALL), before);
});
