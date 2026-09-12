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
