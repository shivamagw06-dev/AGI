import assert from 'node:assert/strict';
import test from 'node:test';
import { scopeQueueToLiveUniverse } from './confluenceCandidateScope.js';

test('validation queue keeps only live-universe names with captured anchors', () => {
  const queue = {
    completeness: { total: 3 },
    items: [
      { symbol: 'RELIANCE', anchors: { captured_at: '2026-08-10T04:00:00Z' } },
      { symbol: 'TCS', anchors: null },
      { symbol: 'OUTSIDE', anchors: { captured_at: '2026-08-10T04:00:00Z' } },
    ],
  };
  const universe = { members: [{ symbol: 'RELIANCE' }, { symbol: 'TCS' }] };
  const scoped = scopeQueueToLiveUniverse(queue, universe);
  assert.deepEqual(scoped.items.map((item) => item.symbol), ['RELIANCE']);
  assert.equal(scoped.completeness.validation_candidates, 1);
  assert.equal(scoped.completeness.excluded_without_live_identity_or_anchors, 2);
});
