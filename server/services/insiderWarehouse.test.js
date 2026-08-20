import assert from 'node:assert/strict';
import test from 'node:test';

import {
  clusters, dailyFlow, dedupe, isOpenMarket, modeBreakdown, pledges, regimeOf, side, summarise,
} from './insiderWarehouse.js';

const row = (over = {}) => ({
  company_name: 'Liberty Shoes', reported_on: '2026-08-20', person: 'Anupam Bansal',
  action: 'Acquisition', quantity: 4548, mode: 'Market Purchase', is_open_market: 'true',
  value: 1109712, regulation: 'Insider Trading', regime: 'insider', symbol_match: 'exact',
  ...over,
});

test('a filing stored twice is counted once', () => {
  // insider_trades was re-keyed from ticker to company name once it became clear
  // most of these companies have no ticker. Every row id changed, so the second
  // import inserted alongside the first and 87 trades are stored twice.
  const stale = row({ symbol_match: null });
  assert.equal(dedupe([stale, row()]).length, 1);
});

test('the copy that records how its ticker was resolved is the one kept', () => {
  const kept = dedupe([row({ symbol_match: null, symbol: null }), row({ symbol: 'LIBERTSHOE' })]);
  assert.equal(kept[0].symbol, 'LIBERTSHOE');
});

test('two trades by one person on one day both survive', () => {
  // A promoter can file twice in a session; collapsing them loses a real trade.
  assert.equal(dedupe([row({ quantity: 4548 }), row({ quantity: 9000 })]).length, 2);
});

test('a bare "Market" mode is an open-market trade', () => {
  // SAST filings write "Market" where insider filings write "Market Purchase".
  // Excluding it left a quarter of real open-market activity off the page.
  assert.equal(isOpenMarket(row({ mode: 'Market', is_open_market: 'true' })), true);
});

test('a gift is not an open-market trade', () => {
  // Nobody paid a price, so it is not evidence of conviction.
  assert.equal(isOpenMarket(row({ mode: 'Gift', is_open_market: 'false' })), false);
});

test('a takeover-code filing is separated from an insider one', () => {
  // A SAST filing is an acquirer crossing a threshold, not a director trading
  // their own company.
  assert.equal(regimeOf(row({ regulation: 'SAST (29(2))', regime: 'sast' })), 'sast');
  assert.equal(regimeOf(row()), 'insider');
});

test('the regime is recovered from the regulation when the column is absent', () => {
  // Rows imported before the column existed still carry the regulation text.
  assert.equal(regimeOf({ regulation: 'SAST (Reg31)' }), 'sast');
});

test('value coverage is reported against insider filings only', () => {
  // SAST filings disclose a shareholding change, never a price. Counting them
  // in makes coverage read 61% and look like a collection failure.
  const out = summarise([
    row({ value: 1000 }),
    row({ person: 'B', regulation: 'SAST (29(2))', regime: 'sast', value: null }),
    row({ person: 'C', regulation: 'SAST (29(1))', regime: 'sast', value: null }),
  ]);
  assert.equal(out.stats.valueCoveragePct, 100);
  assert.equal(out.stats.insiderRecords, 1);
  assert.equal(out.stats.sastRecords, 2);
});

test('daily flow nets buys against sells and carries a running total', () => {
  const days = dailyFlow([
    row({ reported_on: '2026-08-18' }),
    row({ reported_on: '2026-08-19', person: 'B', action: 'Disposal', mode: 'Market Sale' }),
    row({ reported_on: '2026-08-19', person: 'C', action: 'Disposal', mode: 'Market Sale' }),
  ]);
  assert.deepEqual(days.map((d) => d.net), [1, -2]);
  assert.deepEqual(days.map((d) => d.cumulativeNet), [1, -1]);
});

test('flow counts filings rather than rupees', () => {
  // A third of filings report no value. A rupee line would step down on the days
  // where the unpriced filings happen to be the large ones.
  const [day] = dailyFlow([row({ value: null }), row({ person: 'B', value: null })]);
  assert.equal(day.buys, 2);
  assert.equal(day.buyValue, 0);
});

test('a gift does not move the flow line', () => {
  assert.deepEqual(dailyFlow([row({ mode: 'Gift', is_open_market: 'false' })]), []);
});

test('three separate buyers make a cluster, one buyer does not', () => {
  const many = ['A', 'B', 'C'].map((person) => row({ person }));
  assert.equal(clusters(many).length, 1);
  assert.equal(clusters(many)[0].buyers, 3);
  assert.equal(clusters([row(), row({ quantity: 10 })]).length, 0);
});

test('one person filing three times is not three buyers', () => {
  // The whole point of a cluster is independent people reaching the same view.
  const repeat = [4548, 9000, 12000].map((quantity) => row({ quantity }));
  assert.equal(clusters(repeat).length, 0);
});

test('buying that stopped months ago is not a current cluster', () => {
  const old = ['A', 'B', 'C'].map((person) => row({ person, reported_on: '2026-01-10' }));
  const recent = row({ person: 'D', reported_on: '2026-08-20', company_name: 'Other' });
  assert.equal(clusters([...old, recent]).length, 0);
});

test('pledges are reported apart from buying and selling', () => {
  // A promoter pledging shares has borrowed against the company. It is a risk
  // disclosure, not a conviction one.
  const out = summarise([
    row({ action: 'unspecified', mode: 'Pledge Creation', is_open_market: 'false' }),
    row({ person: 'B', action: 'Revoke', mode: 'unspecified', is_open_market: 'false' }),
  ]);
  assert.equal(out.stats.buys, 0);
  assert.deepEqual(pledges(out.trades).map((p) => [p.created, p.released]), [[1, 1]]);
});

test('an unstated mode is never counted as an open-market trade', () => {
  const [entry] = modeBreakdown([row({ mode: 'unspecified', is_open_market: 'false' })]);
  assert.equal(entry.openMarket, false);
});

test('an acquisition is a buy and a disposal is a sell', () => {
  assert.equal(side(row()), 'buy');
  assert.equal(side(row({ action: 'Disposal' })), 'sell');
  assert.equal(side(row({ action: 'Pledge' })), 'other');
});

test('the date filter excludes rather than reorders', () => {
  const out = summarise([row({ reported_on: '2026-01-01' }), row({ reported_on: '2026-08-20' })],
    { from: '2026-06-01' });
  assert.equal(out.stats.records, 1);
});

test('search covers the company, the person and the ticker', () => {
  const rows = [row(), row({ company_name: 'Astral', person: 'Sujal Shroff', symbol: 'ASTRAL' })];
  assert.equal(summarise(rows, { search: 'shroff' }).stats.records, 1);
  assert.equal(summarise(rows, { search: 'astral' }).stats.records, 1);
});
