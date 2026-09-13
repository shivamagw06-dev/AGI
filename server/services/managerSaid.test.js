import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { buildSaid } from './managerSaidService.js';

const PUBLICATIONS = [{ id: 'p1', title: '2025 Annual Report', as_of_date: '2025-12-31',
  source_url: null, pasted_at: '2026-09-13T00:00:00Z', digest: 'secret', manager_id: 'm1' }];

const fact = (over) => ({ kind: 'chain_claim', status: 'approved', slot: 'how_much',
  basis: 'stated', source_excerpt: 'x', ...over });

const FACTS = [
  fact({ slot: 'how_much', metric: 'float',
    source_excerpt: 'our insurance float stood at $176 billion at year-end.' }),
  fact({ slot: 'what_changed', basis: 'derived',
    source_excerpt: 'GEICO’s loss ratio was 71.8% in 2024 and 81.0% in 2023.' }),
  fact({ slot: 'why', status: 'pending',
    source_excerpt: 'Our investment in Kraft Heinz has been disappointing.' }),
  fact({ slot: 'why', status: 'pending', source_excerpt: 'Another cause nobody has read yet.' }),
  fact({ slot: 'expectations', status: 'pending',
    source_excerpt: 'we expect to write less reinsurance premium.' }),
  fact({ slot: 'how_much', metric: 'impairment',
    source_excerpt: 'We recorded an impairment charge of $5.0 billion on Kraft Heinz.' }),
  { kind: 'disclosed_holding', status: 'pending', issuer: 'Apple Inc.', percent_owned: 1.6,
    market_value: 61962, cost_basis: 6255, unit: 'millions', source_excerpt: 'Apple row' },
];

const said = () => buildSaid({
  publications: PUBLICATIONS,
  facts: FACTS,
  holdingNames: ['KRAFT HEINZ CO', 'APPLE INC', 'BERKSHIRE HATHAWAY INC'],
  managerName: 'Berkshire Hathaway',
});

describe('what reaches the page', () => {
  test('only approved claims are published', () => {
    const published = said().by_step.flatMap((group) => group.claims);
    assert.equal(published.length, 3);
    assert.ok(published.every((claim) => claim.status === 'approved'));
  });

  test('pending claims are counted by step, not hidden', () => {
    // A page that simply omits them implies the document was silent on that
    // step, when 142 causes and 15 stated expectations are sitting in a queue.
    assert.deepEqual(said().awaiting_review, [
      { slot: 'why', question: 'Why did it happen?', pending: 2 },
      { slot: 'expectations', question: 'What does management expect next?', pending: 1 },
    ]);
  });

  test('steps come back in chain order with the question attached', () => {
    // The page should not have to know that "how_much" is asked after "why".
    assert.deepEqual(said().by_step.map((group) => group.slot), ['how_much', 'what_changed']);
    assert.equal(said().by_step[0].question, 'How much?');
  });

  test('the two unfillable steps travel with their reason', () => {
    const gaps = said().unreachable;
    assert.deepEqual(gaps.map((gap) => gap.slot), ['catalysts', 'so_what']);
    for (const gap of gaps) assert.match(gap.reason, /\S/);
  });

  test('the document digest does not reach the page', () => {
    // It is an internal identity for recognising a re-paste, and a select('*')
    // feeding straight through is how internal columns end up public.
    assert.deepEqual(Object.keys(said().publications[0]).sort(),
      ['as_of_date', 'id', 'pasted_at', 'source_url', 'title']);
  });
});

describe('what the fund said about a position', () => {
  test('a position is listed only where the filer wrote about it', () => {
    const holdings = said().by_holding;
    assert.deepEqual(holdings.map((entry) => entry.issuer), ['KRAFT HEINZ CO']);
    assert.equal(holdings[0].claims.length, 1);
  });

  test('a holding the filer only tabulated is absent, not empty', () => {
    // Berkshire did not decline to discuss Apple; it disclosed Apple in a
    // table and said nothing about it. An empty section would read as the
    // first and it is the second.
    assert.ok(!said().by_holding.some((entry) => entry.issuer === 'APPLE INC'));
    // The disclosure itself still comes through, so the position is visible.
    assert.equal(said().disclosed.length, 1);
    assert.equal(said().disclosed[0].issuer, 'Apple Inc.');
  });

  test('the manager is not a position in itself', () => {
    const built = buildSaid({
      publications: PUBLICATIONS,
      facts: [fact({ source_excerpt: 'Berkshire Hathaway produced $46 billion of cash flow.' })],
      holdingNames: ['BERKSHIRE HATHAWAY INC'],
      managerName: 'Berkshire Hathaway',
    });
    assert.deepEqual(built.by_holding, []);
  });

  test('a pending claim about a holding is not published under it', () => {
    // "Our investment in Kraft Heinz has been disappointing" is the most
    // interesting sentence about that position and it is a `why`, so it waits.
    const texts = said().by_holding[0].claims.map((claim) => claim.source_excerpt);
    assert.ok(!texts.some((text) => /disappointing/.test(text)));
  });
});

