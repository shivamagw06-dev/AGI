import test from 'node:test';
import assert from 'node:assert/strict';
import { aiMateriality, capitalQuality, earningsMomentum, evidenceConfidence, expectationLoad } from './indiaAiFactors.js';

const d = (value) => ({ kind: 'disclosed', value });
const a = (value, low, high) => ({ kind: 'assumption', value, low, high });

test('materiality comes from the base case, else a stated share, else says why not', () => {
  const model = { symbol: 'X', type: 'contract', params: { contractValueCr: d(900), years: d(3), margin: a(0.2, 0.1, 0.3), totalEbitdaFY26Cr: d(200) } };
  assert.deepEqual([aiMateriality({ model }).band, aiMateriality({ model }).value], ['high', '30%']);
  assert.equal(aiMateriality({ statedShare: '12%' }).band, 'stated only');
  const waiting = { symbol: 'W', type: 'growBase', params: { revenueBaseCr: d(100), dcShare: a(null, null, null), years: d(3), growth: a(0.1, 0, 0.2), margin: a(0.1, 0, 0.2) } };
  assert.equal(aiMateriality({ model: waiting }).band, 'not measurable');
});

test('evidence confidence reads tier and hard-evidence depth', () => {
  const ev = (n) => Array.from({ length: n }, (_, i) => ({ kind: 'order', date: `2026-0${i + 1}-01` }));
  assert.equal(evidenceConfidence({ attribution: 'SEGMENT_REPORTED', admittedOn: ev(1) }).band, 'high');
  assert.equal(evidenceConfidence({ attribution: 'MANAGEMENT_DISCLOSED', admittedOn: ev(2), supportingEvidence: ev(1) }).band, 'high');
  assert.equal(evidenceConfidence({ attribution: 'MANAGEMENT_DISCLOSED', admittedOn: ev(1) }).band, 'medium');
  const low = evidenceConfidence({ attribution: 'NOT_ATTRIBUTABLE', admittedOn: [...ev(2), { kind: 'partnership', date: '2026-09-01' }] });
  assert.equal(low.band, 'low');
  assert.match(low.value, /2 hard items, latest 2026-02-01/);
});

test('momentum is quarter growth and book-to-bill; missing data is not a zero', () => {
  const m = earningsMomentum({ revenueQ1FY27: 130, revenueQ1FY26: 100, intakeQ1FY27: 260 });
  assert.equal(m.band, 'high');
  assert.match(m.value, /\+30% y\/y · book-to-bill 2\.00/);
  assert.equal(earningsMomentum({ revenueQ1FY27: 130 }).band, 'not measurable');
});

test('capital quality separates strong, weak and capital-hungry', () => {
  assert.equal(capitalQuality({ revenueFY26: 100, cfoFY26: 20, capexFY26: 5, statedRoceFY26: 0.3 }).band, 'strong');
  assert.equal(capitalQuality({ revenueFY26: 100, cfoFY26: 5, capexFY26: 20, ebitFY26: 8, capitalEmployedFY26: 100 }).band, 'weak');
  assert.equal(capitalQuality({ revenueFY26: 100, cfoFY26: 50, capexFY26: 150, statedRoceFY26: 0.14 }).band, 'capital-hungry');
  assert.equal(capitalQuality({}).band, 'not measurable');
});

test('expectation load is the growth the price needs', () => {
  const e = expectationLoad({ marketValueCr: 30000, patCr: 500, exitMultiple: 30, years: 3 });
  assert.equal(e.band, 'high');
  assert.match(e.value, /60x FY26 profit · needs 26% a year/);
  assert.equal(expectationLoad({ marketValueCr: 30000, patCr: -1, exitMultiple: 30, years: 3 }).band, 'not measurable');
});

test('a price already under the exit multiple needs no growth, and says so', () => {
  const e = expectationLoad({ marketValueCr: 10000, patCr: 500, exitMultiple: 30, years: 3 });
  assert.equal(e.band, 'low');
  assert.match(e.value, /already at or under 30x; no growth needed/);
});
