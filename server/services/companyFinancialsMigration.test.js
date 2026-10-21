import test from 'node:test';
import assert from 'node:assert/strict';
import { LINE_ITEMS } from './companyFinancialsImport.js';
import { DEFINITIONS, isUnrecorded } from './factOntology.js';
import { unwritable } from './factStore.js';
import { reconcileFamily, reconcileFor } from './factReconciliation.js';
import {
  COLUMN_DEFINITIONS, SOURCE, SOURCE_RESTATED, factsFromRow, summarise,
} from './companyFinancialsMigration.js';

/**
 * Figures are Reliance's, from the Integrated Annual Report 2025-26, arranged
 * as company_financials would have held them - which is the point of these
 * tests: that shape cannot say which capex 1,44,271 is.
 */
const row = {
  ticker: 'RELIANCE', period_end: '2026-03-31', period_type: 'annual', basis: 'consolidated',
  currency: 'INR', scale: 10000000, restated: false,
  revenue: 1175919, ebitda: 207911, ebit: 139828, capex: 144271,
  operating_cash_flow: 192113, gross_debt: 374421, net_income: 80775,
  receivables: null, share_count: 1353,
};

test('every column the old store can hold becomes a fact', () => {
  // A column with no mapping is data the migration would drop in silence.
  const unmapped = LINE_ITEMS.filter((column) => !COLUMN_DEFINITIONS.has(column));
  assert.deepEqual(unmapped, []);
});

test('every definition the mapping names is in the register', () => {
  for (const [column, definition_id] of COLUMN_DEFINITIONS) {
    assert.ok(DEFINITIONS.has(definition_id), `${column} maps to unknown ${definition_id}`);
  }
});

test('a blank column is not a zero', () => {
  const { facts } = factsFromRow(row);
  assert.equal(facts.some((fact) => fact.concept === 'receivables'), false);
  assert.equal(facts.length, 8);
});

test('a column that named one definition keeps it', () => {
  const { facts } = factsFromRow(row);
  const cfo = facts.find((fact) => fact.concept === 'cfo');
  assert.equal(cfo.definition_id, 'CFO.STATEMENT');
  assert.equal(isUnrecorded(cfo.definition_id), false);
  assert.equal(cfo.value, 192113);
});

test('a column that named three keeps none of them', () => {
  // 1,44,271 is management's capex in Reliance's report and the segment note's
  // total, and the cash flow statement says 1,22,916. A column called capex
  // cannot hold that, and nothing in the row says which one was entered.
  const { facts } = factsFromRow(row);
  const capex = facts.find((fact) => fact.concept === 'capex');
  assert.equal(capex.definition_id, 'CAPEX.UNRECORDED');
  assert.equal(capex.measurement_basis, 'unrecorded');
  assert.equal(capex.value, 144271);
});

test('a basis every definition shares survives; one they do not share does not', () => {
  const { facts } = factsFromRow(row);
  // All three revenue definitions are statutory, so only which is unknown.
  assert.equal(facts.find((fact) => fact.concept === 'revenue').measurement_basis, 'statutory');
  // EBIT spans the segment note, management and the statutory accounts.
  assert.equal(facts.find((fact) => fact.concept === 'ebit').measurement_basis, 'unrecorded');
});

test('the column name is the label, because the issuer’s words are gone', () => {
  const { facts } = factsFromRow(row);
  assert.equal(facts.find((fact) => fact.concept === 'capex').as_reported_label, 'capex');
  assert.equal(facts.find((fact) => fact.concept === 'capex').source_sentence, null);
});

test('a count sheds the currency the row carried', () => {
  const { facts } = factsFromRow(row);
  const shares = facts.find((fact) => fact.concept === 'share_count');
  assert.equal(shares.currency, null);
  assert.equal(shares.unit, 10000000);
});

test('a restated row is a different document, so both survive', () => {
  const original = factsFromRow(row).facts.find((fact) => fact.concept === 'revenue');
  const restated = factsFromRow({ ...row, restated: true, revenue: 1170000 })
    .facts.find((fact) => fact.concept === 'revenue');
  assert.equal(original.reported_in_document, SOURCE);
  assert.equal(restated.reported_in_document, SOURCE_RESTATED);
  assert.equal(original.original_or_restated, 'original');
  assert.equal(restated.original_or_restated, 'restated');
});

