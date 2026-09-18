import test from 'node:test';
import assert from 'node:assert/strict';
import { impliedGrowth, runModel, valueOf } from './indiaAiEstimates.js';

const d = (value) => ({ kind: 'disclosed', value });
const a = (value, low, high) => ({ kind: 'assumption', value, low, high });

test('a disclosed input ignores the scenario; an assumption follows it; an override wins', () => {
  assert.equal(valueOf(d(10), 'high'), 10);
  assert.equal(valueOf(a(0.1, 0.05, 0.2), 'low'), 0.05);
  assert.equal(valueOf(a(0.1, 0.05, 0.2), 'high', { 'X.m': '0.3' }, 'X.m'), 0.3);
});

test('growBase compounds a disclosed base and measures it against filed EBITDA', () => {
  const out = runModel({
    symbol: 'X', type: 'growBase',
    params: { aiRevenueBaseCr: d(1000), years: d(3), growth: a(0.1, 0, 0.2), margin: a(0.1, 0.05, 0.15), totalEbitdaFY26Cr: d(500) },
  });
  assert.equal(out.ok, true);
  assert.equal(out.aiRevenueCr, 1331);
  assert.equal(out.aiEbitdaCr, 133);
  assert.equal(out.materiality, 0.2662);
});

test('with no disclosed share the model waits for one instead of guessing', () => {
  const model = {
    symbol: 'H', type: 'growBase',
    params: { revenueBaseCr: d(8000), dcShare: { kind: 'assumption', value: null, low: null, high: null }, years: d(3), growth: a(0.2, 0.1, 0.3), margin: a(0.15, 0.1, 0.2) },
  };
  assert.deepEqual(runModel(model).missing, ['dcShare']);
  const set = runModel(model, { overrides: { 'H.dcShare': 0.1 } });
  assert.equal(set.ok, true);
  assert.equal(set.aiRevenueCr, Math.round(800 * 1.2 ** 3));
});

test('a contract is spread over its stated period', () => {
  const out = runModel({ symbol: 'S', type: 'contract', params: { contractValueCr: d(9000), years: d(3), margin: a(0.2, 0.15, 0.25) } });
  assert.equal(out.aiRevenueCr, 3000);
  assert.equal(out.aiEbitdaCr, 600);
});

test('a target is discounted by achievement, and capacity multiplies out', () => {
  assert.equal(runModel({ symbol: 'B', type: 'target', params: { targetRevenueCr: d(3000), achievement: a(0.8, 0.5, 1), margin: a(0.1, 0.07, 0.12) } }).aiRevenueCr, 2400);
  const cap = runModel({ symbol: 'A', type: 'capacity', params: { operatingMW: d(65.4), addedMW: a(400, 200, 600), utilisation: a(0.8, 0.7, 0.9), revenuePerMWCr: a(10, 8, 12), margin: a(0.5, 0.4, 0.6) } }, { scenario: 'low' });
  assert.equal(cap.aiRevenueCr, Math.round(265.4 * 0.7 * 8));
});

test('implied growth is what the price needs, and refuses bad inputs', () => {
  const out = impliedGrowth({ marketValueCr: 30000, patCr: 500, exitMultiple: 30, years: 3 });
  assert.equal(out.trailingMultiple, 60);
  assert.equal(out.requiredPatCr, 1000);
  assert.equal(out.cagr, 0.2599);
  assert.equal(impliedGrowth({ marketValueCr: 30000, patCr: -5, exitMultiple: 30, years: 3 }), null);
});

test('electricity is IT load x PUE x hours, and PUE below 1 is refused', async () => {
  const { dcElectricityGWh } = await import('./indiaAiEstimates.js');
  assert.equal(dcElectricityGWh({ itMW: 1, pue: 1.3 }), 11.39);
  assert.equal(dcElectricityGWh({ itMW: 250, pue: 1.3 }), 2847);
  assert.equal(dcElectricityGWh({ itMW: 100, pue: 0.9 }), null);
});

test('an OSAT model waits for price and utilisation, then multiplies out', () => {
  const model = { symbol: 'C', type: 'osat', params: {
    unitsPerDay: d(15e6), utilisation: a(null, null, null), pricePerUnitRs: a(null, null, null), margin: a(0.2, 0.1, 0.3) } };
  assert.deepEqual(runModel(model).missing, ['utilisation', 'pricePerUnitRs']);
  const out = runModel(model, { overrides: { 'C.utilisation': 0.5, 'C.pricePerUnitRs': 10 } });
  assert.equal(out.aiRevenueCr, Math.round(15e6 * 365 * 0.5 * 10 / 1e7));
});

test('market size multiplies MW by content per layer and names layers it cannot price', async () => {
  const { marketSize } = await import('./indiaAiEstimates.js');
  const out = marketSize({ addedMW: 4400, layers: [
    { key: 'cable', label: 'Cables', lowCrPerMW: 3.5, highCrPerMW: 3.5 },
    { key: 'elec', label: 'Electrical', lowCrPerMW: 20, highCrPerMW: 28 },
    { key: 'cool', label: 'Cooling', lowCrPerMW: null },
  ] });
  assert.equal(out.totalLowCr, 4400 * 23.5);
  assert.equal(out.totalHighCr, 4400 * 31.5);
  assert.deepEqual(out.unpriced, ['Cooling']);
  assert.equal(marketSize({ addedMW: 0, layers: [] }), null);
});

test('market share multiplies industry demand, and a JV counts at its share', () => {
  const ms = runModel({ symbol: 'P', type: 'marketShare', params: { mwPerYear: a(1250, 800, 1800), contentPerMWCr: d(3.5), share: a(0.25, 0.15, 0.4), margin: a(0.138, 0.12, 0.15) } });
  assert.equal(ms.aiRevenueCr, 1094);
  const jv = runModel({ symbol: 'J', type: 'capacity', params: { operatingMW: d(100), addedMW: a(0, 0, 0), utilisation: a(1, 1, 1), revenuePerMWCr: a(10, 10, 10), margin: a(0.5, 0.5, 0.5), ownershipShare: d(0.5) } });
  assert.equal(jv.aiRevenueCr, 500);
  assert.equal(jv.aiEbitdaCr, 250);
});
