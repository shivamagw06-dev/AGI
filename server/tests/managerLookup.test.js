import test from 'node:test';
import assert from 'node:assert/strict';
import { isUuid } from '../services/institutionalResearchLayerService.js';

test('a slug is not mistaken for an id', () => {
  // The bug: matching slug and id together in one `or` sends the slug to a
  // uuid column, and Postgres rejects the whole clause -
  // `invalid input syntax for type uuid: "berkshire-hathaway"`.
  assert.equal(isUuid('berkshire-hathaway'), false);
  assert.equal(isUuid('blackrock'), false);
  assert.equal(isUuid(''), false);
  assert.equal(isUuid(null), false);
});

test('a real uuid is recognised, in either case', () => {
  assert.equal(isUuid('052c581b-2333-4e55-9f91-1cee9406c74a'), true);
  assert.equal(isUuid('052C581B-2333-4E55-9F91-1CEE9406C74A'), true);
});

test('something uuid-shaped but wrong is refused', () => {
  // Sent to a uuid column these fail the same way a slug does, so they must
  // take the slug path and simply find nothing.
  assert.equal(isUuid('052c581b-2333-4e55-9f91-1cee9406c74'), false);
  assert.equal(isUuid('052c581b23334e559f911cee9406c74a'), false);
  assert.equal(isUuid('zzzzzzzz-2333-4e55-9f91-1cee9406c74a'), false);
});
