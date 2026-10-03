import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { valuationFingerprint, valuationMoney, valuationStale } from './investorValuations.js';
test('valuation identity matches Python and changes with disclosed quantities', async () => {
  const profile = { reportPeriod: 'Jun 2026', rows: [{ stock: 'Test Ltd', quantity: '1,000', history: ['2%'] }] };
  const python = execFileSync('python3', ['-c', "import sys;sys.path.insert(0,'scripts/investor_valuation');from refresh import fingerprint;import json;print(fingerprint(json.loads(sys.argv[1])))", JSON.stringify(profile)], { encoding: 'utf8' }).trim();
  assert.equal(await valuationFingerprint(profile), python);
  profile.rows[0].quantity = '2,000';
  assert.notEqual(await valuationFingerprint(profile), python);
});
test('display retains unknown values and detects overdue refreshes', () => {
  assert.equal(valuationMoney(null, 'IN'), 'Not priced');
  assert.equal(valuationMoney(1e7, 'IN'), '₹1 Cr');
  assert.equal(valuationMoney(1e6, 'US'), '$1 M');
  assert.equal(valuationStale({ updatedAt: new Date(Date.now()-48*3600000).toISOString() }), true);
  assert.equal(valuationStale({ updatedAt: new Date().toISOString() }), false);
});
