import test from 'node:test';
import assert from 'node:assert/strict';
import { aggregateConsensus } from '../services/institutionalHoldingsService.js';

/**
 * Quarter activity on the consensus table read +0/-0 on every row, next to
 * prose describing movement. Holdings are grouped by CUSIP; the changes were
 * still grouped by `ticker || cusip`, so every lookup asked a CUSIP of a
 * ticker-keyed map and missed. Zeros that look measured are worse than a
 * stated absence, so the two sides are exercised together here.
 */
const holdings = [
  { cusip: '023135106', ticker: 'AMZN', issuer_name: 'AMAZON COM INC', manager_id: 'm1', portfolio_weight: 8, value_usd: 8_000_000_000 },
  { cusip: '023135106', ticker: 'AMZN', issuer_name: 'AMAZON COM INC', manager_id: 'm2', portfolio_weight: 5, value_usd: 5_000_000_000 },
  { cusip: '023135106', ticker: null, issuer_name: 'AMAZON COM INC', manager_id: 'm3', portfolio_weight: 3, value_usd: 3_000_000_000 },
];

test('a security whose managers bought and sold does not report no activity', () => {
  const changes = [
    { cusip: '023135106', ticker: 'AMZN', manager_id: 'm1', change_type: 'increased', share_change: 1000 },
    { cusip: '023135106', ticker: 'AMZN', manager_id: 'm2', change_type: 'new', share_change: 5000 },
    { cusip: '023135106', ticker: null, manager_id: 'm4', change_type: 'exited', share_change: -2000 },
  ];
  const [row] = aggregateConsensus(holdings, changes, 48);
  assert.equal(row.owners, 3);
  assert.ok(row.new_buyers + row.increasers + row.reducers + row.exits > 0,
    'the table showed +0/-0 for every security while the page described movement');
  assert.equal(row.new_buyers, 1);
  assert.equal(row.increasers, 1);
});

test('a change row carrying no ticker still matches its holding', () => {
  // This is the case that made the two keys diverge: enrichment resolves per
  // filing, so one security reaches the aggregation with a ticker on some rows
  // and not others.
  const changes = [{ cusip: '023135106', ticker: null, manager_id: 'm1', change_type: 'increased', share_change: 10 }];
  const [row] = aggregateConsensus(holdings, changes, 48);
  assert.equal(row.increasers, 1);
});

test('changes for a different security do not leak in', () => {
  const changes = [{ cusip: '037833100', ticker: 'AAPL', manager_id: 'm1', change_type: 'new', share_change: 10 }];
  const [row] = aggregateConsensus(holdings, changes, 48);
  assert.equal(row.new_buyers, 0);
  assert.equal(row.increasers, 0);
});

test('a manager that exited is counted as an exit, not an owner', () => {
  const changes = [{ cusip: '023135106', ticker: 'AMZN', manager_id: 'm9', change_type: 'exited', share_change: -500 }];
  const [row] = aggregateConsensus(holdings, changes, 48);
  assert.equal(row.owners, 3, 'a manager that exited no longer holds it');
  assert.equal(row.exits, 1);
});
