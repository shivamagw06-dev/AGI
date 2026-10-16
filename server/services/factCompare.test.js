import test from 'node:test';
import assert from 'node:assert/strict';
import { compare, compareAcross, latestPeriods, rankCompanies } from './factCompare.js';
import { toRow } from './factStore.js';

/**
 * Reliance's figures are from its Integrated Annual Report 2025-26. The other
 * companies are CONSTRUCTED: this file is about what happens when five issuers
 * answer the same question differently, and inventing a second issuer's
 * accounts to demonstrate that would be the thing the system exists to stop.
 * Their names say what they are.
 */
const PERIOD = '2026-03-31';

const fact = (over) => ({
  period_type: 'annual', accounting_scope: 'consolidated', entity_scope: 'group',
  concept: 'capex', segment: null, geography: null, dimensions: {}, verdict: 'stated',
  currency: 'INR', unit: 10000000, ...over,
});

const RELIANCE = [
  fact({ company: 'RELIANCE', period_end: PERIOD, definition_id: 'CAPEX.MANAGEMENT',
    measurement_basis: 'accrual', value: 144271, reported_in_document: 'RIL FY2025-26',
    as_reported_label: 'capital expenditure',
    source_sentence: 'RIL’s capital expenditure for FY 2025-26 stood at H 1,44,271 crore (US$ 15.2 billion) as compared to H 1,31,107 crore in the previous financial year.' }),
  fact({ company: 'RELIANCE', period_end: PERIOD, definition_id: 'CAPEX.CASH_PPE_INTANGIBLES',
    measurement_basis: 'cash', value: 122916, reported_in_document: 'RIL FY2025-26',
    as_reported_label: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets',
    source_sentence: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets   (1,22,916)   (1,39,967)' }),
];

// CONSTRUCTED: an issuer with a March year-end that discloses cash capex only.
const SAME_YEAR_END = [
  fact({ company: 'CONSTRUCTED-MARCH-FILER', period_end: PERIOD,
    definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash', value: 40000,
    reported_in_document: 'MARCH FY2025-26', as_reported_label: 'Purchase of fixed assets',
    source_sentence: 'Purchase of fixed assets (40,000)' }),
];

// CONSTRUCTED: a December year-end, nine months overlapping.
const DECEMBER_FILER = [
  fact({ company: 'CONSTRUCTED-DECEMBER-FILER', period_end: '2025-12-31',
    definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash', value: 60000,
    reported_in_document: 'DEC CY2025', as_reported_label: 'Capital expenditures',
    source_sentence: 'Capital expenditures (60,000)' }),
];

// CONSTRUCTED: reports in dollar millions rather than rupee crore.
const DOLLAR_FILER = [
  fact({ company: 'CONSTRUCTED-DOLLAR-FILER', period_end: PERIOD, currency: 'USD', unit: 1000000,
    definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash', value: 9000,
    reported_in_document: 'USD FY2026', as_reported_label: 'Capital expenditures',
    source_sentence: 'Capital expenditures (9,000)' }),
];

const cash = { concept: 'capex', purpose: 'cash_basis' };

test('the latest period is found per company, not across them', () => {
  const latest = latestPeriods([...RELIANCE, ...DECEMBER_FILER], 'capex');
  assert.equal(latest.get('RELIANCE'), PERIOD);
  assert.equal(latest.get('CONSTRUCTED-DECEMBER-FILER'), '2025-12-31');
});

test('a comparable pair of companies is usable and says which definitions it used', () => {
  const table = compare({ facts: [...RELIANCE, ...SAME_YEAR_END], ...cash });
  assert.equal(table.usable, true);
  assert.deepEqual(table.rows.map((row) => [row.company, row.value, row.definition_id]), [
    ['CONSTRUCTED-MARCH-FILER', 40000, 'CAPEX.CASH_PPE_INTANGIBLES'],
    ['RELIANCE', 122916, 'CAPEX.CASH_PPE_INTANGIBLES'],
  ]);
  // Reliance discloses capex two ways. The column says which one it took, and
  // what taking it gave up.
  const reliance = table.rows.find((row) => row.company === 'RELIANCE');
  assert.match(reliance.rule, /cash calculation takes cash measurements/);
  assert.equal(reliance.forgone[0].definition_id, 'CAPEX.MANAGEMENT');
  assert.equal(reliance.forgone[0].as_share_of_chosen, -0.173737);
});

test('year-ends nine months apart block the comparison and say by how much', () => {
  const table = compare({ facts: [...RELIANCE, ...DECEMBER_FILER], ...cash });
  assert.equal(table.usable, false);
  assert.equal(table.comparability[0].status, 'offset');
  assert.equal(table.comparability[0].overlap.days, 275);
  assert.ok(table.blockers.some((row) => /3 months apart/.test(row.why)));
});

test('currencies are reported, never converted', () => {
  // Turning rupee crore into dollar millions needs a rate on a date. There
  // isn't one, and inventing one would put a fabricated number in the middle
  // of a comparison that looks like arithmetic.
  const table = compare({ facts: [...RELIANCE, ...DOLLAR_FILER], ...cash });
  assert.equal(table.usable, false);
  assert.ok(table.blockers.some((row) => /different currencies or units and are not converted/.test(row.why)));
  const dollars = table.rows.find((row) => row.company === 'CONSTRUCTED-DOLLAR-FILER');
  assert.equal(dollars.value, 9000);
  assert.equal(dollars.currency, 'USD');
  assert.equal(dollars.unit, 1000000);
});

test('a company that did not disclose it appears as a row, not as a gap', () => {
  const table = compare({ facts: [...RELIANCE], companies: ['RELIANCE', 'CONSTRUCTED-SILENT-FILER'], ...cash });
  const silent = table.rows.find((row) => row.company === 'CONSTRUCTED-SILENT-FILER');
  assert.equal(silent.status, 'not_disclosed');
  assert.equal(silent.value, null);
  assert.equal(table.usable, false);
});

test('a company whose definitions the purpose cannot separate blocks the column', () => {
  // CONSTRUCTED: two statutory revenues, which no rule about measurement can
  // choose between.
  const twoRevenues = ['REVENUE.VALUE_OF_SALES_AND_SERVICES', 'REVENUE.TOTAL_INCOME']
    .map((definition_id, at) => fact({ company: 'CONSTRUCTED-TWO-REVENUES', period_end: PERIOD,
      concept: 'revenue', definition_id, measurement_basis: 'statutory',
      value: [1175919, 1104637][at], reported_in_document: 'DOC', source_sentence: 'x' }));
  const table = compare({ facts: twoRevenues, concept: 'revenue', purpose: 'statutory_basis' });
  assert.equal(table.rows[0].status, 'needs_a_definition');
  assert.equal(table.rows[0].candidates.length, 2);
  assert.equal(table.usable, false);
});

test('naming the definition unblocks it', () => {
  const twoRevenues = ['REVENUE.VALUE_OF_SALES_AND_SERVICES', 'REVENUE.TOTAL_INCOME']
    .map((definition_id, at) => fact({ company: 'CONSTRUCTED-TWO-REVENUES', period_end: PERIOD,
      concept: 'revenue', definition_id, measurement_basis: 'statutory',
      value: [1175919, 1104637][at], reported_in_document: 'DOC', source_sentence: 'x' }));
  const table = compare({ facts: twoRevenues, concept: 'revenue', purpose: 'statutory_basis',
    prefer: { revenue: 'REVENUE.TOTAL_INCOME' } });
  assert.equal(table.usable, true);
  assert.equal(table.rows[0].value, 1104637);
  assert.equal(table.rows[0].rule, 'named by the caller');
});

test('a substituted basis blocks the column and names the substitution', () => {
  // CONSTRUCTED: an issuer disclosing capex only on an accrual basis, in a
  // cash comparison.
  const accrualOnly = [fact({ company: 'CONSTRUCTED-ACCRUAL-ONLY', period_end: PERIOD,
    definition_id: 'CAPEX.MANAGEMENT', measurement_basis: 'accrual', value: 50000,
    reported_in_document: 'DOC', source_sentence: '50,000' })];
  const table = compare({ facts: [...SAME_YEAR_END, ...accrualOnly], ...cash });
  assert.equal(table.usable, false);
  assert.ok(table.blockers.some((row) => /is measured accrual, which is not the same thing/.test(row.why)));
});

test('an ordering over figures that are not comparable is withheld, not qualified', () => {
  // The thing a reader is most likely to act on and least likely to check.
  const table = compare({ facts: [...RELIANCE, ...DOLLAR_FILER], ...cash });
  const ranked = rankCompanies(table);
  assert.equal(ranked.ordered, null);
  assert.equal(ranked.withheld, true);
  assert.ok(ranked.blockers.length > 0);
});

test('an ordering over comparable figures is given', () => {
  const table = compare({ facts: [...RELIANCE, ...SAME_YEAR_END], ...cash });
  const ranked = rankCompanies(table);
  assert.equal(ranked.withheld, false);
  assert.deepEqual(ranked.ordered.map((row) => [row.position, row.company, row.value]), [
    [1, 'RELIANCE', 122916],
    [2, 'CONSTRUCTED-MARCH-FILER', 40000],
  ]);
});

test('a read that did not finish makes the comparison unusable', async () => {
  // A truncated read looks exactly like a company with fewer disclosures.
  const rows = [...RELIANCE, ...SAME_YEAR_END].map(toRow);
  const client = {
    from() {
      const builder = {
        select() { return builder; }, eq() { return builder; }, in() { return builder; },
        order() { return builder; }, range() { return builder; },
        then(resolve) { return Promise.resolve({ data: null, error: { message: 'timeout' } }).then(resolve); },
      };
      return builder;
    },
  };
  const { error, comparison } = await compareAcross(client, { concept: 'capex', purpose: 'cash_basis' });
  assert.equal(error.message, 'timeout');
  assert.equal(comparison, null);
  assert.ok(rows.length > 0);
});

test('a read that stopped short makes the comparison unusable', async () => {
  // A truncated read looks exactly like a company with fewer disclosures, so
  // the comparison is marked rather than quietly built on what arrived.
  // The facts below would compare cleanly: two March year-ends, one cash
  // definition each, one currency. Only the truncation makes it unusable, so
  // nothing else can be what the assertion is reading.
  const rows = [...SAME_YEAR_END, ...SAME_YEAR_END.map((row) => ({
    ...row, company: 'CONSTRUCTED-SECOND-MARCH-FILER', value: 55000,
  }))].map(toRow);
  const client = {
    from() {
      const builder = {
        select() { return builder; }, eq() { return builder; }, in() { return builder; },
        order() { return builder; }, range() { return builder; },
        then(resolve) { return Promise.resolve({ data: rows, error: null }).then(resolve); },
      };
      return builder;
    },
  };
  const whole = await compareAcross(client, { concept: 'capex', purpose: 'cash_basis' });
  assert.equal(whole.comparison.usable, true);
  const { comparison } = await compareAcross(client, { concept: 'capex', purpose: 'cash_basis', limit: 1 });
  assert.equal(comparison.usable, false);
  assert.ok(comparison.blockers.some((row) => /did not return every matching fact/.test(row.why)));
});

test('comparing never alters the facts it was given', () => {
  const facts = [...RELIANCE, ...SAME_YEAR_END];
  const before = JSON.stringify(facts);
  rankCompanies(compare({ facts, ...cash }));
  assert.equal(JSON.stringify(facts), before);
});
