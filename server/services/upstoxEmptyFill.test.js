import { test } from 'node:test';
import assert from 'node:assert/strict';
import { summarizeStatementBatch } from './upstoxEmptyFill.js';

test('rate-limited statement names remain eligible for retry', () => {
  const result = summarizeStatementBatch(['ACME', 'BETA'], {
    errors: [{ symbol: 'BETA', status: 429 }],
    ingest: { results: [{ symbol: 'ACME', ok: true }] },
  });
  assert.deepEqual(result.settled, ['ACME']);
  assert.equal(result.filledCount, 1);
  assert.equal(result.failedCount, 0);
  assert.equal(result.rateLimitedCount, 1);
});

test('whole-batch rate limit does not count missing data as a failure', () => {
  const result = summarizeStatementBatch(['ACME', 'BETA'], { status: 429 });
  assert.deepEqual(result.settled, []);
  assert.equal(result.failedCount, 0);
  assert.equal(result.rateLimitedCount, 2);
});
