import test from 'node:test';
import assert from 'node:assert/strict';
import { paged } from '../services/institutionalResearchLayerService.js';

/** A builder that hands back `total` rows a page at a time, like PostgREST. */
const source = (total, pageSize = 1000) => {
  const calls = [];
  const build = () => ({
    range: async (from, to) => {
      calls.push([from, to]);
      const slice = [];
      for (let i = from; i <= Math.min(to, total - 1); i += 1) slice.push({ i });
      // The ceiling is the point: a real response never exceeds the page size.
      return { data: slice.slice(0, pageSize), error: null };
    },
  });
  return { build, calls };
};

test('a result larger than one page is read whole', () => {
  // The bug this exists for: an unpaged read of 2,600 rows returns 1,000 and
  // reports success, and nothing downstream can tell.
  const { build, calls } = source(2_600);
  return paged(build).then((rows) => {
    assert.equal(rows.length, 2_600);
    assert.equal(calls.length, 3);
  });
});

test('a short page ends the read without an extra request', () => {
  const { build, calls } = source(400);
  return paged(build).then((rows) => {
    assert.equal(rows.length, 400);
    assert.equal(calls.length, 1);
  });
});

test('an exactly-full final page still terminates', () => {
  // 2,000 rows in two full pages: the loop cannot stop on a short page, so it
  // must ask once more and get nothing. Without that it would return 2,000
  // rows and never know whether there were more.
  const { build, calls } = source(2_000);
  return paged(build).then((rows) => {
    assert.equal(rows.length, 2_000);
    assert.equal(calls.length, 3);
  });
});

test('an empty result is empty, not an error', () => {
  const { build } = source(0);
  return paged(build).then((rows) => assert.deepEqual(rows, []));
});

test('the ceiling throws rather than returning a short answer', () => {
  // The whole point of the helper is that a truncated read must not be able to
  // pass for a complete one. Silently stopping at the ceiling would reproduce
  // the bug it was written to fix.
  const { build } = source(10_000);
  return assert.rejects(
    () => paged(build, { maxRows: 3_000, label: 'holdings' }),
    /holdings exceeded its 3000-row ceiling/,
  );
});

test('an error from the source is raised, not swallowed', () => {
  const build = () => ({ range: async () => ({ data: null, error: new Error('statement timeout') }) });
  return assert.rejects(() => paged(build), /statement timeout/);
});
