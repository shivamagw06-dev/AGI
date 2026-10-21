import { test } from 'node:test';
import assert from 'node:assert/strict';
import { flattenKeyRatioRows, selectDailyRotation } from './upstoxValuationRatiosRefresh.js';

test('company valuation rotation excludes funds and keeps equity issuers', () => {
  const rows = [
    { symbol: 'FUND', isin: 'INF000000001' },
    { symbol: 'ACME', isin: 'INE000000001' },
    { symbol: 'BETA', isin: 'INE000000002' },
  ];
  const result = selectDailyRotation(rows, { limit: 10, now: new Date('2026-09-30T12:00:00Z') });
  assert.equal(result.universeSize, 2);
  assert.deepEqual(result.companies.map((row) => row.symbol).sort(), ['ACME', 'BETA']);
});

test('empty key-ratio payload has no company rows', () => {
  assert.deepEqual(flattenKeyRatioRows([{ symbol: 'ACME', isin: 'INE000000001', data: [] }]), []);
  assert.equal(flattenKeyRatioRows([{ symbol: 'ACME', isin: 'INE000000001', data: [{ name: 'P/E', company_value: 20 }] }]).length, 1);
});
