import test from 'node:test';
import assert from 'node:assert/strict';
import { PROMOTER_HEADERS, parsePromoterTables } from './manualPromoterScreener.js';

const header = PROMOTER_HEADERS.join(',');
const first = '1,Example Ltd,1.25,2026-06-30,100,1200,2026-06-30,12,1.4,,-2.1,EXAMPLE,500001,INE123A01011';
const second = '2,Other Ltd,0.75,2026-06-30,70,900,2026-06-30,8,0.8,10,15,OTHER,500002,INE123A01012';

test('accepts the promoter CSV and preserves missing financial growth', () => {
  const rows = parsePromoterTables([`${header}\n${first}\n${second}`], '2026-09-30');
  assert.equal(rows.length, 2);
  assert.equal(rows[0].revenueGrowth, null);
  assert.equal(rows[0].profitGrowth, -2.1);
  assert.equal(rows[1].promoterChange, 0.75);
});

test('rejects duplicates and nonqualifying promoter changes', () => {
  assert.throws(() => parsePromoterTables([`${header}\n${first}\n${first}`], '2026-09-30'), /Duplicate ISIN/);
  assert.throws(() => parsePromoterTables([`${header}\n${first.replace(',1.25,', ',0.1,')}`], '2026-09-30'), /above 0.1%/);
});

test('rejects a filing date later than the snapshot date', () => {
  assert.throws(() => parsePromoterTables([`${header}\n${first}`], '2026-01-01'), /cannot be after/);
});
