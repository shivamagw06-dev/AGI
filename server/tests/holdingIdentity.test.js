import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

/**
 * The deduplication key in code and the uniqueness rule in the database have
 * to describe the same thing. When they drifted apart, the code emitted two
 * rows the index considered one, Postgres refused the batch, and the manager
 * was not ingested - the failure landing on ingestion rather than anywhere
 * near the disagreement that caused it.
 */
const service = readFileSync(new URL('../services/institutionalHoldingsService.js', import.meta.url), 'utf8');
const migration = readFileSync(
  new URL('../../supabase/migrations/20260908090000_holding_identity_share_type.sql', import.meta.url),
  'utf8',
);

function codeKeyFields() {
  const match = service.match(/return \[row\.cusip,([\s\S]*?)\]\s*\n\s*\.map/);
  assert.ok(match, 'filingKey should still be an array literal of row fields');
  return ['cusip', ...[...match[1].matchAll(/row\.([a-z_]+)/g)].map((m) => m[1])];
}

function indexKeyFields() {
  const body = migration.slice(migration.lastIndexOf('create unique index'));
  return [...body.matchAll(/(?:coalesce\()?\s*\b(cusip|title_of_class|share_type|put_call|investment_discretion|other_manager)\b/g)]
    .map((m) => m[1]);
}

test('every field the code deduplicates on is part of the uniqueness rule', () => {
  // The direction that breaks ingestion. A field the code distinguishes but
  // the index does not means two rows go in that the database calls one.
  const missing = codeKeyFields().filter((field) => !indexKeyFields().includes(field));
  assert.deepEqual(missing, [], `not in the unique index: ${missing.join(', ')}`);
});

test('share_type specifically is in both', () => {
  // The field that actually drifted. SH and PRN against one CUSIP is an
  // equity position and a convertible note - different holdings, different
  // values, different prices - and two managers failed to ingest over it.
  assert.ok(codeKeyFields().includes('share_type'), 'filingKey must distinguish shares from principal');
  assert.ok(indexKeyFields().includes('share_type'), 'the unique index must distinguish them too');
});
