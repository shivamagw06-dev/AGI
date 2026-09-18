import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DASHBOARD_CONCEPTS, FUNDAMENTAL_STATE, definitionsFor, factStoreKeyFor,
  fundamentalsFor, fundamentalsForUniverse, intensityForUniverse, intensityFrom, resolveFromStore,
  withFactStoreKeys,
} from './aiEnablersFundamentals.js';

const fact = (definition_id, period_end, value, extra = {}) => ({
  company: 'KAYNES', definition_id, period_end, value,
  period_type: 'fiscal_year', accounting_scope: 'consolidated', entity_scope: 'group',
  segment: null, geography: null, dimensions: null,
  reported_in_document: 'AR FY26', verdict: 'stated',
  currency: 'INR', unit: 'crore',
  source_document_id: 'kaynes-ar-fy26', source_page: 142,
  source_sentence: 'Capital expenditure for the year was Rs 473 crore.',
  as_reported_label: 'Capital expenditure', ...extra,
});

/** A fake PostgREST client: loadFacts pages against .range(). */
const clientWith = (rowsByCompany) => ({
  from: () => {
    const state = { company: null };
    const builder = {
      select: () => builder,
      eq: (column, value) => { if (column === 'company') state.company = value; return builder; },
      order: () => builder,
      range: async () => ({ data: rowsByCompany[state.company] || [], error: null }),
    };
    return builder;
  },
});

test('an un-ingested company is NOT_INGESTED, never NOT_DISCLOSED', () => {
  // The distinction the module exists for. resolveConcept() in the store
  // would answer "places in the filing were searched and none disclosed it"
  // about a filing nobody has opened, which on a dashboard reads as "this
  // company discloses no capex".
  const resolved = resolveFromStore({ facts: [], concept: 'capex', period_end: '2026-03-31' });
  assert.equal(resolved.state, FUNDAMENTAL_STATE.NOT_INGESTED);
  assert.equal(resolved.value, null);
  assert.match(resolved.reason, /no filing has been ingested/);
});

test('a company with filings but no capex row is NOT_DISCLOSED', () => {
  const resolved = resolveFromStore({
    facts: [fact('REVENUE.OPERATIONS_NET', '2026-03-31', 3_000)],
    concept: 'capex', period_end: '2026-03-31',
  });
  assert.equal(resolved.state, FUNDAMENTAL_STATE.NOT_DISCLOSED);
  assert.match(resolved.reason, /none of them measure capex/);
});

test('a stated figure carries its citation through to the caller', () => {
  const resolved = resolveFromStore({
    facts: [fact('CAPEX.MANAGEMENT', '2026-03-31', 473)],
    concept: 'capex', period_end: '2026-03-31',
  });
  assert.equal(resolved.state, FUNDAMENTAL_STATE.FOUND);
  assert.equal(resolved.value, 473);
  assert.equal(resolved.citations[0].source_page, 142);
  assert.match(resolved.citations[0].source_sentence, /Rs 473 crore/);
  assert.equal(resolved.citations[0].as_reported_label, 'Capital expenditure');
});

test('every disclosed definition of a concept is returned, not just one', () => {
  // Management capex and cash capex are both real and usually differ. The
  // page has to show which is which rather than picking one and labelling it
  // "capex", which is how a number becomes unarguable-with.
  const resolved = resolveFromStore({
    facts: [
      fact('CAPEX.MANAGEMENT', '2026-03-31', 473),
      fact('CAPEX.CASH_PPE_INTANGIBLES', '2026-03-31', 431),
    ],
    concept: 'capex', period_end: '2026-03-31',
  });
  assert.equal(resolved.definitions.length, 2);
  assert.deepEqual(resolved.definitions.map((one) => one.value), [473, 431]);
  assert.match(resolved.definitions[0].label, /management reports it/);
});

