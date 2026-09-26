import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { seedManagers } from '../services/institutionalHoldingsService.js';

/** A client that records the upsert it was given and answers as told. */
function stubClient(error = null) {
  const calls = [];
  return {
    calls,
    from() {
      return {
        upsert(rows, options) { calls.push({ rows, options }); return Promise.resolve({ error }); },
      };
    },
  };
}

test('a seed failure does not take the read path down with it', () => {
  // This is what happened: seeding runs before every read of every
  // institutional surface, so one rejected row emptied all of them and the
  // page showed "duplicate key value violates unique constraint
  // institutional_managers_slug_key" to the public.
  const client = stubClient({ message: 'duplicate key value violates unique constraint "institutional_managers_slug_key"' });
  return seedManagers(client).then((result) => {
    assert.equal(result.ok, false);
    assert.match(result.error, /institutional_managers_slug_key/);
  });
});

test('a caller that cannot proceed without the roster still gets the error', () => {
  // A collection run is about to crawl the managers it seeded; serving a
  // stale roster there would silently crawl the wrong set.
  const client = stubClient({ message: 'boom' });
  return assert.rejects(() => seedManagers(client, { required: true }), /boom/);
});

test('managers are matched on the slug, not the CIK', () => {
  // The slug identifies a manager to us - it is in the URL, it is stable, we
  // choose it. The CIK belongs to the filer and can change: BlackRock Finance
  // stopped filing and BlackRock, Inc. took over under a different number.
  // Conflicting on the CIK turns correcting one into an insert, and that
  // insert carries a slug the old row still holds.
  const client = stubClient();
  return seedManagers(client).then(() => {
    assert.equal(client.calls[0].options.onConflict, 'slug');
  });
});

test('changing a manager CIK is an update, not a second row', () => {
  // The regression this exists to prevent, stated as the property that makes
  // it safe: one row per slug in what is sent, matched on that slug.
  const client = stubClient();
  return seedManagers(client).then(() => {
    const { rows, options } = client.calls[0];
    const slugs = rows.map((r) => r.slug);
    assert.equal(new Set(slugs).size, slugs.length, 'two rows sharing a slug would collide on the way in');
    assert.equal(options.onConflict, 'slug');
  });
});

test('the seed list itself carries no duplicate slug or CIK', () => {
  // Both columns are unique in the table, so a duplicate in this file is a
  // failed write at startup rather than a bad row.
  const source = readFileSync(new URL('../services/institutionalHoldingsService.js', import.meta.url), 'utf8');
  const slugs = [...source.matchAll(/\{ slug: '([a-z0-9-]+)', display_name:/g)].map((m) => m[1]);
  const ciks = [...source.matchAll(/cik: '(\d{10})'/g)].map((m) => m[1]);
  assert.ok(slugs.length > 40, `expected the full roster, found ${slugs.length}`);
  assert.equal(new Set(slugs).size, slugs.length, 'duplicate slug in DEFAULT_MANAGERS');
  assert.equal(new Set(ciks).size, ciks.length, 'duplicate CIK in DEFAULT_MANAGERS');
});
