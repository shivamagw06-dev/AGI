import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { FACT_COLUMNS, factRows } from './publicationRows.js';
import { intelligenceChain } from './publicationIntelligence.js';
import { extractDisclosedHoldings } from './publicationFacts.js';

const here = dirname(fileURLToPath(import.meta.url));
const PROSE = readFileSync(
  join(here, '..', 'tests', 'fixtures', 'publications', 'berkshire-2025-prose.txt'), 'utf8');
const TABLES = readFileSync(
  join(here, '..', 'tests', 'fixtures', 'publications', 'berkshire-2025-equity-tables.txt'), 'utf8');

const IDS = { publicationId: '11111111-1111-1111-1111-111111111111',
  managerId: '22222222-2222-2222-2222-222222222222' };

const build = () => factRows({
  ...IDS,
  holdings: extractDisclosedHoldings(TABLES),
  chain: intelligenceChain(PROSE),
  now: '2026-09-13T00:00:00.000Z',
});

describe('every row has every column', () => {
  test('a holdings row and a claim row are the same shape', () => {
    // PostgREST sends the array as one INSERT whose column list is the union
    // of every key present, and a row omitting one of those keys gets NULL -
    // not the column's DEFAULT. Holdings rows relied on status defaulting to
    // 'pending' for as long as no other row set it. The moment claims carried
    // a status so some could be auto-approved, status joined the column list
    // and the nine holdings rows were sent as null:
    //
    //   null value in column "status" ... violates not-null constraint
    //
    // It failed loudly because status is NOT NULL. A nullable column would
    // have taken the null silently, which is what this test is really for.
    const { rows } = build();
    assert.ok(rows.length > 20);
    const expected = [...FACT_COLUMNS].sort();
    for (const row of rows) {
      assert.deepEqual(Object.keys(row).sort(), expected,
        `row shape drifted: ${row.source_excerpt}`);
    }
  });

  test('no row leaves status unset, whatever kind it is', () => {
    // The specific column that failed, asserted on its own so a future change
    // to FACT_COLUMNS cannot quietly drop it from the shape test above.
    for (const row of build().rows) {
      assert.ok(['pending', 'approved'].includes(row.status), `status was ${row.status}`);
    }
  });

  test('a reviewed row records who reviewed it and an unreviewed one does not', () => {
    // The table's pair constraint. Asserted here because a violation shows up
    // in production as a failed write of the whole chunk.
    for (const row of build().rows) {
      if (row.status === 'pending') {
        assert.equal(row.reviewed_by, null);
        assert.equal(row.reviewed_at, null);
      } else {
        assert.ok(row.reviewed_by, 'an approved row with no reviewer');
        assert.ok(row.reviewed_at, 'an approved row with no review time');
      }
    }
  });
});