describe('a manager with nothing pasted', () => {
  test('no publication is null, not an empty shell', () => {
    // So a page renders nothing for the forty-nine rather than a heading with
    // no rows under it.
    assert.equal(buildSaid({ publications: [], facts: FACTS }), null);
    assert.equal(buildSaid({}), null);
  });

  test('a publication with nothing approved yet still reports its queue', () => {
    const built = buildSaid({
      publications: PUBLICATIONS,
      facts: [fact({ slot: 'why', status: 'pending', source_excerpt: 'A cause.' })],
    });
    assert.deepEqual(built.by_step, []);
    assert.equal(built.approved_count, 0);
    assert.equal(built.awaiting_review[0].pending, 1);
  });
});

describe('the same sentence stored twice is shown once', () => {
  // Berkshire's annual report was pasted a second time, differed by a
  // character, and stored as a second publication. Facts are read by manager
  // rather than by publication, so all 452 approved claims rendered twice on
  // the live page. Pasting warns about this now; the page should not depend
  // on the warning being read.
  const OLD = { id: 'old', title: '2025 Annual Report', as_of_date: '2025-12-31',
    source_url: null, pasted_at: '2026-09-12T12:26:12Z', manager_id: 'm1' };
  const NEW = { id: 'new', title: '2025 Annual Report', as_of_date: '2025-12-31',
    source_url: null, pasted_at: '2026-09-13T05:47:28Z', manager_id: 'm1' };
  const SENTENCE = 'In 2025, BNSF’s operating margin improved to 34.5% from 32.0% in 2024.';

  const twice = (over = {}) => buildSaid({
    publications: [OLD, NEW],
    facts: [
      { kind: 'chain_claim', status: 'approved', slot: 'what_changed', basis: 'derived',
        publication_id: 'old', segment: 'from-the-old-one', source_excerpt: SENTENCE },
      { kind: 'chain_claim', status: 'approved', slot: 'what_changed', basis: 'derived',
        publication_id: 'new', segment: 'from-the-new-one', source_excerpt: SENTENCE },
      ...(over.facts || []),
    ],
    holdingNames: [],
    managerName: 'Berkshire Hathaway Inc',
  });

  test('one claim reaches the page, not two', () => {
    const built = twice();
    const rows = built.by_step.flatMap((group) => group.claims || []);
    assert.equal(rows.length, 1);
    assert.equal(built.approved_count, 1);
  });

  test('the surviving claim is the one from the newer publication', () => {
    // Asserting the count alone would pass just as happily on the stale row,
    // and a re-paste is how a document gets corrected.
    const rows = twice().by_step.flatMap((group) => group.claims || []);
    assert.equal(rows[0].segment, 'from-the-new-one');
  });

  test('a duplicated holding is shown once, from the newer publication', () => {
    const built = buildSaid({
      publications: [OLD, NEW],
      facts: [
        { kind: 'disclosed_holding', status: 'approved', issuer: 'Apple Inc.', percent_owned: 1.6,
          market_value: 61962, cost_basis: 6255, unit: 'millions',
          publication_id: 'old', source_excerpt: 'Apple row' },
        { kind: 'disclosed_holding', status: 'approved', issuer: 'Apple Inc.', percent_owned: 9.9,
          market_value: 61962, cost_basis: 6255, unit: 'millions',
          publication_id: 'new', source_excerpt: 'Apple row' },
      ],
      holdingNames: [], managerName: 'Berkshire Hathaway Inc',
    });
    assert.equal(built.disclosed.length, 1);
    assert.equal(built.disclosed[0].percent_owned, 9.9);
  });

  test('a pending duplicate is counted once, not twice', () => {
    const built = twice({ facts: [
      { kind: 'chain_claim', status: 'pending', slot: 'risks', publication_id: 'old',
        source_excerpt: 'A risk sentence nobody has read.' },
      { kind: 'chain_claim', status: 'pending', slot: 'risks', publication_id: 'new',
        source_excerpt: 'A risk sentence nobody has read.' },
    ] });
    const risks = built.awaiting_review.find((step) => step.slot === 'risks');
    assert.equal(risks.pending, 1);
  });

  test('two different sentences are both kept', () => {
    // The rule removes repeats, never content. A manager with an annual report
    // and a quarterly release has two documents, and both belong on the card.
    const built = twice({ facts: [
      { kind: 'chain_claim', status: 'approved', slot: 'what_changed', basis: 'derived',
        publication_id: 'new', source_excerpt: 'Premiums written increased $694 million.' },
    ] });
    const rows = built.by_step.flatMap((group) => group.claims || []);
    assert.equal(rows.length, 2);
    assert.deepEqual(new Set(rows.map((row) => row.source_excerpt)),
      new Set([SENTENCE, 'Premiums written increased $694 million.']));
  });

  test('the same sentence under different steps is not a duplicate', () => {
    // One sentence can answer two questions, which the database allows on
    // purpose - uniqueness there is (publication, slot, excerpt).
    const built = twice({ facts: [
      { kind: 'chain_claim', status: 'approved', slot: 'how_much', publication_id: 'new',
        metric: 'operating margin', source_excerpt: SENTENCE },
    ] });
    assert.equal(built.by_step.flatMap((group) => group.claims || []).length, 2);
  });
});