test('a derived figure comes back with its lineage', () => {
  // Nothing states FCF; it is cfo minus capex. The dashboard must be able to
  // open that, which is the whole point of putting the fact store behind it.
  const resolved = resolveFromStore({
    facts: [
      fact('CFO.STATEMENT', '2026-03-31', 900),
      fact('CAPEX.CASH_PPE_INTANGIBLES', '2026-03-31', 431),
    ],
    concept: 'fcf', period_end: '2026-03-31',
  });
  assert.equal(resolved.state, FUNDAMENTAL_STATE.DERIVED);
  assert.equal(resolved.value, 469);
  assert.equal(resolved.lineage.formula, 'cfo - capex');
  assert.equal(resolved.lineage.inputs.cfo.value, 900);
  assert.equal(resolved.lineage.inputs.capex.value, 431);
  assert.match(resolved.lineage.inputs.capex.source_sentence, /473 crore/);
});

test('a period with no facts is not answered from another period', () => {
  const resolved = resolveFromStore({
    facts: [fact('CAPEX.MANAGEMENT', '2025-03-31', 300)],
    concept: 'capex', period_end: '2026-03-31',
  });
  assert.equal(resolved.state, FUNDAMENTAL_STATE.NOT_DISCLOSED);
  assert.equal(resolved.value, null);
});

test('a member with no declared fact-store key is unmapped, not empty', async () => {
  // NSE symbols and the store's company keys are different namespaces.
  // Falling back to the symbol would attach whatever happened to match.
  const result = await fundamentalsFor(clientWith({}), { symbol: 'KAYNES' }, { period_end: '2026-03-31' });
  assert.equal(result.unmapped, true);
  assert.equal(result.company, null);
  assert.equal(result.concepts.capex.state, FUNDAMENTAL_STATE.NOT_INGESTED);
  assert.match(result.concepts.capex.reason, /no declared fact-store key/);
});

test('factStoreKeyFor never guesses from the symbol', () => {
  assert.equal(factStoreKeyFor({ symbol: 'KAYNES' }), null);
  assert.equal(factStoreKeyFor({ symbol: 'KAYNES', factStoreKey: 'KAYNES' }), 'KAYNES');
});

test('one store read answers every dashboard concept', async () => {
  const client = clientWith({
    KAYNES: [
      fact('CAPEX.MANAGEMENT', '2026-03-31', 473),
      fact('REVENUE.OPERATIONS_NET', '2026-03-31', 3_000),
    ],
  });
  const result = await fundamentalsFor(client,
    { symbol: 'KAYNES', factStoreKey: 'KAYNES' }, { period_end: '2026-03-31' });
  assert.equal(result.factCount, 2);
  assert.deepEqual(Object.keys(result.concepts), [...DASHBOARD_CONCEPTS]);
  assert.equal(result.concepts.capex.state, FUNDAMENTAL_STATE.FOUND);
  assert.equal(result.concepts.revenue.state, FUNDAMENTAL_STATE.FOUND);
  assert.equal(result.concepts.debt.state, FUNDAMENTAL_STATE.NOT_DISCLOSED);
  assert.deepEqual(result.periods, ['2026-03-31']);
});

test('the universe report separates ingested from not ingested from unmapped', async () => {
  const universe = { members: [
    { symbol: 'KAYNES', factStoreKey: 'KAYNES' },
    { symbol: 'CGPOWER', factStoreKey: 'CGPOWER' },
    { symbol: 'NETWEB' },
  ] };
  const result = await fundamentalsForUniverse(
    clientWith({ KAYNES: [fact('CAPEX.MANAGEMENT', '2026-03-31', 473)] }),
    universe, { period_end: '2026-03-31' },
  );
  assert.deepEqual(result.ingested, ['KAYNES']);
  assert.deepEqual(result.notIngested, ['CGPOWER', 'NETWEB']);
  assert.deepEqual(result.unmapped, ['NETWEB']);
});

