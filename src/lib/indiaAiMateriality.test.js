import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyMateriality } from './indiaAiMateriality.js';

const rules = {
  amountCr: 100, revenueShare: 0.05, fy29EbitdaShare: 0.05, capacityShare: 0.05, orderCoverQuarters: 12, evidenceBands: ['medium', 'high'],
};
const base = { rules, evidenceBand: 'medium', hardItems: 2 };

test('a disclosed Rs 100 cr amount with booked revenue is Material', () => {
  const out = classifyMateriality({ ...base, entry: { facts: [{ test: 'amount', valueCr: 145.9, basis: 'D', label: 'x' }], path: { kind: 'revenue' } } });
  assert.equal(out.tier, 'material');
  assert.equal(out.passes[0].tag, 'D');
});

test('an order-book pass finds its path in order cover, and loses it past 12 quarters', () => {
  const entry = { facts: [{ test: 'amount', valueCr: 435, basis: 'D', label: 'x' }] };
  assert.equal(classifyMateriality({ ...base, entry, orderCover: 5.3 }).path.kind, 'cover');
  const far = classifyMateriality({ ...base, entry, orderCover: 14 });
  assert.equal(far.tier, 'not-yet');
  assert.match(far.reasons.join(), /path/);
});

test('a pass on AGI estimate alone is Material, labelled as an estimate', () => {
  const out = classifyMateriality({ ...base, entry: { facts: [{ test: 'amount', valueCr: 80.56, basis: 'I', label: 'x' }] }, fy29Materiality: 0.256 });
  assert.equal(out.tier, 'material-estimate');
  assert.equal(out.path.kind, 'model');
  assert.ok(out.misses.some((m) => /under Rs 100 cr/.test(m)));
});

test('low evidence confidence blocks a pass, whatever the amount', () => {
  const out = classifyMateriality({ ...base, evidenceBand: 'low', entry: { facts: [{ test: 'amount', valueCr: 5000, basis: 'D', label: 'x' }], path: { kind: 'revenue' } } });
  assert.equal(out.tier, 'not-yet');
  assert.match(out.reasons.join(), /confidence is low/);
});

test('contracted capacity needs a named customer and a size to measure against', () => {
  const unnamed = classifyMateriality({ ...base, entry: { facts: [{ test: 'contracted', mw: 758, customerNamed: false, basis: 'I', label: 'x' }] } });
  assert.equal(unnamed.tier, 'not-yet');
  assert.match(unnamed.misses[0], /no customer is named/);
  const small = classifyMateriality({ ...base, entry: { facts: [{ test: 'contracted', mw: 61.4, customerNamed: true, capacityShare: 0.0056, basis: 'I', label: 'x' }] } });
  assert.equal(small.tier, 'not-yet');
  const big = classifyMateriality({ ...base, entry: { facts: [{ test: 'contracted', mw: 630, customerNamed: true, capacityShare: 0.105, basis: 'I', label: 'x' }], path: { kind: 'stated' } } });
  assert.equal(big.tier, 'material');
});

test('a member with nothing quantified is not yet material, and a recorded exception is shown as one', () => {
  const entry = { facts: [], note: 'No capacity, value or revenue disclosed.' };
  assert.equal(classifyMateriality({ ...base, entry }).tier, 'not-yet');
  assert.equal(classifyMateriality({ ...base, entry, exception: { symbol: 'X', reason: 'r' } }).tier, 'exception');
});