describe('a manager with more than one document', () => {
  // Berkshire's 2026 second-quarter report was pasted alongside the 2025
  // annual report. Both are Berkshire's own words and both belong on the card
  // - but the heading named only the newest, the claims were merged, and the
  // sentence shown under each question came out in whatever order the rows
  // arrived. A 2025 sentence read as this quarter's.
  const ANNUAL = { id: 'annual', title: '2025 Annual Report', as_of_date: '2025-12-31',
    source_url: null, pasted_at: '2026-09-13T05:47:28Z', manager_id: 'm1' };
  const QUARTER = { id: 'quarter', title: '2026 Q2', as_of_date: '2026-06-30',
    source_url: null, pasted_at: '2026-09-13T11:00:00Z', manager_id: 'm1' };

  const claim = (publication_id, source_excerpt) => ({
    kind: 'chain_claim', status: 'approved', slot: 'what_changed', basis: 'stated',
    publication_id, source_excerpt,
  });

  // Deliberately listed with the older document's claim first, which is the
  // order that produced the wrong sentence on the live page.
  const built = () => buildSaid({
    publications: [ANNUAL, QUARTER],
    facts: [
      claim('annual', 'Underwriting expenses increased $429 million (7.4%) in 2024.'),
      claim('quarter', 'Premiums written rose $1.2 billion in the second quarter of 2026.'),
    ],
    holdingNames: [], managerName: 'Berkshire Hathaway Inc',
  });

  test('the newest document’s sentence is the one shown', () => {
    const [group] = built().by_step;
    assert.equal(group.claims[0].source_excerpt,
      'Premiums written rose $1.2 billion in the second quarter of 2026.');
  });

  test('every claim names the document it came from', () => {
    const rows = built().by_step.flatMap((group) => group.claims);
    assert.deepEqual(rows.map((row) => row.document.title), ['2026 Q2', '2025 Annual Report']);
  });

  test('the older document is kept, not replaced', () => {
    // A newer report does not make last year's words untrue, and the chain is
    // the manager's own writing across everything it has published.
    const rows = built().by_step.flatMap((group) => group.claims);
    assert.equal(rows.length, 2);
    assert.equal(built().approved_count, 2);
  });

  test('a document carries what identifies it and not its digest', () => {
    const [group] = built().by_step;
    assert.deepEqual(Object.keys(group.claims[0].document).sort(),
      ['as_of_date', 'id', 'source_url', 'title']);
  });

  test('one document still labels each claim, for a caller that wants it', () => {
    const one = buildSaid({
      publications: [ANNUAL],
      facts: [claim('annual', 'Underwriting expenses increased $429 million (7.4%) in 2024.')],
      holdingNames: [], managerName: 'Berkshire Hathaway Inc',
    });
    assert.equal(one.by_step[0].claims[0].document.title, '2025 Annual Report');
  });
});
