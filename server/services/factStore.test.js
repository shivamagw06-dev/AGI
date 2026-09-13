import test from 'node:test';
import assert from 'node:assert/strict';
import {
  COLUMNS, IDENTITY, PAGE, TABLE, documentsFor, fromRow, loadFacts, saveFacts, toRow, unwritable,
} from './factStore.js';

/**
 * A stand-in for PostgREST that reproduces the behaviour worth testing: a
 * select with no range returns a thousand rows and says nothing about the rest.
 * It is not PostgREST, and it proves the query this code builds rather than
 * the database's response to it.
 */
function fakeClient(rows, { error = null, cap = PAGE } = {}) {
  const calls = { upserts: [], selects: [] };
  return {
    calls,
    from(table) {
      const state = { table, filters: [], range: null, order: [] };
      const builder = {
        select() { state.select = '*'; return builder; },
        eq(column, value) { state.filters.push(['eq', column, value]); return builder; },
        in(column, value) { state.filters.push(['in', column, value]); return builder; },
        order(column, options) { state.order.push([column, options]); return builder; },
        range(from, to) { state.range = [from, to]; return builder; },
        upsert(batch, options) {
          calls.upserts.push({ table, batch, options });
          return Promise.resolve({ data: batch, error });
        },
        then(resolve, reject) {
          calls.selects.push(state);
          if (error) return Promise.resolve({ data: null, error }).then(resolve, reject);
          let matched = rows.filter((row) => state.filters.every(([kind, column, value]) => (
            kind === 'in' ? value.includes(row[column]) : row[column] === value)));
          matched = state.range
            ? matched.slice(state.range[0], state.range[1] + 1)
            : matched.slice(0, cap);
          return Promise.resolve({ data: matched, error: null }).then(resolve, reject);
        },
      };
      return builder;
    },
  };
}

/** Reliance Industries' Integrated Annual Report 2025-26. */
const RELIANCE = 'RIL FY2025-26';
const capex = {
  company: 'RELIANCE', period_end: '2026-03-31', period_type: 'annual',
  accounting_scope: 'consolidated', entity_scope: 'group', concept: 'capex',
  definition_id: 'CAPEX.CASH_PPE_INTANGIBLES', measurement_basis: 'cash',
  segment: null, geography: null, dimensions: {}, currency: 'INR', unit: 10000000,
  reported_in_document: RELIANCE, value: 122916, verdict: 'stated',
  as_reported_label: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets',
  source_sentence: 'Expenditure for Property, Plant and Equipment, Spectrum and Other Intangible Assets   (1,22,916)   (1,39,967)',
};

test('a row carries every column whether the caller filled it or not', () => {
  // An upsert row that omits a key writes NULL over it rather than inheriting
  // the column default, so the shape is fixed regardless of the input.
  assert.deepEqual(Object.keys(toRow({})).sort(), [...COLUMNS].sort());
  assert.deepEqual(Object.keys(toRow(capex)).sort(), [...COLUMNS].sort());
});

test('a figure that is not segmental is stored as empty, not as null', () => {
  // The identity index is the upsert conflict target and has to be over plain
  // columns, so "not segmental" is '' in the table and null in memory.
  const row = toRow(capex);
  assert.equal(row.segment, '');
  assert.equal(row.geography, '');
  assert.equal(fromRow(row).segment, null);
  assert.equal(fromRow(row).geography, null);
  assert.equal(fromRow(toRow({ ...capex, segment: 'Retail' })).segment, 'Retail');
});

test('a row comes back with numbers rather than numeric strings', () => {
  const read = fromRow({ ...toRow(capex), value: '122916', unit: '10000000' });
  assert.equal(read.value, 122916);
  assert.equal(read.unit, 10000000);
  assert.equal(typeof read.value, 'number');
});

test('what the table would reject is named before the table sees it', () => {
  assert.deepEqual(unwritable(capex), []);
  assert.deepEqual(unwritable({ ...capex, period_type: 'quarterly' }), ['period_type quarterly']);
  assert.deepEqual(unwritable({ ...capex, measurement_basis: 'made up' }), ['measurement_basis made up']);
  assert.deepEqual(unwritable({ ...capex, verdict: 'probably' }), ['verdict probably']);
  assert.deepEqual(unwritable({ ...capex, unit: 0 }), ['unit 0']);
  assert.deepEqual(unwritable({ ...capex, entity_scope: 'division' }), ['entity_scope division']);
  assert.match(unwritable({ ...capex, company: null })[0], /company is missing/);
});

test('derived_ratio is writable, because the calculator produces it', () => {
  assert.deepEqual(unwritable({
    ...capex, concept: 'ebitda_margin', definition_id: 'EBITDA_MARGIN.ON_REVENUE_OPERATIONS_NET',
    measurement_basis: 'derived_ratio', verdict: 'derived', value: 0.08237, currency: 'INR', unit: 1,
  }), []);
});

