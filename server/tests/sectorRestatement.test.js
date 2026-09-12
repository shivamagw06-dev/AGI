import test from 'node:test';
import assert from 'node:assert/strict';
import { restatements, restated, movementSummary } from '../services/sectorRestatement.js';
import { classifySic } from '../services/sicSectors.js';

const row = (over = {}) => ({
  id: 'r1', security_key: 'K', ticker: 'X', sic_code: '3674',
  sector: 'Industrials', industry: 'Semiconductors & Related Devices', ...over,
});

test('the rows this exists for', () => {
  // Written by the old map, and the exact rows the nightly queue would never
  // revisit, because it measures how long ago a row was written rather than
  // which map wrote it.
  const changes = restatements([
    row({ ticker: 'NVDA', sic_code: '3674', sector: 'Industrials' }),
    row({ ticker: 'AAPL', sic_code: '3571', sector: 'Industrials' }),
    row({ ticker: 'MSFT', sic_code: '7372', sector: 'Consumer Discretionary' }),
  ], classifySic);
  assert.deepEqual(changes.map((c) => [c.row.ticker, c.from, c.to]), [
    ['NVDA', 'Industrials', 'Information Technology'],
    ['AAPL', 'Industrials', 'Information Technology'],
    ['MSFT', 'Consumer Discretionary', 'Information Technology'],
  ]);
});

test('a row that already agrees with the map is not rewritten', () => {
  // The apply must be a no-op on a table that is already correct, or every
  // run churns four thousand rows to change nothing.
  assert.deepEqual(restatements([row({ sector: 'Information Technology' })], classifySic), []);
});

test('an unreadable sic_code leaves the row exactly as it was', () => {
  // The important guard. Re-deriving from a missing input would replace a
  // real sector with Unclassified, which is a loss dressed up as a
  // correction - and these rows are the ones a human most likely fixed.
  for (const code of ['', null, undefined, '   ', 'N/A', '0', '-1', 'abc']) {
    assert.deepEqual(
      restatements([row({ sic_code: code, sector: 'Health Care' })], classifySic), [],
      `sic_code ${JSON.stringify(code)} should be left alone`,
    );
  }
});

test('a code the map does not cover leaves the row alone', () => {
  // 1150 sits between metal mining and coal and belongs to no range. The row
  // keeps whatever it has rather than being downgraded.
  assert.deepEqual(restatements([row({ sic_code: '1150', sector: 'Materials' })], classifySic), []);
});

test('industry is never touched', () => {
  // It holds EDGAR's own description where the registrant gave one, which is
  // more specific than our label and was not what was wrong.
  const [change] = restatements([row({ industry: "EDGAR's own words" })], classifySic);
  const out = restated(change);
  assert.equal(out.industry, "EDGAR's own words");
  assert.equal(out.sector, 'Information Technology');
});

test('a restatement carries the whole row, changing one field', () => {
  // The write goes back through an upsert, so it has to satisfy every
  // not-null column the table declares.
  const [change] = restatements([row({ id: 'abc', security_key: 'CUSIP1', valid_from: '2023-09-30', source: 'SEC submissions' })], classifySic);
  const out = restated(change);
  assert.equal(out.id, 'abc');
  assert.equal(out.security_key, 'CUSIP1');
  assert.equal(out.valid_from, '2023-09-30');
  assert.equal(out.source, 'SEC submissions');
  assert.equal(out.sic_code, '3674');
  assert.equal(out.sector, 'Information Technology');
  assert.ok(out.updated_at);
});

test('a numeric sic_code works as well as a string', () => {
  const [change] = restatements([row({ sic_code: 3674 })], classifySic);
  assert.equal(change.to, 'Information Technology');
});

test('the summary counts moves, largest first', () => {
  const changes = restatements([
    row({ sic_code: '3674' }), row({ sic_code: '3571' }), row({ sic_code: '3679' }),
    row({ sic_code: '2834', sector: 'Materials' }),
  ], classifySic);
  assert.deepEqual(movementSummary(changes), [
    { move: 'Industrials -> Information Technology', count: 3 },
    { move: 'Materials -> Health Care', count: 1 },
  ]);
});

test('a fund row survives the restatement pass untouched', () => {
  // Funds are classified from the forms a registrant files, not from a SIC
  // code, and carry none. The restatement re-derives from sic_code, so
  // without the Unclassified guard every fund would be wiped back to
  // Unclassified on the first nightly run after it was classified.
  const fund = { id: 'f1', security_key: '78462F103', ticker: 'SPY', sic_code: null, sector: 'Funds & ETFs', industry: 'Fund or ETF' };
  assert.deepEqual(restatements([fund], classifySic), []);
  assert.deepEqual(restatements([{ ...fund, sic_code: '' }], classifySic), []);
});

test('nothing in yields nothing out, without throwing', () => {
  assert.deepEqual(restatements(undefined, classifySic), []);
  assert.deepEqual(restatements([], classifySic), []);
  assert.deepEqual(movementSummary(), []);
  assert.deepEqual(movementSummary([]), []);
});
