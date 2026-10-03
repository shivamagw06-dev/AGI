import test from 'node:test';
import assert from 'node:assert/strict';
import { rankEntries, sectorTotals } from '../services/indexRebalanceService.js';

const row = (ticker, flow, sector = 'Tech') => ({
  source_ticker: ticker, net_passive_flow_usd_mn: flow, sector,
});

test('inflows rank largest first, outflows largest outflow first', () => {
  const { inflows, outflows } = rankEntries([
    row('A', 41), row('B', 88), row('C', -22), row('D', -3),
  ]);
  assert.deepEqual(inflows.map((r) => r.source_ticker), ['B', 'A']);
  // The largest outflow is the most negative, and it must lead its own list
  // rather than sorting to the bottom of a single combined ranking.
  assert.deepEqual(outflows.map((r) => r.source_ticker), ['C', 'D']);
});

test('a row with no flow estimate is kept, not dropped', () => {
  // It is still a real index change. Dropping it hides a constituent addition
  // because nobody had sized it yet, and the page then disagrees with the
  // index provider's own announcement.
  const { inflows, outflows, unsized } = rankEntries([
    row('A', 88), row('NOSIZE', null), row('B', -22),
  ]);
  assert.equal(inflows.length, 1);
  assert.equal(outflows.length, 1);
  assert.deepEqual(unsized.map((r) => r.source_ticker), ['NOSIZE']);
});

test('a zero flow is unsized, not an inflow', () => {
  // Zero is not a buy. Ranking it among the inflows would put a name with no
  // expected flow above every genuine outflow.
  const { inflows, unsized } = rankEntries([row('ZERO', 0), row('A', 5)]);
  assert.deepEqual(inflows.map((r) => r.source_ticker), ['A']);
  assert.deepEqual(unsized.map((r) => r.source_ticker), ['ZERO']);
});

test('sector totals net buys against sells within a sector', () => {
  const totals = sectorTotals([
    row('A', 88, 'Consumer'), row('B', -22, 'Consumer'), row('C', 65, 'Software'),
  ]);
  assert.deepEqual(totals, [
    { sector: 'Software', net_flow_usd_mn: 65 },
    { sector: 'Consumer', net_flow_usd_mn: 66 },
  ].sort((a, b) => b.net_flow_usd_mn - a.net_flow_usd_mn));
});

test('a row with no flow does not contribute a zero to its sector', () => {
  // Counting it as zero would be harmless here but wrong in principle: the
  // sector total must mean "the flows we know about", not "the flows we know
  // about plus some we do not, treated as nothing".
  const totals = sectorTotals([row('A', 88, 'Consumer'), row('B', null, 'Consumer')]);
  assert.deepEqual(totals, [{ sector: 'Consumer', net_flow_usd_mn: 88 }]);
});

test('rows without a sector are grouped, not discarded', () => {
  const totals = sectorTotals([{ net_passive_flow_usd_mn: 10 }]);
  assert.deepEqual(totals, [{ sector: 'Unclassified', net_flow_usd_mn: 10 }]);
});

test('empty input yields empty output, without throwing', () => {
  assert.deepEqual(rankEntries(), { inflows: [], outflows: [], unsized: [] });
  assert.deepEqual(sectorTotals(), []);
});
