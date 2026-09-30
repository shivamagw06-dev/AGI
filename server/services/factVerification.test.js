import test from 'node:test';
import assert from 'node:assert/strict';
import {
  checkIdentity, checkRestatements, checkSegmentSum, isReconcilingSegment,
  roundingSlack, statedPrecision, verify, FREE_CASH_FLOW,
} from './factVerification.js';

/**
 * Figures and sentences below are from Reliance Industries' Integrated Annual
 * Report 2025-26, quoted as the extraction reads them. Where a branch needs a
 * disclosure Reliance does not make - it states no free cash flow, and one
 * document cannot restate another - the fixture says CONSTRUCTED and is there
 * to exercise the code, not to assert anything about a company.
 */
const RELIANCE = 'RIL FY2025-26';

const SEGMENT_ROW = 'Capital Expenditure   32,365   1,756   21,131   33,101   52,521   3,397   1,44,271';
const MANAGEMENT = 'RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.';
const CASH_CAPEX = 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets   (1,22,916)   (1,39,967)';
const CFO_ROW = 'Cash   Flow   from   Operating   Activities   *   1,92,113   1,78,703';

const fact = (over) => ({
  company: 'RELIANCE', period_end: '2026-03-31', period_type: 'annual',
  accounting_scope: 'consolidated', entity_scope: 'group',
  currency: 'INR', unit: 10000000, reported_in_document: RELIANCE,
  segment: null, verdict: 'stated', ...over,
});

const segmentCapex = (segment, value) => fact({
  concept: 'capex', definition_id: 'CAPEX.SEGMENT', measurement_basis: 'segment_reporting',
  entity_scope: 'segment', segment, value,
  as_reported_label: 'Capital Expenditure', source_sentence: SEGMENT_ROW,
});

const OPERATING = [
  segmentCapex('O2C', 32365),
  segmentCapex('Oil and Gas', 1756),
  segmentCapex('Retail', 21131),
  segmentCapex('Digital Services', 33101),
  segmentCapex('Others', 52521),
];
const UNALLOCABLE = segmentCapex('Unallocable', 3397);
const SEGMENT_TOTAL = fact({
  concept: 'capex', definition_id: 'CAPEX.SEGMENT', measurement_basis: 'segment_reporting',
  value: 144271, as_reported_label: 'Capital Expenditure', source_sentence: SEGMENT_ROW,
});

const MANAGEMENT_CAPEX = fact({
  concept: 'capex', definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual',
  value: 144271, as_reported_label: 'capital expenditure', source_sentence: MANAGEMENT,
});
const CASH_CAPEX_FACT = fact({
  concept: 'capex', definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash',
  value: 122916, as_reported_label: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets',
  source_sentence: CASH_CAPEX,
});
const CFO = fact({
  concept: 'cfo', definition_id: 'CFO.STATEMENT', measurement_basis: 'cash',
  value: 192113, as_reported_label: 'Cash Flow from Operating Activities', source_sentence: CFO_ROW,
});

test('precision is read from the sentence, not from the stored number', () => {
  // 0.40 and 0.4 are one Number and two claims about how precisely it is known.
  assert.equal(statedPrecision({ value: 0.4, source_sentence: 'margin of 0.40 per cent' }), 2);
  assert.equal(statedPrecision({ value: 0.4, source_sentence: 'margin of 0.4 per cent' }), 1);
});

test('a table row of whole numbers is read as whole numbers', () => {
  // The row is "32,365   1,756   21,131". A pattern that swallowed the spaces
  // would read one number of fourteen digits and get the precision wrong.
  assert.equal(statedPrecision(OPERATING[0]), 0);
  assert.equal(statedPrecision(OPERATING[1]), 0);
});

test('tolerance is what rounding could account for and nothing else', () => {
  assert.equal(roundingSlack([...OPERATING, UNALLOCABLE, SEGMENT_TOTAL]), 3.5);
});

test('Unallocable is a column beside the segments, not a segment', () => {
  assert.equal(isReconcilingSegment('Unallocable'), true);
  assert.equal(isReconcilingSegment('Inter-segment'), true);
  assert.equal(isReconcilingSegment('O2C'), false);
  assert.equal(isReconcilingSegment('Digital Services'), false);
});

test("Reliance's segment capex adds up when the Unallocable column is counted", () => {
  const check = checkSegmentSum({
    facts: [...OPERATING, UNALLOCABLE, SEGMENT_TOTAL],
    definition_id: 'CAPEX.SEGMENT', period_end: '2026-03-31',
  });
  assert.equal(check.status, 'agrees');
  assert.equal(check.sum, 144271);
  assert.equal(check.residual, 0);
  assert.equal(check.operating_sum, 140874);
  assert.equal(check.reconciling_sum, 3397);
});