test('every fact the migration makes can actually be written', () => {
  const { facts } = factsFromRow(row);
  for (const fact of facts) {
    assert.deepEqual(unwritable(fact), [], `${fact.definition_id} would be refused`);
  }
});

test('a row missing what the store requires produces nothing and says why', () => {
  assert.deepEqual(factsFromRow({ ...row, scale: 0 }).problems, ['scale 0']);
  assert.deepEqual(factsFromRow({ ...row, currency: '' }).problems, ['no currency']);
  assert.deepEqual(factsFromRow({ ...row, period_type: 'yearly' }).problems, ['period_type yearly']);
  assert.deepEqual(factsFromRow({ ...row, scale: 0 }).facts, []);
});

test('a ticker becomes the company unless one is named', () => {
  assert.equal(factsFromRow(row).facts[0].company, 'RELIANCE');
  assert.equal(factsFromRow(row, { company: 'Reliance Industries' }).facts[0].company, 'Reliance Industries');
});

test('a migrated figure is never presented as a clean answer', () => {
  // The quiet case: one revenue, nothing to reconcile it against, and a
  // purpose that admits its basis. Without a caveat this reads exactly like a
  // figure whose definition is known.
  const { facts } = factsFromRow(row);
  const picked = reconcileFamily({
    facts, concept: 'revenue', period_end: '2026-03-31', purpose: 'statutory_basis',
  });
  assert.equal(picked.status, 'only_one_observation');
  assert.equal(picked.unrecorded, true);
  assert.match(picked.caveats[0], /recorded a figure but not which definition it is/);
});

test('a set containing an unrecorded figure is not coherent', () => {
  // Only the revenue, so nothing else can be what makes the set incoherent:
  // it resolves at first preference, with no substitution and nothing
  // unresolved. The definition being unknown is the whole of the problem.
  const { facts } = factsFromRow({
    ticker: 'RELIANCE', period_end: '2026-03-31', period_type: 'annual', basis: 'consolidated',
    currency: 'INR', scale: 10000000, restated: false, revenue: 1175919,
  });
  assert.equal(facts.length, 1);
  const across = reconcileFor({ facts, purpose: 'statutory_basis', period_end: '2026-03-31' });
  assert.deepEqual(across.coherence.substituted, []);
  assert.deepEqual(across.coherence.unresolved, []);
  assert.deepEqual(across.coherence.unrecorded, [
    { concept: 'revenue', definition_id: 'REVENUE.UNRECORDED' },
  ]);
  assert.equal(across.coherence.coherent, false);
});

test('a set of figures that do know what they are is coherent', () => {
  // The same shape with the one column the old store could not confuse.
  const { facts } = factsFromRow({
    ticker: 'RELIANCE', period_end: '2026-03-31', period_type: 'annual', basis: 'consolidated',
    currency: 'INR', scale: 10000000, restated: false, operating_cash_flow: 192113,
  });
  const across = reconcileFor({ facts, purpose: 'cash_basis', period_end: '2026-03-31' });
  assert.equal(across.coherence.coherent, true);
  assert.deepEqual(across.coherence.unrecorded, []);
});

test('an unrecorded basis cannot be selected at all', () => {
  // Capex is the case where the basis itself is unknown, so no cash
  // calculation can use it however willing the caller is.
  const { facts } = factsFromRow(row);
  const picked = reconcileFamily({
    facts, concept: 'capex', period_end: '2026-03-31', purpose: 'cash_basis',
  });
  assert.equal(picked.status, 'no_fit');
  assert.equal(picked.chosen, null);
  assert.match(picked.reason, /measured unrecorded/);
});

test('the summary reports what share arrives without a definition', () => {
  const plan = summarise([row, { ...row, period_end: '2025-03-31' }]);
  assert.equal(plan.rows, 2);
  assert.equal(plan.facts, 16);
  // Seven of the eight facts per row come from columns that named more than
  // one definition. Only the operating cash flow arrives knowing what it is.
  // That proportion is the thing to read before writing any of this.
  assert.equal(plan.unrecorded, 14);
  assert.equal(plan.unrecorded_share, 0.875);
});

test('the summary names rows that would produce nothing', () => {
  const plan = summarise([row, { ...row, currency: '' }]);
  assert.deepEqual(plan.problems, ['row 2: no currency']);
});
