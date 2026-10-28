import test from 'node:test';
import assert from 'node:assert/strict';
import { LOW_PE_HEADERS, parseLowPeTables, reviewLowPeTables, lowPePublicationRows, validateAsOf } from './manualLowPeScreener.js';

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

const expandedHeader = ['Stock Name', 'NSE Code', 'BSE Code', 'Stock Code', 'ISIN', 'Industry Name', 'sector_name', 'Current Price', 'Market Capitalization', 'PE TTM Price to Earnings', 'PE 3Yr Average', 'PE 5Yr Average', 'PE 10Yr Average', 'Day change %', 'Week change %', 'Qtr Change %', 'Market Capitalization', 'sector_name', 'Revenue Growth Qtr YoY %', 'Net Profit Qtr Growth YoY %'];
const expandedRow = ['20 Microns Ltd.', '20MICRONS', '533022', '20MICRONS', 'INE144J01027', 'Coal & Mining', 'Metals & Mining', '161.04', '568.25', '8.39', '12.46', '11.35', '10.32', '-14.65', '-13.23', '-21.06', '568.25', 'Metals & Mining', '-0.99', '5.47'];
const expanded = (...rows) => [expandedHeader, ...rows].map((r) => r.join('\t')).join('\r\n');

test('accepts the expanded 20-column clipboard export without shifting financial fields', () => {
  const [row] = parseLowPeTables([expanded(expandedRow)]);
  assert.deepEqual(row, { serial: 1, stock: '20 Microns Ltd.', peTtm: 8.39, pe3y: 12.46, pe5y: 11.35, pe10y: 10.32, dayChange: -14.65, weekChange: -13.23, quarterChange: -21.06, marketCapCr: 568.25, sector: 'Metals & Mining', revenueGrowth: -0.99, profitGrowth: 5.47, nseCode: '20MICRONS', bseCode: '533022', isin: 'INE144J01027' });
  const bseOnly = [...expandedRow]; bseOnly[1] = '';
  assert.equal(parseLowPeTables([expanded(bseOnly)])[0].nseCode, '');
});

test('matches reordered CSV headers, quoted numbers and company names by name', () => {
  const row = [...expandedRow]; row[0] = 'Example, Ltd.'; row[8] = row[16] = '1,234.50';
  const csv = [expandedHeader, row].map((r) => r.toReversed().map((v) => `"${v}"`).join(',')).join('\n');
  const [parsed] = parseLowPeTables([csv]);
  assert.equal(parsed.stock, 'Example, Ltd.'); assert.equal(parsed.marketCapCr, 1234.5); assert.equal(parsed.peTtm, 8.39);
});

test('rejects conflicting repeated fields, missing columns and truncated rows', () => {
  const mismatch = [...expandedRow]; mismatch[16] = '999';
  assert.throws(() => reviewLowPeTables([expanded(mismatch)]), /repeated Market Cap columns disagree/);
  mismatch[16] = expandedRow[16]; mismatch[17] = 'Other sector';
  assert.throws(() => reviewLowPeTables([expanded(mismatch)]), /repeated Sector columns disagree/);
  assert.throws(() => reviewLowPeTables([expanded(expandedRow.slice(1))]), /expected 20 columns/);
  assert.throws(() => reviewLowPeTables([expandedHeader.slice(1).join('\t')]), /missing required columns: Stock/);
  assert.throws(() => reviewLowPeTables([expanded(expandedRow, expandedRow)]), /Duplicate ISIN/);
});

test('reviews non-qualifying rows but cannot publish them or silently exclude them', () => {
  const equal = [...expandedRow]; equal[4] = 'INE123A01012'; equal[0] = 'Equal P/E Ltd'; equal[9] = equal[11];
  const input = expanded(expandedRow, equal);
  const review = reviewLowPeTables([input]);
  assert.equal(review.inputRows, 2); assert.equal(review.rows.length, 1); assert.equal(review.excludedRows.length, 1);
  assert.equal(review.excludedRows[0].stock, 'Equal P/E Ltd'); assert.equal(review.excludedRows[0].rowNumber, 3);
  assert.throws(() => parseLowPeTables([input]), /below all three/);
  for (const acknowledgement of [undefined, false, 'true']) assert.throws(() => lowPePublicationRows([input], acknowledgement), /acknowledge/);
  assert.deepEqual(lowPePublicationRows([input], true), review.rows);
  assert.throws(() => lowPePublicationRows([expanded(equal)], true), /Nothing was published/);
});