test('capex intensity is a derivation over cited rows, with its provenance', () => {
  // "Kaynes capex intensity increased" has to open into the rows it came
  // from. This is the assertion that the claim is traceable.
  const facts = [
    fact('CAPEX.MANAGEMENT', '2026-03-31', 473),
    fact('CAPEX.MANAGEMENT', '2025-03-31', 200),
    fact('REVENUE.OPERATIONS_NET', '2026-03-31', 3_000),
    fact('REVENUE.OPERATIONS_NET', '2025-03-31', 2_500),
    fact('REVENUE.OPERATIONS_NET', '2024-03-31', 2_000),
    fact('REVENUE.OPERATIONS_NET', '2023-03-31', 1_500),
  ];
  const intensity = intensityFrom(facts);
  assert.equal(intensity.periods.latest, '2026-03-31');
  assert.equal(Number(intensity.capexToSales.toFixed(4)), 0.1577);
  assert.equal(Number(intensity.capexGrowth.toFixed(4)), 1.365);
  assert.equal(Number(intensity.revenueCagr3y.toFixed(4)), 0.2599);

  const capexLatest = intensity.provenance.find((one) => one.input === 'capex@latest');
  assert.equal(capexLatest.state, FUNDAMENTAL_STATE.FOUND);
  assert.equal(capexLatest.citations[0].source_page, 142);
});

test('a ratio with a missing input is null and named, never zero', () => {
  const intensity = intensityFrom([fact('CAPEX.MANAGEMENT', '2026-03-31', 473)]);
  assert.equal(intensity.capexToSales, null);
  assert.equal(intensity.revenueCagr3y, null);
  assert.ok(intensity.unavailable.includes('capexToSales'));
  assert.ok(intensity.unavailable.includes('revenueCagr3y'));
});

test('a three-year CAGR is not computed from two disclosed years', () => {
  // With only FY26 and FY25 there is no FY23 to grow from, and annualising
  // one year as three would overstate it badly.
  const intensity = intensityFrom([
    fact('REVENUE.OPERATIONS_NET', '2026-03-31', 3_000),
    fact('REVENUE.OPERATIONS_NET', '2025-03-31', 1_500),
  ]);
  assert.equal(intensity.revenueCagr3y, null);
});

test('intensity rows are the shape stage 3 reads, gaps included', async () => {
  const universe = { members: [
    { symbol: 'KAYNES', factStoreKey: 'KAYNES' },
    { symbol: 'NETWEB' },
  ] };
  const { rows, detail } = await intensityForUniverse(
    clientWith({ KAYNES: [
      fact('CAPEX.MANAGEMENT', '2026-03-31', 473),
      fact('REVENUE.OPERATIONS_NET', '2026-03-31', 3_000),
    ] }),
    universe,
  );
  assert.equal(rows.length, 2);
  assert.equal(Number(rows[0].capexToSales.toFixed(4)), 0.1577);
  assert.deepEqual(rows[1], { symbol: 'NETWEB' });
  assert.equal(detail.NETWEB.unmapped, true);
});

test('definitionsFor finds every definition of a concept', () => {
  const capex = definitionsFor('capex');
  assert.ok(capex.includes('CAPEX.MANAGEMENT'));
  assert.ok(capex.includes('CAPEX.CASH_PPE_INTANGIBLES'));
  assert.ok(capex.includes('CAPEX.SEGMENT'));
});

test('mappings are declared onto the universe, not inferred inside it', () => {
  const universe = { members: [{ symbol: 'KAYNES' }, { symbol: 'NETWEB' }] };
  const mapped = withFactStoreKeys(universe, { KAYNES: 'KAYNES' });
  assert.equal(mapped.members[0].factStoreKey, 'KAYNES');
  assert.equal(mapped.members[1].factStoreKey, undefined);
  // The original is untouched: a caller holding the loaded universe does not
  // suddenly find keys on it.
  assert.equal(universe.members[0].factStoreKey, undefined);
});

/* ── stage 3 from a file of cited inputs ──────────────────────────────── */

import { intensityFromInputs, stageThreeFromInputs } from './aiEnablersFundamentals.js';

