import test from 'node:test';
import assert from 'node:assert/strict';
import { topTrades } from '../services/topTrades.js';

const changes = [
  { cusip: 'A', ticker: 'AAA', issuer_name: 'Alpha', change_type: 'new', weight_change: 3.2, current_weight: 3.2, previous_weight: 0, previous_shares: 0, share_change: 1000, share_change_pct: null },
  { cusip: 'B', ticker: 'BBB', issuer_name: 'Beta', change_type: 'increased', weight_change: 1.1, current_weight: 15, previous_weight: 13.9, previous_shares: 500, share_change: 100, share_change_pct: 20 },
  { cusip: 'C', ticker: 'CCC', issuer_name: 'Gamma', change_type: 'reduced', weight_change: -0.8, current_weight: 2, previous_weight: 2.8, previous_shares: 900, share_change: -300, share_change_pct: -33 },
  { cusip: 'D', ticker: 'DDD', issuer_name: 'Delta', change_type: 'exited', weight_change: -4.5, current_weight: 0, previous_weight: 4.5, previous_shares: 800, share_change: -800, share_change_pct: -100 },
];
const values = new Map([['A', 5_000_000_000], ['B', 20_000_000_000], ['C', 1_000_000_000], ['D', 9_000_000_000]]);

test('buys rank by weight added, not by share count', () => {
  // Weight is the manager's own scaling. Ten million dollars is conviction for
  // one filer and a rounding error for another; a table sorted on size says
  // more about fund size than about what anybody decided.
  const { buys } = topTrades(changes, { valueByCusip: values });
  assert.deepEqual(buys.map((b) => b.ticker), ['AAA', 'BBB']);
  assert.equal(buys[0].weight_change, 3.2);
});

test('an opened position is marked apart from an addition', () => {
  // A manager opening at 3% has committed to something it did not hold; one
  // moving 13.9 to 15 has not. Both belong, labelled.
  const { buys, opened } = topTrades(changes, { valueByCusip: values });
  assert.equal(buys.find((b) => b.ticker === 'AAA').opened, true);
  assert.equal(buys.find((b) => b.ticker === 'BBB').opened, false);
  assert.equal(opened, 1);
});

test('sells rank by the size of the retreat, so an exit leads', () => {
  const { sells } = topTrades(changes, { valueByCusip: values });
  assert.deepEqual(sells.map((s) => s.ticker), ['DDD', 'CCC']);
  assert.equal(sells[0].closed, true);
});

test('an exited position has no current value, rather than a value of zero', () => {
  // Zero would read as a holding worth nothing instead of one that is gone.
  const { sells } = topTrades(changes, { valueByCusip: values });
  assert.equal(sells.find((s) => s.ticker === 'DDD').current_value_usd, null);
  assert.equal(sells.find((s) => s.ticker === 'CCC').current_value_usd, 1_000_000_000);
});

test('a percentage change is dropped when there was nothing to change from', () => {
  // EDGAR-derived rows sometimes carry a computed percentage even where the
  // previous holding was zero. Dividing by nothing is not a hundred per cent
  // growth, it is undefined, and printing it invents a rate of change.
  const openedWithPct = [{
    cusip: 'N', ticker: 'NNN', change_type: 'new', weight_change: 2,
    previous_shares: 0, share_change: 900, share_change_pct: 100,
  }];
  assert.equal(topTrades(openedWithPct).buys[0].share_change_pct, null);
});

test('a large share count does not outrank a large conviction', () => {
  // A million shares of a penny stock is a smaller commitment than ten
  // thousand of an expensive one. Weight is what the manager decided; share
  // count is an artefact of the price.
  const mixed = [
    { cusip: 'P', ticker: 'PENNY', change_type: 'increased', weight_change: 0.2, previous_shares: 1, share_change: 5_000_000, share_change_pct: 10 },
    { cusip: 'Q', ticker: 'BIG', change_type: 'increased', weight_change: 4.0, previous_shares: 1, share_change: 12_000, share_change_pct: 10 },
  ];
  assert.deepEqual(topTrades(mixed).buys.map((b) => b.ticker), ['BIG', 'PENNY']);
});

