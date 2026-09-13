import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFINITIONS, DIMENSIONLESS, MEASUREMENT, ENTITY_SCOPE, VERDICT,
  factKey, familyOf, reconcile, derive,
} from './factOntology.js';

// Reliance Industries, FY2026 consolidated, ₹ crore. Every figure verbatim
// from the Integrated Annual Report 2025-26.
const fact = (over) => ({
  company: 'RELIANCE', period: '2026-03-31', period_type: 'annual',
  accounting_scope: 'consolidated', entity_scope: ENTITY_SCOPE.GROUP,
  currency: 'INR', unit: 1e7, reported_in_document: 'RIL_IAR_2026', ...over,
});

const CAPEX_MANAGEMENT = fact({
  id: 'f1', concept: 'capex', definition_id: 'CAPEX.MANAGEMENT', value: 144271,
  as_reported_label: 'Capex', source_section: 'Financial Performance and Review',
});
const CAPEX_SEGMENT = fact({
  id: 'f2', concept: 'capex', definition_id: 'CAPEX.SEGMENT', value: 144271,
  as_reported_label: 'Capital Expenditure', source_section: 'Segment note',
});
const CAPEX_CASH = fact({
  id: 'f3', concept: 'capex', definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', value: 122916,
  as_reported_label: 'Purchase of Property, Plant and Equipment, Spectrum and Other Intangible Assets',
  source_section: 'Consolidated Cash Flow Statement',
});
const CFO = fact({ id: 'f4', concept: 'cfo', definition_id: 'CFO.STATEMENT', value: 192113,
  as_reported_label: 'Net Cash Flow from Operating Activities' });

describe('three observations of one concept', () => {
  test('they are three facts, not one overwritten twice', () => {
    const keys = new Set([CAPEX_MANAGEMENT, CAPEX_SEGMENT, CAPEX_CASH].map(factKey));
    assert.equal(keys.size, 3);
  });

  test('the issuer’s own label is never discarded', () => {
    // "Value of Sales and Services" is how Reliance says revenue, and a reader
    // asking where a number came from needs the words the filing used.
    assert.match(CAPEX_CASH.as_reported_label, /^Purchase of Property, Plant and Equipment/);
  });

  test('a definition carries how it was measured', () => {
    assert.equal(DEFINITIONS.get('CAPEX.CASH_PPE_INTANGIBLES').measurement, MEASUREMENT.CASH);
    assert.equal(DEFINITIONS.get('CAPEX.MANAGEMENT').measurement, MEASUREMENT.ACCRUAL);
    assert.equal(DEFINITIONS.get('CAPEX.SEGMENT').measurement, MEASUREMENT.SEGMENT_REPORTING);
  });

  test('every definition names a concept and a measurement', () => {
    for (const [id, entry] of DEFINITIONS) {
      assert.ok(entry.concept, `${id} has no concept`);
      assert.ok(Object.values(MEASUREMENT).includes(entry.measurement), `${id}: ${entry.measurement}`);
    }
  });
});

describe('a restated period is not the same fact', () => {
  test('FY25 as first reported and FY25 restated are two facts', () => {
    // Letting one overwrite the other loses the restatement, which is the
    // thing a reader most wants to know.
    const asReported = fact({ period: '2025-03-31', concept: 'revenue',
      definition_id: 'REVENUE.VALUE_OF_SALES_AND_SERVICES', value: 1071174,
      reported_in_document: 'RIL_IAR_2025' });
    const restated = { ...asReported, reported_in_document: 'RIL_IAR_2026' };
    assert.notEqual(factKey(asReported), factKey(restated));
  });

  test('a dimension is part of the key, so it needs no column', () => {
    const floating = fact({ concept: 'debt', definition_id: 'DEBT.GROSS', value: 117221,
      dimensions: { debt_type: 'floating' } });
    const fixed = { ...floating, dimensions: { debt_type: 'fixed' }, value: 85725 };
    assert.notEqual(factKey(floating), factKey(fixed));
    // And the order dimensions are written in does not change identity.
    const reordered = { ...floating, dimensions: { debt_type: 'floating', geography: null } };
    assert.equal(factKey(floating), factKey(reordered));
  });
});

describe('reconciling a family', () => {
  const family = familyOf([CAPEX_MANAGEMENT, CAPEX_SEGMENT, CAPEX_CASH, CFO],
    { concept: 'capex', period: '2026-03-31' });

  test('the family is the observations of one concept, and nothing else', () => {
    assert.equal(family.length, 3);
    assert.equal(family.some((f) => f.concept === 'cfo'), false);
  });

  test('different definitions differing is not a contradiction', () => {
    const found = reconcile(family);
    assert.equal(found.status, 'different_definitions');
    assert.equal(found.reconciliation, 'unresolved');
  });

  test('the two that agree are reported as agreeing', () => {
    const found = reconcile([CAPEX_MANAGEMENT, CAPEX_SEGMENT]);
    assert.equal(found.status, 'agree');
    assert.equal(found.differences[0].difference, 0);
  });

  test('a difference is named against each side it is a share of', () => {
    // 21,355 is 14.8% of the management figure and 17.4% of the cash figure.
    // Both are true and they mean different things, so neither is "the"
    // percentage.
    const found = reconcile([CAPEX_MANAGEMENT, CAPEX_CASH]);
    const [gap] = found.differences;
    assert.equal(gap.difference, 21355);
    assert.ok(Math.abs(gap.as_share_of['CAPEX.MANAGEMENT'] - 21355 / 144271) < 1e-6);
    assert.ok(Math.abs(gap.as_share_of['CAPEX.CASH_PPE_INTANGIBLES'] - 21355 / 122916) < 1e-6);
  });

  test('one observation is not a reconciliation', () => {
    assert.equal(reconcile([CAPEX_CASH]).status, 'single_observation');
    assert.equal(reconcile([]).status, 'none');
  });
});

