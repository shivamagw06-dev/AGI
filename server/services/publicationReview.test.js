import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  REVIEW_STATUSES, REVIEW_BATCH_LIMIT, reviewPatch, reviewRow,
} from './publicationReviewService.js';

const ID = (n) => `0000000${n}-1111-2222-3333-444444444444`;

describe('what a person may decide', () => {
  test('a decision is always recorded as a person', () => {
    // The rule's approvals are recomputed on every import. A page that
    // presents one as the other is the conflation reviewed_by exists to
    // prevent, and the import script printed exactly that for a day.
    const { patch } = reviewPatch({ ids: [ID(1)], status: 'approved', at: 'T' });
    assert.deepEqual(patch, { status: 'approved', reviewed_by: 'person', reviewed_at: 'T' });
  });

  test('rejecting is as available as approving', () => {
    // A queue whose only button is "approve" launders the extractor's
    // mistakes, and the extractor published a balance-sheet row, five date
    // ranges and a mitigation-as-hazard inside one day.
    assert.deepEqual(REVIEW_STATUSES, ['approved', 'rejected']);
    assert.equal(reviewPatch({ ids: [ID(1)], status: 'rejected' }).patch.status, 'rejected');
  });

  test('a rule cannot be impersonated through this path', () => {
    assert.match(reviewPatch({ ids: [ID(1)], status: 'pending' }).error, /status must be one of/);
    assert.ok(reviewPatch({ ids: [ID(1)], status: 'rule' }).error);
    assert.ok(reviewPatch({ ids: [ID(1)] }).error);
  });
});

describe('decisions are made on claims that were shown', () => {
  test('nothing selected decides nothing', () => {
    assert.match(reviewPatch({ ids: [], status: 'approved' }).error, /no claims were selected/);
    assert.ok(reviewPatch({ status: 'approved' }).error);
  });

  test('an id that is not a claim id is refused, and named', () => {
    // The route takes ids rather than a filter, so a malformed one is a
    // caller mistake worth reporting verbatim.
    const found = reviewPatch({ ids: [ID(1), 'why', 'all'], status: 'approved' });
    assert.match(found.error, /not a claim id: why, all/);
  });

  test('the same claim twice is one claim', () => {
    const { ids } = reviewPatch({ ids: [ID(1), ID(1), ID(2)], status: 'approved' });
    assert.deepEqual(ids, [ID(1), ID(2)]);
  });

  test('a batch is capped, and the count is in the message', () => {
    // Deduplicated before the cap, so repeating an id does not consume the
    // allowance.
    const many = Array.from({ length: REVIEW_BATCH_LIMIT + 1 },
      (unused, index) => `${String(index).padStart(8, '0')}-1111-2222-3333-444444444444`);
    assert.match(reviewPatch({ ids: many, status: 'approved' }).error,
      new RegExp(`at most ${REVIEW_BATCH_LIMIT} claims at a time, got ${REVIEW_BATCH_LIMIT + 1}`));
    assert.ok(!reviewPatch({ ids: many.slice(0, REVIEW_BATCH_LIMIT), status: 'approved' }).error);
    assert.ok(!reviewPatch({ ids: [...many.slice(0, REVIEW_BATCH_LIMIT), many[0]], status: 'approved' }).error);
  });
});

describe('what a reviewer is shown', () => {
  const ROW = {
    id: ID(1), kind: 'chain_claim', slot: 'what_changed', basis: 'derived',
    metric: 'expense ratio', segment: 'geico', segment_source: 'in_sentence',
    themes: ['retention'], change: { delta: 2.7, direction: 'up' }, figures: [],
    issuer: null, unit: null, status: 'pending', reviewed_by: null,
    source_excerpt: 'GEICO’s expense ratio was 12.4% in 2025.',
    created_at: '2026-09-13T00:00:00Z',
    institutional_managers: { display_name: 'Berkshire Hathaway', slug: 'berkshire-hathaway' },
    manager_publications: { title: '2025 Annual Report', as_of_date: '2025-12-31' },
  };

  test('the sentence and the two things that qualify it always travel', () => {
    // basis says whose arithmetic it is; segment_source says whether the
    // business was named in the sentence or inherited from a heading, which
    // is the difference between evidence and a guess.
    const shown = reviewRow(ROW);
    assert.equal(shown.source_excerpt, ROW.source_excerpt);
    assert.equal(shown.basis, 'derived');
    assert.equal(shown.segment_source, 'in_sentence');
    assert.equal(shown.manager, 'Berkshire Hathaway');
    assert.equal(shown.publication, '2025 Annual Report');
  });

  test('nothing internal reaches the reviewer that is not about the claim', () => {
    // created_at and the embedded rows are joined for ordering and labels,
    // not for display, and a select('*') passed straight through is how
    // internal columns end up on a surface.
    assert.deepEqual(Object.keys(reviewRow(ROW)).sort(), [
      'as_of_date', 'basis', 'change', 'figures', 'id', 'issuer', 'kind', 'manager',
      'manager_slug', 'metric', 'publication', 'reviewed_by', 'segment', 'segment_source',
      'slot', 'source_excerpt', 'status', 'themes', 'unit',
    ]);
  });

  test('a holdings row survives having no slot and no segment', () => {
    const shown = reviewRow({ ...ROW, slot: null, segment: null, segment_source: null,
      themes: null, kind: 'disclosed_holding', issuer: 'Apple Inc.', unit: 'millions' });
    assert.equal(shown.slot, null);
    assert.deepEqual(shown.themes, []);
    assert.equal(shown.issuer, 'Apple Inc.');
  });

  test('a row with no manager joined does not throw', () => {
    const shown = reviewRow({ id: ID(2), source_excerpt: 'x' });
    assert.equal(shown.manager, null);
    assert.equal(shown.publication, null);
  });
});
