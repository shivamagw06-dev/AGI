import test from 'node:test';
import assert from 'node:assert/strict';
import { MONTHS_IN, asOf, changeIn, comparable, overlapOf, periodOf, seriesOf } from './factPeriods.js';

/**
 * Figures are from Reliance Industries' Integrated Annual Report 2025-26,
 * which states each year beside its comparative. Fixtures marked CONSTRUCTED
 * reach branches one document cannot exhibit on its own.
 */
const RELIANCE = 'RIL FY2025-26';
const LAST_YEAR = 'RIL FY2024-25';

const fact = (over) => ({
  company: 'RELIANCE', period_type: 'annual', accounting_scope: 'consolidated',
  entity_scope: 'group', currency: 'INR', unit: 10000000,
  reported_in_document: RELIANCE, segment: null, verdict: 'stated', ...over,
});

const CAPEX_SENTENCE = 'RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.';
const CASH_ROW = 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets   (1,22,916)   (1,39,967)';
const CFO_ROW = 'Cash   Flow   from   Operating   Activities   *   1,92,113   1,78,703';
const EBITDA_ROW = 'Earnings Before Depreciation, Finance Cost and Tax Expenses (EBITDA) #  21,923   2,07,911   1,83,422   1,78,290';

const pair = (definition_id, concept, now, before, source_sentence) => [
  fact({ concept, definition_id, period_end: '2026-03-31', value: now, source_sentence }),
  fact({ concept, definition_id, period_end: '2025-03-31', value: before, source_sentence }),
];

const FACTS = [
  ...pair('CAPEX.MANAGEMENT', 'capex', 144271, 131107, CAPEX_SENTENCE),
  ...pair('CAPEX.CASH_PPE_INTANGIBLES', 'capex', 122916, 139967, CASH_ROW),
  ...pair('CFO.STATEMENT', 'cfo', 192113, 178703, CFO_ROW),
  ...pair('EBITDA.REPORTED', 'ebitda', 207911, 183422, EBITDA_ROW),
];

const YEAR = { from: '2025-03-31', to: '2026-03-31' };

test('a March year-end means an April-to-March year', () => {
  const span = periodOf(fact({ period_end: '2026-03-31' }));
  assert.equal(new Date(span.start).toISOString().slice(0, 10), '2025-04-01');
  assert.equal(span.days, 365);
  assert.equal(span.stated_start, false);
});

test('a fact that states its own start is believed over the arithmetic', () => {
  // CONSTRUCTED: a 52/53-week retail year is not twelve months, and an issuer
  // reporting one should say so rather than have this guess.
  const span = periodOf(fact({ period_end: '2026-01-31', period_start: '2025-02-02' }));
  assert.equal(span.stated_start, true);
  // 364 days, not 365. A 52-week year is a week, not a twelfth, short.
  assert.equal(span.days, 364);
  assert.equal(MONTHS_IN.quarter, 3);
});

test('two year-ends nine months apart are offset, not comparable or incomparable', () => {
  // CONSTRUCTED period ends: Reliance ends in March, a December filer in
  // December. Neither aligned nor useless - the number is what lets a reader
  // decide which questions survive the gap.
  const check = comparable(fact({ period_end: '2026-03-31' }), fact({ period_end: '2025-12-31' }));
  assert.equal(check.status, 'offset');
  assert.equal(check.overlap.days, 275);
  assert.equal(check.overlap.share_of_shorter, 0.753425);
  assert.equal(Math.abs(check.offset_months), 3);
});

test('two March year-ends are aligned', () => {
  const check = comparable(fact({ period_end: '2026-03-31' }), fact({ period_end: '2026-03-31' }));
  assert.equal(check.status, 'aligned');
  assert.equal(check.overlap.share_of_shorter, 1);
});

test('periods of different length are never put side by side', () => {
  const check = comparable(fact({ period_end: '2026-03-31' }),
    fact({ period_end: '2026-03-31', period_type: 'quarter' }));
  assert.equal(check.status, 'different_length');
  assert.equal(check.reason, 'annual against quarter');
});

test('periods that barely meet are not comparable', () => {
  const check = comparable(fact({ period_end: '2026-03-31' }), fact({ period_end: '2024-12-31' }));
  assert.equal(check.status, 'not_comparable');
  assert.equal(check.overlap.days, 0);
});

