import test from 'node:test';
import assert from 'node:assert/strict';
import { PIOTROSKI_HEADERS, parsePiotroskiTables } from './manualPiotroskiScreener.js';

const header = PIOTROSKI_HEADERS.join(',');
const first = 'Example Ltd,EXAMPLE,500001,EXAMPLE,INE123A01011,Industrial,Industrials,123.45,1000,8';
const second = 'Other Ltd,,500002,OTHER,INE123A01012,Banking,Banking and Finance,30,2000,9';

test('accepts 8 and 9 scores, BSE-only rows and a blank workbook column', () => {
  const rows = parsePiotroskiTables([`${header},\n${first},\n${second},`]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].score, 8);
  assert.equal(rows[1].nseCode, '');
  assert.equal(rows[1].score, 9);
});

test('rejects nonqualifying scores and duplicate securities', () => {
  assert.throws(() => parsePiotroskiTables([`${header}\n${first.replace(/,8$/, ',7')}`]), /must be 8 or 9/);
  assert.throws(() => parsePiotroskiTables([`${header}\n${first}\n${first}`]), /Duplicate ISIN/);
});

test('requires the expected headers and a price', () => {
  assert.throws(() => parsePiotroskiTables([`Stock,Wrong\n${first}`]), /10-column header/);
  assert.throws(() => parsePiotroskiTables([`${header}\n${first.replace(',123.45,', ',,')}`]), /Current Price is required/);
});
