import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  canonicalSector, filedSizeRows, lastCloseThrough, marketValueRows, totalsBy,
} from './aiEnablersMarketValue.js';

const members = [
  { symbol: 'A', layer: 'power' },
  { symbol: 'B', layer: 'power' },
  { symbol: 'C', layer: 'data_centre' },
];
const shares = {
  A: { shares: 10_000_000, asOf: '2026-06-30' },
  B: { shares: 20_000_000, asOf: '2026-06-30' },
  C: { shares: 5_000_000, asOf: '2026-06-30' },
};

test('market value is close times filed shares, in crore', () => {
  const rows = marketValueRows({ members, shares, closes: { A: { date: '2026-09-18', close: 1500 } } });
  assert.equal(rows[0].marketValueCr, 1500);
  assert.equal(rows[0].status, 'OK');
  assert.equal(rows[1].status, 'NO_CLOSE');
});

test('a share count older than a bonus or split ex-date is left out, not scaled', () => {
  const rows = marketValueRows({
    members: [members[0]], shares,
    closes: { A: { date: '2026-09-18', close: 750 } },
    exDates: { A: new Set(['2026-08-24', '2027-01-01']) },
  });
  assert.equal(rows[0].marketValueCr, null);
  assert.equal(rows[0].status, 'SHARE_COUNT_PREDATES_CORPORATE_ACTION');
  assert.equal(rows[0].exDate, '2026-08-24');
});

test('an ex-date on or before the count date does not make it stale', () => {
  const rows = marketValueRows({
    members: [members[0]], shares: { A: { shares: 10_000_000, asOf: '2026-08-24' } },
    closes: { A: { date: '2026-09-18', close: 750 } },
    exDates: { A: new Set(['2026-08-24']) },
  });
  assert.equal(rows[0].status, 'OK');
});

test('the P/B x book gap is reported and flagged, never used to exclude', () => {
  const rows = marketValueRows({
    members: [members[0]], shares,
    closes: { A: { date: '2026-09-18', close: 1500 } },
    pbMarketCaps: { A: 1000 },
  });
  assert.equal(rows[0].marketValueCr, 1500);
  assert.equal(rows[0].crossCheck.gap, 0.5);
  assert.equal(rows[0].crossCheck.within, false);
});

test('totals name what they leave out', () => {
  const rows = marketValueRows({
    members, shares,
    closes: { A: { date: '2026-09-18', close: 1000 }, C: { date: '2026-09-18', close: 6000 } },
  });
  const out = totalsBy(rows, (row) => row.layer);
  assert.equal(out.totalCr, 4000);
  assert.deepEqual(out.groups.map((g) => [g.key, g.marketValueCr, g.share]), [['data_centre', 3000, 0.75], ['power', 1000, 0.25]]);
  assert.deepEqual(out.leftOut, [{ symbol: 'B', status: 'NO_CLOSE' }]);
});

test('only the duplicate spellings are merged', () => {
  assert.equal(canonicalSector('Cables'), 'Cable');
  assert.equal(canonicalSector('Capital Goods - Electrical Equipment'), 'Electric Equipment');
  assert.equal(canonicalSector('Auto Ancillary'), 'Auto Ancillary');
  assert.equal(canonicalSector(null), null);
});

test('stage 2 sizes free float on filed shares and says why a row is unsized', () => {
  const rows = marketValueRows({
    members, shares,
    closes: { A: { date: '2026-09-18', close: 1000 }, C: { date: '2026-09-18', close: 6000 } },
  });
  const out = filedSizeRows(rows, {
    floats: { A: { ratio: 0.25, asOf: 'Jun 2026' }, C: { ratio: null } },
    turnover: { A: 5e8 },
  });
  assert.equal(out[0].freeFloatMarketCap, 250);
  assert.equal(out[0].medianDailyTurnover, 5e8);
  assert.equal(out[1].reason, 'NO_CLOSE');
  assert.equal(out[1].freeFloatMarketCap, null);
  assert.equal(out[2].reason, 'NO_FREE_FLOAT_RATIO');
});

test('the last close is the latest on or before the cut-off', () => {
  const closes = new Map([['2026-09-16', 1], ['2026-09-17', 2], ['2026-09-18', 3]]);
  assert.deepEqual(lastCloseThrough(closes, '2026-09-17'), { date: '2026-09-17', close: 2 });
  assert.equal(lastCloseThrough(new Map(), '2026-09-17'), null);
});

test('every admitted member has a filed share count with its source', async () => {
  const read = async (name) => JSON.parse(await readFile(new URL(`../config/${name}`, import.meta.url), 'utf8'));
  const universe = await read('india-ai-enablers.universe.json');
  const file = await read('india-ai-enablers.shares.json');
  for (const member of universe.members.filter((one) => one.admitted !== false)) {
    const one = file.shares[member.symbol];
    assert.ok(one, `${member.symbol} has no share count`);
    assert.ok(Number.isInteger(one.shares) && one.shares > 0, `${member.symbol} share count`);
    assert.match(one.asOf, /^\d{4}-\d{2}-\d{2}$/);
    assert.ok(one.source && one.excerpt, `${member.symbol} needs a source and an excerpt`);
  }
});