describe('a person\'s decision survives a re-import', () => {
  const claimFor = (rows, text) => rows.find((row) => row.source_excerpt === text);
  const CAUSE = 'Insurance investment income increased $4.1 billion in 2024 compared to 2023, '
    + 'driven by higher interest income from short-term investments.';

  test('an approved claim stays approved when the document is extracted again', () => {
    // The upsert updates every column it is given, so a second run of the same
    // document rewrote status to 'pending' and discarded 142 claims someone
    // had read and approved. Re-extracting is routine - every tightening of
    // the extractor calls for it - and it must not throw away the one part of
    // this pipeline that cost a person their attention.
    const chain = intelligenceChain(CAUSE);
    const fresh = factRows({ ...IDS, chain });
    assert.equal(claimFor(fresh.rows, CAUSE).status, 'pending');

    const kept = factRows({ ...IDS, chain,
      reviewed: [{ slot: 'why', source_excerpt: CAUSE, status: 'approved',
        reviewed_by: 'person', reviewed_at: '2026-09-13T00:00:00.000Z' }] });
    const row = kept.rows.find((item) => item.slot === 'why');
    assert.equal(row.status, 'approved');
    assert.equal(row.reviewed_by, 'person');
    assert.equal(row.reviewed_at, '2026-09-13T00:00:00.000Z');
  });

  test('a rejected claim is not quietly re-approved by a rule', () => {
    // The rule runs again on every import. Without carrying the rejection
    // forward, a claim a person threw out comes back approved.
    const amount = 'our insurance float stood at $176 billion.';
    const kept = factRows({ ...IDS, chain: intelligenceChain(amount),
      reviewed: [{ slot: 'how_much', source_excerpt: amount, status: 'rejected',
        reviewed_by: 'person', reviewed_at: '2026-09-13T00:00:00.000Z' }] });
    const row = kept.rows.find((item) => item.slot === 'how_much');
    assert.equal(row.status, 'rejected');
    assert.equal(row.reviewed_by, 'person');
  });

  test('a rule\'s approval is recomputed, not carried', () => {
    // Which is what lets a tightened rule take back a claim it should not have
    // published. Only a person's decision is sticky.
    const amount = 'our insurance float stood at $176 billion.';
    const kept = factRows({ ...IDS, chain: intelligenceChain(amount),
      reviewed: [{ slot: 'how_much', source_excerpt: amount, status: 'rejected',
        reviewed_by: 'rule', reviewed_at: '2026-09-13T00:00:00.000Z' }] });
    assert.equal(kept.rows.find((item) => item.slot === 'how_much').status, 'approved');
  });

  test('a row the extractor no longer produces is reported, not deleted', () => {
    // An upsert only writes, so a claim the extractor has stopped believing
    // keeps whatever status it had - which is how a balance-sheet row stayed
    // approved on the page after the rule that admitted it was fixed.
    const gone = 'Treasury Bills 112,811 89,705 Investments in and advances to consolidated '
      + 'subsidiaries 604,100 568,987 and other assets 8,871 13,417';
    const built = factRows({ ...IDS, chain: intelligenceChain(CAUSE),
      reviewed: [{ slot: 'how_much', source_excerpt: gone, status: 'approved',
        reviewed_by: 'rule', reviewed_at: null }] });
    assert.equal(built.stale.length, 1);
    assert.equal(built.stale[0].source_excerpt, gone);
    // And it is not in the write, so nothing revives it.
    assert.ok(!built.rows.some((row) => row.source_excerpt === gone));
  });

  test('nothing stale when the extraction still produces everything', () => {
    const chain = intelligenceChain(CAUSE);
    const built = factRows({ ...IDS, chain,
      reviewed: [{ slot: 'why', source_excerpt: CAUSE, status: 'approved',
        reviewed_by: 'person', reviewed_at: null }] });
    assert.deepEqual(built.stale, []);
  });
});

describe('what the rows say', () => {
  test('holdings always wait for a person', () => {
    // The figures carry a scale read off a header line elsewhere on the page,
    // and a thousand-fold error has shipped from this codebase once already.
    const holdings = build().rows.filter((row) => row.kind === 'disclosed_holding');
    assert.ok(holdings.length > 0);
    for (const row of holdings) {
      assert.equal(row.status, 'pending');
      assert.equal(row.slot, null);
      assert.ok(row.issuer);
    }
  });

  test('an approved claim is approved by rule, and only in the two quotation slots', () => {
    const approved = build().rows.filter((row) => row.status === 'approved');
    assert.ok(approved.length > 0);
    for (const row of approved) {
      assert.equal(row.reviewed_by, 'rule');
      assert.ok(['how_much', 'what_changed'].includes(row.slot),
        `${row.slot} was approved by rule`);
    }
  });

  test('an empty array becomes an empty write, not a row of nulls', () => {
    const { rows, collapsed } = factRows({ ...IDS });
    assert.deepEqual(rows, []);
    assert.equal(collapsed, 0);
  });

  test('the same sentence in the same slot collapses and is counted', () => {
    const line = 'our insurance float stood at $176 billion at year-end.';
    const { rows, collapsed } = factRows({
      ...IDS,
      chain: intelligenceChain(`${line}\n\nFiller sentence sits between them here.\n\n${line}`),
    });
    assert.equal(rows.filter((row) => row.slot === 'how_much').length, 1);
    assert.equal(collapsed, 0, 'the extractor should already have deduplicated');
    const keys = rows.map((row) => JSON.stringify([row.slot, row.source_excerpt]));
    assert.equal(new Set(keys).size, keys.length);
  });
});