test('leaving the Unallocable column out is a residual, named, not an error', () => {
  const check = checkSegmentSum({
    facts: [...OPERATING, SEGMENT_TOTAL],
    definition_id: 'CAPEX.SEGMENT', period_end: '2026-03-31',
  });
  assert.equal(check.status, 'residual');
  assert.equal(check.residual, 3397);
  assert.equal(check.reconciling_sum, null);
  // The useful reading is that a column is missing from the extraction, not
  // that the filing fails to add up.
  assert.match(check.note, /unallocable|eliminations/i);
});

test('a residual inside what rounding allows is not reported as a gap', () => {
  const nudged = [...OPERATING.slice(0, 4), segmentCapex('Others', 52520), UNALLOCABLE, SEGMENT_TOTAL];
  const check = checkSegmentSum({ facts: nudged, definition_id: 'CAPEX.SEGMENT', period_end: '2026-03-31' });
  assert.equal(check.status, 'within_rounding');
  assert.equal(check.residual, 1);
});

test('segment arithmetic never crosses a definition', () => {
  // The segment total and management's capex are both 1,44,271 crore. They are
  // still two definitions, and the sum is checked against its own total only.
  const check = checkSegmentSum({
    facts: [...OPERATING, UNALLOCABLE, MANAGEMENT_CAPEX],
    definition_id: 'CAPEX.SEGMENT', period_end: '2026-03-31',
  });
  assert.equal(check.status, 'insufficient_data');
  assert.equal(check.reason, 'no total disclosed');
});

test('figures in different money are not added', () => {
  const inDollars = { ...UNALLOCABLE, currency: 'USD', unit: 1000000 };
  const check = checkSegmentSum({
    facts: [...OPERATING, inDollars, SEGMENT_TOTAL],
    definition_id: 'CAPEX.SEGMENT', period_end: '2026-03-31',
  });
  assert.equal(check.status, 'not_comparable');
});