test('filed inputs give the same four ratios as the fact store path', () => {
  const out = intensityFromInputs({
    symbol: 'POWERINDIA',
    revenue: { FY26: 8147.71, FY23: 4483.65 },
    capex: { FY26: 509.83, FY25: 129.09 },
    rnd: { FY26: null },
  });
  assert.equal(Number(out.capexToSales.toFixed(4)), Number((509.83 / 8147.71).toFixed(4)));
  assert.equal(Number(out.capexGrowth.toFixed(4)), Number((509.83 / 129.09 - 1).toFixed(4)));
  assert.equal(Number(out.revenueCagr3y.toFixed(4)), Number(((8147.71 / 4483.65) ** (1 / 3) - 1).toFixed(4)));
  assert.equal(out.rndToSales, null);
  assert.deepEqual(out.unavailable, ['rndToSales']);
});

test('a disclosed nil R&D is a real zero; a missing figure is not a zero', () => {
  assert.equal(intensityFromInputs({ revenue: { FY26: 100 }, rnd: { FY26: 0 } }).rndToSales, 0);
  const none = intensityFromInputs({ revenue: { FY26: 100 }, capex: { FY26: null, FY25: 10 } });
  assert.equal(none.capexToSales, null);
  assert.equal(none.capexGrowth, null);
  assert.equal(none.revenueCagr3y, null);
});

test('a zero base yields no growth figure rather than infinity', () => {
  const out = intensityFromInputs({ revenue: { FY26: 100, FY23: 0 }, capex: { FY26: 10, FY25: 0 } });
  assert.equal(out.capexGrowth, null);
  assert.equal(out.revenueCagr3y, null);
});

test('growth compares total with total when the base is total revenue', () => {
  const out = intensityFromInputs({
    revenue: { FY26: 8147.71, FY26_total: 8387.63, FY23_total: 4483.65 },
    capex: { FY26: 509.83, FY25: 129.09 },
  });
  assert.equal(Number(out.revenueCagr3y.toFixed(6)), Number(((8387.63 / 4483.65) ** (1 / 3) - 1).toFixed(6)));
  // Capex intensity stays on revenue from operations.
  assert.equal(Number(out.capexToSales.toFixed(6)), Number((509.83 / 8147.71).toFixed(6)));
  // A missing total is not replaced by the operating figure.
  assert.equal(intensityFromInputs({ revenue: { FY26: 100, FY26_total: null, FY23_total: 80 } }).revenueCagr3y, null);
});

test('stage 3 from the inputs file: a pass, a below, and an unscreened company', async () => {
  const { stageThree } = await import('./aiEnablersScreen.js');
  const file = {
    asOf: '2026-09-18',
    rows: [
      { symbol: 'HIGH', kind: 'member', revenue: { FY26: 200, FY26_total: 210, FY23_total: 100 }, capex: { FY26: 40, FY25: 10 } },
      { symbol: 'LOW', kind: 'member', revenue: { FY26: 100, FY26_total: 105, FY23_total: 100 }, capex: { FY26: 1, FY25: 1 } },
      { symbol: 'MID', kind: 'candidate', revenue: { FY26: 150, FY26_total: 150, FY23_total: 100 } },
      { symbol: 'NONE', kind: 'candidate', revenue: {}, capex: {}, excluded: 'not comparable' },
    ],
  };
  const out = stageThreeFromInputs(file, { stageThree });
  const by = Object.fromEntries(out.rows.map((one) => [one.symbol, one]));
  assert.equal(by.HIGH.verdict, 'PASS');
  assert.equal(by.LOW.verdict, 'BELOW');
  assert.deepEqual(by.LOW.tested, ['revenueCagr3y', 'capexGrowth', 'capexToSales']);
  assert.deepEqual(by.MID.tested, ['revenueCagr3y']);
  assert.equal(by.NONE.verdict, 'NOT_SCREENED');
  assert.equal(by.NONE.excluded, 'not comparable');
  assert.equal(out.asOf, '2026-09-18');
});