test('a new position reports no percentage change, because there is no base', () => {
  // Dividing by a previous holding of zero is infinite. The move is the
  // weight itself, which the reader can already see.
  const { buys } = topTrades(changes, { valueByCusip: values });
  assert.equal(buys.find((b) => b.ticker === 'AAA').share_change_pct, null);
  assert.equal(buys.find((b) => b.ticker === 'BBB').share_change_pct, 20);
});

test('the totals count the whole quarter, not the rows displayed', () => {
  // A table of six must not be mistaken for everything that happened.
  const many = Array.from({ length: 20 }, (_, i) => ({
    cusip: `X${i}`, ticker: `X${i}`, change_type: 'increased', weight_change: i + 1, previous_shares: 1,
  }));
  const t = topTrades(many, { limit: 6 });
  assert.equal(t.buys.length, 6);
  assert.equal(t.total_buys, 20);
});

test('a change with no movement is not listed as a trade', () => {
  const flat = [{ cusip: 'Z', ticker: 'ZZZ', change_type: 'increased', weight_change: 0, previous_shares: 1 }];
  const t = topTrades(flat);
  assert.equal(t.buys.length, 0);
  assert.equal(t.total_buys, 1, 'it still happened, it just did not move the book');
});

test('an empty quarter yields empty lists rather than throwing', () => {
  const t = topTrades([]);
  assert.deepEqual(t.buys, []);
  assert.deepEqual(t.sells, []);
  assert.equal(t.total_buys, 0);
  assert.deepEqual(topTrades(null).sells, []);
});

test('a move too small to render does not take a row', () => {
  // Berkshire's list carried LEN-B at +0.00% - a move from 0.01 to 0.01 -
  // which tells a reader nothing and displaced something that would have.
  const tiny = [
    { cusip: 'T', ticker: 'TINY', change_type: 'increased', weight_change: 0.001, previous_weight: 0.01, current_weight: 0.01, previous_shares: 1 },
    { cusip: 'R', ticker: 'REAL', change_type: 'increased', weight_change: 0.9, previous_weight: 1, current_weight: 1.9, previous_shares: 1 },
  ];
  assert.deepEqual(topTrades(tiny).buys.map((b) => b.ticker), ['REAL']);
});

test('opening a position always ranks, however small', () => {
  // The quarter Berkshire opened one position, the footnote said so and no
  // row carried the tag: the opening was smaller than six trivial additions.
  // Starting a holding is a different kind of act from adding to one.
  const rows = [
    { cusip: 'N', ticker: 'NEW', change_type: 'new', weight_change: 0.002, previous_weight: 0, current_weight: 0.002, previous_shares: 0 },
    ...Array.from({ length: 8 }, (_, i) => ({
      cusip: `B${i}`, ticker: `B${i}`, change_type: 'increased', weight_change: 1 + i,
      previous_weight: 1, current_weight: 2 + i, previous_shares: 1,
    })),
  ];
  const { buys } = topTrades(rows);
  assert.equal(buys[0].ticker, 'NEW', 'the opening leads');
  assert.equal(buys[0].opened, true);
  assert.equal(buys.length, 6);
});

test('closing a position always ranks, however small', () => {
  const rows = [
    { cusip: 'X', ticker: 'GONE', change_type: 'exited', weight_change: -0.002, previous_weight: 0.002, current_weight: 0, previous_shares: 5 },
    ...Array.from({ length: 8 }, (_, i) => ({
      cusip: `S${i}`, ticker: `S${i}`, change_type: 'reduced', weight_change: -(1 + i),
      previous_weight: 5, current_weight: 1, previous_shares: 1,
    })),
  ];
  const { sells } = topTrades(rows);
  assert.equal(sells[0].ticker, 'GONE');
  assert.equal(sells[0].closed, true);
});