test('Reliance states no free cash flow, so there is nothing to verify', () => {
  const check = checkIdentity({
    facts: [CFO, MANAGEMENT_CAPEX, CASH_CAPEX_FACT], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.status, 'no_stated_figure');
  assert.equal(check.candidates.length, 2);
});

test('the two defensible free cash flows are 44.6% apart', () => {
  const check = checkIdentity({
    facts: [CFO, MANAGEMENT_CAPEX, CASH_CAPEX_FACT], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  // 1,92,113 less cash capex is 69,197; less management capex is 47,842. The
  // gap is the same 21,355 crore as the capex gap and a different proportion:
  // 17.4% of cash capex, 44.6% of the smaller free cash flow.
  assert.equal(check.spread.high, 69197);
  assert.equal(check.spread.low, 47842);
  assert.equal(check.spread.difference, 21355);
  assert.equal(check.spread.as_share_of_low, 0.446365);
});

test('a stated figure identifies which capex the issuer meant', () => {
  // CONSTRUCTED: an issuer that does state free cash flow.
  const stated = fact({
    concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', measurement_basis: 'cash',
    value: 69197, as_reported_label: 'Free cash flow',
    source_sentence: 'Free cash flow for the year was 69,197.',
  });
  const check = checkIdentity({
    facts: [CFO, MANAGEMENT_CAPEX, CASH_CAPEX_FACT, stated], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.status, 'identifies_definition');
  assert.equal(check.readings[0].matches.length, 1);
  assert.equal(check.readings[0].matches[0].using.capex, 'CAPEX.CASH_PPE_INTANGIBLES');
});

test('arithmetic catches a figure filed under the wrong definition', () => {
  // CONSTRUCTED: the value is cash-capex free cash flow, filed as the
  // management-capex one. Only the arithmetic can tell.
  const mislabelled = fact({
    concept: 'fcf', definition_id: 'FCF.CFO_MINUS_MANAGEMENT_CAPEX', measurement_basis: 'cash',
    value: 69197, as_reported_label: 'Free cash flow',
    source_sentence: 'Free cash flow for the year was 69,197.',
  });
  const check = checkIdentity({
    facts: [CFO, MANAGEMENT_CAPEX, CASH_CAPEX_FACT, mislabelled], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.status, 'definition_mismatch');
  assert.deepEqual(check.readings[0].disagreement, [{
    concept: 'capex', filed_as: 'CAPEX.MANAGEMENT', arithmetic_says: 'CAPEX.CASH_PPE_INTANGIBLES',
  }]);
});

test('a stated figure matching no candidate is reported unexplained, not corrected', () => {
  // CONSTRUCTED.
  const odd = fact({
    concept: 'fcf', definition_id: 'FCF.CFO_MINUS_CASH_CAPEX', measurement_basis: 'cash',
    value: 58000, as_reported_label: 'Free cash flow',
    source_sentence: 'Free cash flow for the year was 58,000.',
  });
  const check = checkIdentity({
    facts: [CFO, MANAGEMENT_CAPEX, CASH_CAPEX_FACT, odd], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.status, 'unexplained');
  assert.equal(check.readings[0].stated, 58000);
  assert.equal(check.readings[0].against.length, 2);
});

test('an identity with a missing input says so instead of guessing', () => {
  const check = checkIdentity({
    facts: [MANAGEMENT_CAPEX, CASH_CAPEX_FACT], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.status, 'insufficient_data');
  assert.equal(check.reason, 'no cfo disclosed');
});

test('segment facts are not fed into a group identity', () => {
  const check = checkIdentity({
    facts: [CFO, ...OPERATING, UNALLOCABLE], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.status, 'insufficient_data');
});

test('the same figure from two documents is a restatement, not a conflict', () => {
  // CONSTRUCTED: one document cannot restate another.
  const asFiled = fact({
    period_end: '2025-03-31', concept: 'capex', definition_id: 'CAPEX.MANAGEMENT',
    measurement_basis: 'accrual', value: 131107, reported_in_document: 'RIL FY2024-25',
    as_reported_label: 'capital expenditure', source_sentence: 'Capital expenditure was 1,31,107 crore.',
  });
  const asRestated = { ...asFiled, value: 130500, reported_in_document: RELIANCE, original_or_restated: 'restated' };
  const [finding] = checkRestatements([asFiled, asRestated]);
  assert.equal(finding.status, 'restated');
  assert.equal(finding.change, -607);
  assert.equal(finding.reported_in.length, 2);
});

test('the same figure repeated by two documents is corroboration', () => {
  // CONSTRUCTED.
  const asFiled = fact({
    period_end: '2025-03-31', concept: 'capex', definition_id: 'CAPEX.MANAGEMENT',
    measurement_basis: 'accrual', value: 131107, reported_in_document: 'RIL FY2024-25',
    as_reported_label: 'capital expenditure', source_sentence: 'Capital expenditure was 1,31,107 crore.',
  });
  const [finding] = checkRestatements([asFiled, { ...asFiled, reported_in_document: RELIANCE }]);
  assert.equal(finding.status, 'confirmed');
});

test('one document reporting a figure once is not a restatement', () => {
  assert.deepEqual(checkRestatements([MANAGEMENT_CAPEX, CASH_CAPEX_FACT, CFO]), []);
});

test('verify finds the segment check without being told to look', () => {
  const checks = verify([...OPERATING, UNALLOCABLE, SEGMENT_TOTAL, MANAGEMENT_CAPEX, CASH_CAPEX_FACT, CFO],
    { identities: [{ period_end: '2026-03-31', ...FREE_CASH_FLOW }] });
  const segment = checks.find((check) => check.check === 'segment_sum');
  assert.equal(segment.definition_id, 'CAPEX.SEGMENT');
  assert.equal(segment.status, 'agrees');
  assert.equal(checks.find((check) => check.check === 'identity').status, 'no_stated_figure');
});

test('verification never alters the facts it was given', () => {
  const facts = [...OPERATING, UNALLOCABLE, SEGMENT_TOTAL, MANAGEMENT_CAPEX, CASH_CAPEX_FACT, CFO];
  const before = JSON.stringify(facts);
  verify(facts, { identities: [{ period_end: '2026-03-31', ...FREE_CASH_FLOW }] });
  assert.equal(JSON.stringify(facts), before);
});

test('a candidate mixing currencies is dropped, not converted', () => {
  // CONSTRUCTED: the cash capex figure restated in US dollars. Reliance gives
  // dollar equivalents throughout, and subtracting one from a rupee cash flow
  // would produce a number that looks like an answer.
  const inDollars = { ...CASH_CAPEX_FACT, currency: 'USD', unit: 1000000, value: 12960 };
  const check = checkIdentity({
    facts: [CFO, MANAGEMENT_CAPEX, inDollars], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.candidates.length, 1);
  assert.equal(check.candidates[0].using.capex, 'CAPEX.MANAGEMENT');
  assert.equal(check.spread, null);
});

test('an identity with nothing comparable left says so', () => {
  // CONSTRUCTED.
  const inDollars = { ...CASH_CAPEX_FACT, currency: 'USD', unit: 1000000, value: 12960 };
  const check = checkIdentity({
    facts: [CFO, inDollars], period_end: '2026-03-31', ...FREE_CASH_FLOW,
  });
  assert.equal(check.status, 'not_comparable');
});
