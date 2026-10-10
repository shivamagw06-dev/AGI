import test from 'node:test';
import assert from 'node:assert/strict';
import { consensusKey, dedupeSignalRows } from '../services/consensusKey.js';

test('one security groups under one key whether or not its ticker resolved', () => {
  // The failure. Tickers resolve per filing at that filing's report date, so
  // two managers holding the same security on different dates can carry
  // different values - one enriched, one not. Keyed on `ticker || cusip` those
  // formed two groups that both published the same CUSIP, and the insert
  // carried two rows with one conflict key.
  const enriched = { cusip: '438516106', ticker: 'HON' };
  const notYet = { cusip: '438516106', ticker: null };
  assert.equal(consensusKey(enriched), consensusKey(notYet));
});

test('two securities of one issuer stay distinct', () => {
  // Honeywell's succession pair. They may well be the same company, but that
  // is for the identity chain to establish, not for a ticker coincidence.
  assert.notEqual(consensusKey({ cusip: '438516106' }), consensusKey({ cusip: '438516205' }));
});

test('a row with no CUSIP has no consensus identity', () => {
  assert.equal(consensusKey({ ticker: 'HON' }), null);
  assert.equal(consensusKey({}), null);
});

test('a duplicate conflict key does not reach the insert', () => {
  // One repeated security failed the entire rebuild - every fund score as
  // well as every consensus row. The cost is out of all proportion.
  const rows = [
    { scope_type: 'stock', scope_id: 'X', as_of: '2026-06-30', signal_type: 'consensus', score: 1 },
    { scope_type: 'stock', scope_id: 'X', as_of: '2026-06-30', signal_type: 'consensus', score: 2 },
    { scope_type: 'fund', scope_id: 'M', as_of: '2026-06-30', signal_type: 'conviction', score: 3 },
  ];
  const { rows: kept, dropped } = dedupeSignalRows(rows);
  assert.equal(kept.length, 2);
  assert.equal(dropped.length, 1);
});

test('rows differing in any part of the key are all kept', () => {
  const rows = [
    { scope_type: 'stock', scope_id: 'X', as_of: '2026-06-30', signal_type: 'consensus' },
    { scope_type: 'fund', scope_id: 'X', as_of: '2026-06-30', signal_type: 'consensus' },
    { scope_type: 'stock', scope_id: 'Y', as_of: '2026-06-30', signal_type: 'consensus' },
    { scope_type: 'stock', scope_id: 'X', as_of: '2026-03-31', signal_type: 'consensus' },
    { scope_type: 'stock', scope_id: 'X', as_of: '2026-06-30', signal_type: 'conviction' },
  ];
  assert.equal(dedupeSignalRows(rows).rows.length, 5);
});
