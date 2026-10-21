import test from 'node:test';
import assert from 'node:assert/strict';
import { backtestStrategyKey } from '../services/institutionalResearchLayerService.js';

test('the same strategy is one key however it is asked for', () => {
  // The property the resumable sweep rests on: it computes the key to decide
  // what has already run, and a key that differs by a clamp from the one the
  // run writes under makes every manager look outstanding for ever.
  assert.equal(
    backtestStrategyKey({ topN: 10, quarters: 20 }),
    backtestStrategyKey({ topN: 10, quarters: 20, transactionCostBps: 10 }),
  );
});

test('depth is clamped, so out-of-range requests share the row they write', () => {
  // runInstitutionalBacktest clamps to 2..48. Asking for sixty quarters stores
  // a forty-eight quarter run, and asking again must find it.
  assert.equal(backtestStrategyKey({ quarters: 60 }), backtestStrategyKey({ quarters: 48 }));
  assert.equal(backtestStrategyKey({ quarters: 1 }), backtestStrategyKey({ quarters: 2 }));
  assert.equal(backtestStrategyKey({ quarters: 0 }), backtestStrategyKey({ quarters: 12 }), 'zero falls back to the default, not to the floor');
});

test('breadth is clamped the same way', () => {
  assert.equal(backtestStrategyKey({ topN: 500 }), backtestStrategyKey({ topN: 50 }));
  assert.equal(backtestStrategyKey({ topN: 0 }), backtestStrategyKey({ topN: 10 }), 'zero falls back to the default');
});

test('depth and breadth both appear in the key', () => {
  // Without depth, a twelve-quarter and a forty-quarter run for one manager on
  // one day would overwrite each other and the stored row could not say which
  // it was.
  assert.notEqual(backtestStrategyKey({ quarters: 12 }), backtestStrategyKey({ quarters: 40 }));
  assert.notEqual(backtestStrategyKey({ topN: 10 }), backtestStrategyKey({ topN: 25 }));
  assert.notEqual(backtestStrategyKey({ transactionCostBps: 10 }), backtestStrategyKey({ transactionCostBps: 25 }));
});

test('the key is readable, so a stored row says what it is', () => {
  assert.match(backtestStrategyKey({ topN: 10, quarters: 20 }), /^top_10_q20_[0-9a-f]{6}$/);
});

test('nothing in yields the default strategy, without throwing', () => {
  assert.equal(backtestStrategyKey(), backtestStrategyKey({ topN: 10, quarters: 12, transactionCostBps: 10 }));
});