test('the direction of the trend depends on which capex you mean', () => {
  // The finding this module exists for. One company, one year, two disclosed
  // definitions of capital expenditure, opposite signs.
  const management = changeIn({ facts: FACTS, definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  const cash = changeIn({ facts: FACTS, definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', ...YEAR });
  assert.equal(management.change, 13164);
  assert.equal(management.growth, 0.100407);
  assert.equal(cash.change, -17051);
  assert.equal(cash.growth, -0.121822);
});

test('both years come from one document when one document gives both', () => {
  const change = changeIn({ facts: FACTS, definition_id: 'CFO.STATEMENT', ...YEAR });
  assert.equal(change.status, 'measured');
  assert.equal(change.basis, 'same_document');
  assert.equal(change.document, RELIANCE);
  assert.equal(change.growth, 0.075041);
  assert.deepEqual(change.caveats, []);
});

test("the computed growth agrees with the growth the issuer states", () => {
  // Reliance says EBITDA expanded "13.4% Y-o-Y". 2,07,911 over 1,83,422 is
  // 13.3512%, which is the same claim to the precision it was made at.
  const change = changeIn({
    facts: FACTS, definition_id: 'EBITDA.REPORTED', ...YEAR,
    stated: { value: 0.134, source_sentence: 'EBITDA for FY 2025-26 was at  H   2,07,911 crore (US$ 21.9 billion), expanding 13.4% Y-o-Y' },
  });
  assert.equal(change.growth, 0.133512);
  assert.equal(change.also_stated.value, 0.134);
  assert.equal(change.also_stated.within_rounding, true);
});

test('two periods from two documents are measured, and said to be', () => {
  // CONSTRUCTED: the prior year taken from last year's report instead of from
  // this year's comparative.
  const split = [
    FACTS[0],
    { ...FACTS[1], reported_in_document: LAST_YEAR },
  ];
  const change = changeIn({ facts: split, definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  assert.equal(change.status, 'measured');
  assert.equal(change.basis, 'across_documents');
  assert.match(change.caveats[0], /RIL FY2024-25/);
  assert.match(change.caveats[0], /restated comparative would show here as growth/);
});

test('documents that disagree about both years do not produce a growth rate', () => {
  // CONSTRUCTED: a later report restates the prior year. The difference
  // between 1,31,107 and 1,29,000 is a restatement, not growth, and returning
  // a percentage here would present one as the other.
  const restating = [
    ...FACTS.slice(0, 2),
    { ...FACTS[0], reported_in_document: 'RIL FY2026-27' },
    { ...FACTS[1], value: 129000, reported_in_document: 'RIL FY2026-27' },
  ];
  const change = changeIn({ facts: restating, definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  assert.equal(change.status, 'restated');
  assert.equal(change.growth, undefined);
  assert.equal(change.reported_in.length, 2);
});

test('a period reported twice with no document covering both is refused', () => {
  // CONSTRUCTED.
  const scattered = [
    { ...FACTS[0], reported_in_document: 'A' },
    { ...FACTS[1], reported_in_document: 'B' },
    { ...FACTS[1], value: 130000, reported_in_document: 'C' },
  ];
  const change = changeIn({ facts: scattered, definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  assert.equal(change.status, 'restated');
  assert.match(change.reason, /none reports both/);
});

test('overlapping periods are not a year-on-year change', () => {
  // CONSTRUCTED: an annual figure to September against an annual figure to
  // March shares six months, and the difference is not growth.
  const overlapping = [FACTS[0], { ...FACTS[1], period_end: '2025-09-30' }];
  const change = changeIn({ facts: overlapping, definition_id: 'CAPEX.MANAGEMENT', from: '2025-09-30', to: '2026-03-31' });
  assert.equal(change.status, 'overlapping_periods');
  assert.match(change.reason, /share 183 days/);
});

test('a quarter is not compared with a year', () => {
  // CONSTRUCTED.
  const mixed = [FACTS[0], { ...FACTS[1], period_type: 'quarter' }];
  const change = changeIn({ facts: mixed, definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  assert.equal(change.status, 'different_length');
});

test('growth from a base of zero is not reported, but the change is', () => {
  // CONSTRUCTED.
  const fromZero = [FACTS[0], { ...FACTS[1], value: 0 }];
  const change = changeIn({ facts: fromZero, definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  assert.equal(change.change, 144271);
  assert.equal(change.growth, null);
  assert.match(change.caveats[0], /not reported from a base of 0/);
});

test('figures in different money are not differenced', () => {
  // CONSTRUCTED: the dollar equivalent printed beside the rupee figure.
  const mixed = [FACTS[0], { ...FACTS[1], currency: 'USD', unit: 1000000, value: 15200 }];
  const change = changeIn({ facts: mixed, definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  assert.equal(change.status, 'not_comparable');
});

test('a missing period is a stated absence', () => {
  const change = changeIn({ facts: [FACTS[0]], definition_id: 'CAPEX.MANAGEMENT', ...YEAR });
  assert.equal(change.status, 'insufficient_data');
  assert.match(change.reason, /2025-03-31/);
});

test('nothing published after the date is visible on it', () => {
  const documents = { [RELIANCE]: '2026-06-20', [LAST_YEAR]: '2025-06-18' };
  const earlier = [{ ...FACTS[1], reported_in_document: LAST_YEAR }];
  const { facts, excluded } = asOf([...FACTS, ...earlier], { on: '2026-01-01', documents });
  assert.equal(facts.length, 1);
  assert.equal(facts[0].reported_in_document, LAST_YEAR);
  assert.equal(excluded.length, 8);
  assert.match(excluded[0].reason, /published 2026-06-20/);
});

test('a document with no known publication date is excluded, not assumed', () => {
  // Defaulting the unknown case to "include" is exactly how look-ahead gets
  // in: it asserts the filing existed when that is the question being asked.
  const { facts, excluded } = asOf(FACTS, { on: '2030-01-01', documents: {} });
  assert.deepEqual(facts, []);
  assert.equal(excluded.length, FACTS.length);
  assert.match(excluded[0].reason, /publication date of RIL FY2025-26 is unknown/);
});

test('a document published on the day is visible that day', () => {
  const { facts } = asOf(FACTS, { on: '2026-06-20', documents: { [RELIANCE]: '2026-06-20' } });
  assert.equal(facts.length, FACTS.length);
});

test('a series runs oldest first and carries every step', () => {
  const series = seriesOf({ facts: FACTS, definition_id: 'CAPEX.CASH_PPE_INTANGIBLES' });
  assert.deepEqual(series.period_ends, ['2025-03-31', '2026-03-31']);
  assert.equal(series.steps.length, 1);
  assert.equal(series.steps[0].growth, -0.121822);
});

test('reading periods never alters the facts it was given', () => {
  const before = JSON.stringify(FACTS);
  seriesOf({ facts: FACTS, definition_id: 'CAPEX.MANAGEMENT' });
  asOf(FACTS, { on: '2026-06-20', documents: { [RELIANCE]: '2026-06-20' } });
  assert.equal(JSON.stringify(FACTS), before);
});
