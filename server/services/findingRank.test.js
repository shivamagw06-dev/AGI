import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { largestAmount, dedupe, materiality, rank } from './findingRank.js';
import { figuresIn } from './publicationIntelligence.js';

// Verbatim from NVIDIA's Q2 FY2027 10-Q, as the queue returned them.
const claim = (slot, source_excerpt) => ({ slot, source_excerpt, figures: figuresIn(source_excerpt) });
const NVIDIA = [
  claim('what_happened', 'We have significantly increased our supply and capacity commitments '
    + 'from $119 billion last quarter to $279 billion as of July 26, 2026 to meet future demand.'),
  claim('what_happened', 'SB Energy Corp. guarantees – In August 2026, we entered into guarantees, '
    + 'capped at a total of $105 billion, to provide credit support on a land, power, and shell '
    + 'buildout with affiliates of SB Energy Corp.'),
  claim('what_happened', 'As of July 26, 2026, we had $56.6 billion in cash, cash equivalents, and '
    + 'marketable debt securities as well as $42.8 billion of marketable equity securities.'),
  claim('why', 'As a result of these requirements, we incurred a $4.5 billion charge in the first '
    + 'quarter of fiscal year 2026 associated with H20 for excess inventory and purchase obligations.'),
  // The same buyback, three times, in three sentences.
  claim('what_happened', 'Unregistered Sales of Equity Securities and Use of Proceeds Issuer '
    + 'Purchases of Equity Securities We repurchased 94 million and 203 million shares of our '
    + 'common stock for $19.7 billion and $39.8 billion during the second quarter and first half '
    + 'of fiscal year 2027, respectively.'),
  claim('what_happened', 'Capital Return to Shareholders In the second quarter and first half of '
    + 'fiscal year 2027, we repurchased 94 million and 203 million shares of our common stock for '
    + '$19.7 billion and $39.8 billion, respectively.'),
  claim('how', 'Capital Return to Shareholders In the second quarter and first half of fiscal '
    + 'year 2027, we repurchased 94 million and 203 million shares of our common stock for '
    + '$19.7 billion and $39.8 billion, respectively.'),
  // Boilerplate, which states no amount at all.
  claim('risks', 'Any of these risks may adversely affect our business, financial condition, '
    + 'results of operations or cash flows.'),
];

describe('the amount a finding states', () => {
  test('the largest money figure, in units', () => {
    assert.equal(largestAmount(NVIDIA[0]).value, 279e9);
    assert.equal(largestAmount(NVIDIA[1]).value, 105e9);
    assert.equal(largestAmount(NVIDIA[3]).value, 4.5e9);
  });

  test('a percentage is not an amount', () => {
    // "up 117% from a year ago" is a change, not a size, and ranking a list by
    // it would put 117 above $105 billion.
    const percent = claim('what_happened', 'Data Center revenue was up 117% from a year ago.');
    assert.equal(largestAmount(percent), null);
  });

  test('a sentence with no figure states no amount', () => {
    assert.equal(largestAmount(NVIDIA[7]), null);
  });
});

describe('the same fact said twice', () => {
  test('one buyback, reported in three sentences, is two findings', () => {
    // Two under what_happened collapse; the one filed as a response is a
    // different reading of the same figure and stays.
    const buybacks = dedupe(NVIDIA).filter((c) => /repurchased 94 million/.test(c.source_excerpt));
    assert.equal(buybacks.length, 2);
    assert.deepEqual([...new Set(buybacks.map((c) => c.slot))].sort(), ['how', 'what_happened']);
  });

  test('the fuller sentence survives', () => {
    // Both state $39.8 billion. The longer one says it was an issuer purchase
    // of equity securities, which is the part a reader cannot reconstruct.
    const kept = dedupe(NVIDIA).find((c) => c.slot === 'what_happened'
      && /repurchased 94 million/.test(c.source_excerpt));
    assert.match(kept.source_excerpt, /Unregistered Sales of Equity Securities/);
  });

  test('a finding with no amount is never merged away', () => {
    assert.ok(dedupe(NVIDIA).some((c) => c.slot === 'risks'));
  });
});

describe('how large, against what the company reported', () => {
  // NVIDIA's own disclosures, from the same filing.
  const against = { cash: 56.6e9 };

  test('a share is reported with the denominator it used', () => {
    const found = materiality(NVIDIA[1], { against });
    assert.equal(found.of, 'cash');
    assert.ok(Math.abs(found.share - 105e9 / 56.6e9) < 1e-9);
    assert.match(found.basis, /cash as reported/);
  });

  test('with nothing to compare against, it says so', () => {
    const found = materiality(NVIDIA[1], {});
    assert.equal(found.share, null);
    assert.match(found.basis, /size alone/);
    // The amount is still there, so a list can still be ordered.
    assert.equal(found.amount, 105e9);
  });

  test('a denominator that is zero or missing is not used', () => {
    for (const bad of [{ revenue: 0 }, { revenue: null }, { revenue: 'lots' }]) {
      assert.equal(materiality(NVIDIA[1], { against: bad }).share, null);
    }
  });
});

describe('the order a reader should read them in', () => {
  test('the largest disclosures come first, and boilerplate does not appear', () => {
    const top = rank(NVIDIA, { against: { cash: 56.6e9 }, limit: 3 });
    assert.equal(top.length, 3);
    assert.match(top[0].claim.source_excerpt, /\$279 billion/);
    assert.match(top[1].claim.source_excerpt, /capped at a total of \$105 billion/);
    // A sentence stating no amount cannot be ranked and is not padded in.
    assert.equal(rank(NVIDIA, {}).some((e) => /Any of these risks/.test(e.claim.source_excerpt)), false);
  });

  test('normalised findings never interleave with unnormalised ones', () => {
    // A figure with a denominator and one without are not comparable, and
    // sorting them together invents a precedence between them.
    const mixed = rank(NVIDIA, { against: { cash: 56.6e9 } });
    const firstUnnormalised = mixed.findIndex((entry) => entry.share === null);
    if (firstUnnormalised >= 0) {
      assert.ok(mixed.slice(firstUnnormalised).every((entry) => entry.share === null));
    }
  });
});