describe('derived facts carry what produced them', () => {
  const byManagement = derive({
    concept: 'fcf',
    definition_id: 'FCF.CFO_MINUS_MANAGEMENT_CAPEX',
    formula: ({ cfo, capex }) => cfo - capex,
    inputs: { cfo: CFO, capex: CAPEX_MANAGEMENT },
  });
  const byCash = derive({
    concept: 'fcf',
    definition_id: 'FCF.CFO_MINUS_CASH_CAPEX',
    formula: ({ cfo, capex }) => cfo - capex,
    inputs: { cfo: CFO, capex: CAPEX_CASH },
  });

  test('two definitions of free cash flow, both correct', () => {
    assert.equal(byManagement.value, 47842);
    assert.equal(byCash.value, 69197);
    assert.equal(byManagement.verdict, VERDICT.DERIVED);
  });

  test('the free cash flows differ by far more than the capex figures do', () => {
    // The same ₹21,355 crore gap is 17.4% of cash capex and 44.6% of the
    // smaller free cash flow. Attaching the larger number to the capex
    // discrepancy would be wrong, and it is a mistake I made.
    const spread = (byCash.value - byManagement.value) / byManagement.value;
    assert.ok(Math.abs(spread - 0.4464) < 0.001, String(spread));
    const capexSpread = 21355 / 122916;
    assert.ok(Math.abs(capexSpread - 0.1737) < 0.001, String(capexSpread));
  });

  test('inputs are recorded as facts, not as numbers', () => {
    // A restated input can then invalidate everything downstream instead of
    // leaving a stale figure that still looks computed.
    assert.deepEqual(byManagement.input_fact_ids, { cfo: 'f4', capex: 'f1' });
  });

  test('a missing input refuses and names what was missing', () => {
    const found = derive({
      concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX',
      formula: ({ cfo, capex }) => cfo - capex,
      inputs: { cfo: CFO, capex: null },
    });
    assert.equal(found.value, null);
    assert.equal(found.verdict, VERDICT.UNSUPPORTED);
    assert.match(found.reason, /capex not available/);
  });
});

describe('four verdicts, not two', () => {
  test('a sum of stated components is derived, not unsupported', () => {
    // Reliance's contingent claims of ₹5,532 crore appear nowhere in the
    // filing: it is 1,692 for joint arrangements plus 3,840 for others. A
    // checker that only accepts literal matches rejects correct arithmetic.
    const joint = fact({ id: 'c1', concept: 'contingent_claims', definition_id: 'DEBT.GROSS', value: 1692 });
    const others = fact({ id: 'c2', concept: 'contingent_claims', definition_id: 'DEBT.GROSS', value: 3840 });
    const total = derive({
      concept: 'contingent_claims', definition_id: 'DEBT.GROSS',
      formula: ({ a, b }) => a + b, inputs: { a: joint, b: others },
    });
    assert.equal(total.value, 5532);
    assert.equal(total.verdict, VERDICT.DERIVED);
  });

  test('inferred is a verdict of its own', () => {
    // "Reliance has no material refinancing risk" reads liquidity, the
    // maturity profile and a credit rating together. It is supported by facts
    // and entailed by none of them, and calling it derived would claim an
    // arithmetic that does not exist.
    assert.equal(VERDICT.INFERRED, 'inferred');
    assert.notEqual(VERDICT.INFERRED, VERDICT.DERIVED);
    assert.equal(new Set(Object.values(VERDICT)).size, 4);
  });
});

test('a definition is complete or it is not a definition', () => {
  // A definition missing `measures` stops being compared to anything and one
  // missing `measurement` cannot be stored, both silently.
  for (const [id, definition] of DEFINITIONS) {
    for (const field of ['concept', 'measurement', 'measures', 'label']) {
      assert.ok(definition[field], `${id} has no ${field}`);
    }
    assert.ok(Object.values(MEASUREMENT).includes(definition.measurement), `${id} has an unknown basis`);
  }
});

test('a quantity is competed for within one concept, never across two', () => {
  // Two definitions claiming the same quantity are compared against each
  // other. If they sat under different concepts the comparison would cross a
  // boundary the rest of the system is built to respect.
  const byQuantity = new Map();
  for (const [id, definition] of DEFINITIONS) {
    if (!byQuantity.has(definition.measures)) byQuantity.set(definition.measures, new Set());
    byQuantity.get(definition.measures).add(definition.concept);
  }
  for (const [quantity, concepts] of byQuantity) {
    assert.equal(concepts.size, 1, `${quantity} is claimed under ${[...concepts].join(' and ')}`);
  }
});

test('a count and a ratio are dimensionless; everything else is money', () => {
  assert.ok(DIMENSIONLESS.has(MEASUREMENT.COUNT));
  assert.ok(DIMENSIONLESS.has(MEASUREMENT.DERIVED_RATIO));
  for (const basis of [MEASUREMENT.CASH, MEASUREMENT.ACCRUAL, MEASUREMENT.STATUTORY,
    MEASUREMENT.SEGMENT_REPORTING, MEASUREMENT.MANAGEMENT_ADJUSTED]) {
    assert.equal(DIMENSIONLESS.has(basis), false, `${basis} should require a currency`);
  }
  // Share counts are the reason COUNT exists: Q77 asks whether the share count
  // moved, and 1,353 crore shares are not an amount of rupees.
  assert.equal(DEFINITIONS.get('SHARE_COUNT.OUTSTANDING').measurement, MEASUREMENT.COUNT);
});
