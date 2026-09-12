import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { extractDisclosedHoldings, unitBefore, documentDigest } from './publicationFacts.js';

/**
 * The fixture is the equity section of Berkshire's 2025 annual report, as it
 * arrives when pasted out of the PDF.
 *
 *   server/tests/fixtures/publications/berkshire-2025-equity-tables.txt
 *
 * It is here rather than hand-written because the interesting parts are the
 * ones a clean example would not have: two tables in one document, a total row
 * under each, issuer names carrying their own punctuation, and figures whose
 * scale is declared on a header line rather than in the rows.
 */
const FIXTURE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '..', 'tests', 'fixtures', 'publications',
    'berkshire-2025-equity-tables.txt'),
  'utf8',
);

describe('holdings a manager discloses in its own report', () => {
  const facts = extractDisclosedHoldings(FIXTURE);

  test('both tables are read and the totals are not holdings', () => {
    // Nine issuers across two tables. A total row stored as a tenth holding
    // would double the book.
    assert.equal(facts.length, 9);
    assert.equal(facts.some((row) => /^total/i.test(row.issuer)), false);
  });

  test('the figures 13F never shows', () => {
    // Cost basis and percentage owned are in no filing. Apple at $6,255m
    // against $61,962m is a 9.9x holding, and the 13F shows only the second
    // number.
    const apple = facts.find((row) => row.issuer === 'Apple Inc.');
    assert.deepEqual(
      { percent: apple.percent_owned, cost: apple.cost_basis, market: apple.market_value, dividends: apple.dividends },
      { percent: 1.6, cost: 6255, market: 61962, dividends: 280 },
    );
  });

  test('the holdings that are not 13F-reportable at all', () => {
    // The reason this exists. Five Japanese trading houses, $35.4bn of market
    // value, invisible to every 13F because Japanese listings are not
    // reportable.
    const japan = ['Mitsubishi Corporation', 'ITOCHU Corporation', 'Mitsui & Co., Ltd.',
      'Marubeni Corporation', 'Sumitomo Corporation'];
    for (const issuer of japan) {
      assert.ok(facts.find((row) => row.issuer === issuer), issuer);
    }
    const total = japan.reduce((sum, issuer) =>
      sum + facts.find((row) => row.issuer === issuer).market_value, 0);
    // 35,368 is the total the report states for these five.
    assert.equal(total, 35368);
  });

  test('a name carrying its own punctuation survives', () => {
    // A greedy issuer match would swallow the percentage into the name, and
    // these are the names that would show it.
    assert.ok(facts.find((row) => row.issuer === 'Mitsui & Co., Ltd.'));
    assert.ok(facts.find((row) => row.issuer === "Moody's Corporation"));
    assert.ok(facts.find((row) => row.issuer === 'The Coca-Cola Company'));
  });

  test('every fact carries the line it came from', () => {
    // A reviewer approves a number against the text that produced it, not
    // against an assurance that the parse went well.
    for (const fact of facts) {
      assert.ok(fact.source_excerpt.includes(fact.issuer), fact.issuer);
      assert.ok(FIXTURE.includes(fact.source_excerpt), fact.issuer);
    }
  });
});

describe('scale is read, never assumed', () => {
  test('the unit declared above a table applies to it', () => {
    // "$ 6,255" is six thousand dollars or six billion depending on a header
    // line elsewhere on the page. This codebase has already shipped a
    // thousand-fold value error once.
    for (const fact of extractDisclosedHoldings(FIXTURE)) {
      assert.equal(fact.unit, 'millions', fact.issuer);
    }
  });

  test('a table with no declared unit returns figures as written', () => {
    // Null, not a guess. Nothing downstream may multiply these.
    const bare = 'Apple Inc. 1.6% $ 6,255 $ 61,962 $ 280';
    assert.equal(extractDisclosedHoldings(bare)[0].unit, null);
  });

  test('the nearest declaration above wins, not the first in the file', () => {
    const mixed = '(Dollars in thousands)\nA Corp 5.0% 1 2 3\n(Dollars in millions)\nB Corp 6.0% 4 5 6';
    const [a, b] = extractDisclosedHoldings(mixed);
    assert.equal(a.unit, 'thousands');
    assert.equal(b.unit, 'millions');
    assert.equal(unitBefore(mixed, mixed.length), 'millions');
    assert.equal(unitBefore(mixed, 0), null);
  });
});

describe('what the extractor refuses', () => {
  test('a line missing any figure is not half-read', () => {
    // A holding with an invented number is worse than a holding nobody
    // recorded.
    for (const line of [
      'Apple Inc. 1.6% $ 6,255 $ 61,962',
      'Apple Inc. $ 6,255 $ 61,962 $ 280',
      'Apple Inc. 1.6%',
      'we initiated a position in Apple during the quarter',
    ]) {
      assert.deepEqual(extractDisclosedHoldings(line), [], line);
    }
  });

  test('prose is not a table', () => {
    // The honest limit. This reads tables; a letter written in sentences
    // yields nothing and says nothing, rather than yielding something wrong.
    const prose = 'A large portion of our portfolio is concentrated in a small number of '
      + 'American companies such as Apple, American Express, Coca-Cola, and Moody\'s.';
    assert.deepEqual(extractDisclosedHoldings(prose), []);
  });

  test('an issuer of punctuation is a table artefact', () => {
    assert.deepEqual(extractDisclosedHoldings('— 1.6% 1 2 3'), []);
    assert.deepEqual(extractDisclosedHoldings('(1) 1.6% 1 2 3'), []);
  });

  test('nothing in is nothing out', () => {
    for (const empty of ['', null, undefined]) {
      assert.deepEqual(extractDisclosedHoldings(empty), []);
    }
  });
});

describe('recognising the same document twice', () => {
  test('re-pasting out of a PDF is the same document', () => {
    // Line wrapping differs between pastes and nothing else does.
    const sha = (value) => createHash('sha256').update(value).digest('hex');
    const rewrapped = FIXTURE.replace(/\n/g, '\n ').replace(/ {2,}/g, ' ');
    assert.equal(documentDigest(FIXTURE, sha), documentDigest(rewrapped, sha));
    assert.notEqual(documentDigest(FIXTURE, sha), documentDigest(`${FIXTURE}\nApple Inc. 9.9% 1 2 3`, sha));
  });
});
