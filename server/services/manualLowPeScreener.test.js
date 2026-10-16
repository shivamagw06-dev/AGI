import test from 'node:test';
import assert from 'node:assert/strict';
import { LOW_PE_HEADERS, parseLowPeTables, validateAsOf } from './manualLowPeScreener.js';

const header = LOW_PE_HEADERS.join(',');
const first = '1,Example Ltd,10,15,17,20,-1.2,2,3,1200,Industrials,8,-4,EXAMPLE,500001,INE123A01011';
const second = '1,Other Ltd,8,12,13,14,0.5,-1,2,2000,Banking,4,10,OTHER,500002,INE123A01012';

test('merges the two daily CSV parts and preserves signed values', () => {
  const rows = parseLowPeTables([`${header}\n${first}`, `${header}\n${second}`]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].dayChange, -1.2);
  assert.equal(rows[1].stock, 'Other Ltd');
});

test('rejects a duplicate security before publishing', () => {
  assert.throws(() => parseLowPeTables([`${header}\n${first}`, `${header}\n${first}`]), /Duplicate ISIN/);
});

test('rejects a row that does not qualify for the named screen', () => {
  assert.throws(() => parseLowPeTables([`${header}\n${first.replace(',10,15,', ',16,15,')}`]), /below all three/);
});

test('requires a real snapshot date', () => {
  assert.equal(validateAsOf('2026-09-30'), '2026-09-30');
  assert.throws(() => validateAsOf('2026-02-30'), /valid data date/);
});