test('one unwritable fact does not cost the others', async () => {
  const client = fakeClient([]);
  const { written, refused, error } = await saveFacts(client, [
    capex, { ...capex, period_type: 'quarterly' }, { ...capex, definition_id: 'CAPEX.MANAGEMENT', value: 144271 },
  ]);
  assert.equal(error, null);
  assert.equal(written, 2);
  assert.equal(refused.length, 1);
  assert.equal(refused[0].at, 1);
  assert.deepEqual(refused[0].problems, ['period_type quarterly']);
});

test('the conflict target is the identity index, declared once', async () => {
  const client = fakeClient([]);
  await saveFacts(client, [capex]);
  assert.equal(client.calls.upserts[0].table, TABLE);
  assert.equal(client.calls.upserts[0].options.onConflict, IDENTITY.join(','));
  assert.equal(client.calls.upserts[0].options.ignoreDuplicates, false);
  // An index and a conflict target that disagree insert duplicates instead of
  // raising anything, so they come from the same constant.
  assert.ok(IDENTITY.includes('reported_in_document'), 'a restatement must be an insert, not an overwrite');
});

test('a write larger than a chunk goes in more than one call', async () => {
  const client = fakeClient([]);
  const many = Array.from({ length: 1200 }, (_, at) => ({ ...capex, period_end: `2026-03-${String((at % 28) + 1).padStart(2, '0')}`, definition_id: `D${at}` }));
  const { written } = await saveFacts(client, many, { chunk: 500 });
  assert.equal(written, 1200);
  assert.deepEqual(client.calls.upserts.map((call) => call.batch.length), [500, 500, 200]);
});

test('a write that errors stops and says how far it got', async () => {
  const client = fakeClient([], { error: { message: 'duplicate key' } });
  const { written, error } = await saveFacts(client, [capex]);
  assert.equal(written, 0);
  assert.equal(error.message, 'duplicate key');
});

// Synthetic rows. The subject is paging, not a company.
const paging = Array.from({ length: 2500 }, (_, at) => toRow({
  ...capex, company: 'PAGING-FIXTURE', definition_id: `D${at}`, value: at,
}));

test('a read larger than the cap returns everything, not the first thousand', async () => {
  const client = fakeClient(paging);
  const { facts, complete } = await loadFacts(client, { company: 'PAGING-FIXTURE' });
  assert.equal(facts.length, 2500);
  assert.equal(complete, true);
  assert.deepEqual(client.calls.selects.map((call) => call.range), [[0, 999], [1000, 1999], [2000, 2999]]);
});

test('every read asks for a range', async () => {
  // An unbounded select comes back with a thousand rows and no indication
  // there were more, which reads as a small company rather than as an error.
  const client = fakeClient(paging);
  await loadFacts(client, { company: 'PAGING-FIXTURE' });
  assert.ok(client.calls.selects.every((call) => call.range), 'a select went out unbounded');
});

test('one company or several, one period or several', async () => {
  const client = fakeClient([toRow(capex)]);
  await loadFacts(client, { companies: ['RELIANCE', 'BERKSHIRE'], concept: 'capex', period_end: '2026-03-31' });
  const [call] = client.calls.selects;
  assert.deepEqual(call.filters, [
    ['in', 'company', ['RELIANCE', 'BERKSHIRE']],
    ['eq', 'concept', 'capex'],
    ['eq', 'period_end', '2026-03-31'],
  ]);
});

test('a segment filter finds the non-segmental rows too', async () => {
  const client = fakeClient([toRow(capex)]);
  await loadFacts(client, { company: 'RELIANCE', segment: null });
  assert.deepEqual(client.calls.selects[0].filters.at(-1), ['eq', 'segment', '']);
});

test('a read that fails says so instead of returning what it had', async () => {
  const client = fakeClient(paging, { error: { message: 'timeout' } });
  const { facts, error, complete } = await loadFacts(client, { company: 'PAGING-FIXTURE' });
  assert.equal(error.message, 'timeout');
  assert.equal(complete, false);
  assert.deepEqual(facts, []);
});

test('documents are listed newest period first', async () => {
  const client = fakeClient([
    toRow(capex),
    toRow({ ...capex, period_end: '2025-03-31', reported_in_document: 'RIL FY2024-25', value: 139967 }),
    toRow({ ...capex, definition_id: 'CAPEX.MANAGEMENT', value: 144271 }),
  ]);
  const { documents } = await documentsFor(client, 'RELIANCE');
  assert.deepEqual(documents, [
    { document: RELIANCE, facts: 2, latest_period: '2026-03-31' },
    { document: 'RIL FY2024-25', facts: 1, latest_period: '2025-03-31' },
  ]);
});

test('a limit smaller than a page is still a limit', async () => {
  // Checked before the short-page exit, or a result smaller than one page
  // returns more rows than the caller asked for.
  const client = fakeClient(paging.slice(0, 3));
  const { facts, complete } = await loadFacts(client, { company: 'PAGING-FIXTURE', limit: 1 });
  assert.equal(facts.length, 1);
  // A limited read is never complete: complete means every matching fact.
  assert.equal(complete, false);
});
