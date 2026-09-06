/**
 * Ranking for the security search.
 *
 * The box used to demand a ticker and navigate to whatever was typed, so APPLE
 * opened a page for a security called APPLE. These tests cover the ordering a
 * person expects when they type a name instead.
 *
 *   node --test server/services/institutionalSecuritySearch.test.js
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { rank, normalise } from './institutionalSecuritySearch.js';

const entry = (issuer_name, ticker, owners, cusip = null) => ({
  issuer_name, ticker, owners, cusip,
  haystack: normalise(`${issuer_name || ''} ${ticker || ''}`),
});

const INDEX = [
  entry('APPLE INC', 'AAPL', 31, '037833100'),
  entry('APPLIED MATERIALS INC', 'AMAT', 9),
  entry('APPLOVIN CORP', 'APP', 6),
  entry('ALPHABET INC', 'GOOG', 25, '02079K107'),
  entry('ALPHABET INC', 'GOOGL', 29, '02079K305'),
  entry('TAIWAN SEMICONDUCTOR MANUFAC', 'TSM', 27),
  entry('AMAZON COM INC', 'AMZN', 29),
  entry('MOET HENNESSY LOUIS VUITTON', 'LVMUY', 2),
];

test('typing a company name finds it', () => {
  // The whole point: nobody outside a desk types AAPL.
  const [first] = rank(INDEX, 'apple');
  assert.equal(first.issuer_name, 'APPLE INC');
  assert.equal(first.ticker, 'AAPL');
  assert.equal(first.key, 'AAPL', 'the page should open the readable ticker, not the CUSIP');
});

test('an exact ticker beats a name that merely starts the same way', () => {
  // Someone typing APP means AppLovin's ticker, not Apple or Applied Materials.
  const [first] = rank(INDEX, 'APP');
  assert.equal(first.ticker, 'APP');
});

test('a name prefix ranks above a mere substring', () => {
  const names = rank(INDEX, 'appl').map((r) => r.issuer_name);
  assert.equal(names[0], 'APPLE INC');
  assert.ok(names.indexOf('APPLIED MATERIALS INC') < names.indexOf('APPLOVIN CORP')
    || !names.includes('APPLOVIN CORP'));
});

test('breadth of ownership breaks ties between share classes', () => {
  // Two Alphabet lines with identical names. GOOG is listed FIRST in the
  // fixture on purpose: a stable sort would leave it there, so only a real
  // tie-break on ownership can lift GOOGL above it. With them the other way
  // round this test passed even when the tie-break was deleted.
  const alphabet = rank(INDEX, 'alphabet');
  assert.equal(alphabet[0].ticker, 'GOOGL');
  assert.equal(alphabet[1].ticker, 'GOOG');
});

test('a partial company name finds the full one', () => {
  const [first] = rank(INDEX, 'taiwan semi');
  assert.equal(first.ticker, 'TSM');
});

test('accents and punctuation do not have to be typed', () => {
  assert.equal(normalise('Moët Hennessy'), 'MOET HENNESSY');
  const [first] = rank(INDEX, 'moet');
  assert.equal(first.ticker, 'LVMUY');
});

test('one character returns nothing rather than the whole book', () => {
  assert.deepEqual(rank(INDEX, 'a'), []);
  assert.deepEqual(rank(INDEX, ''), []);
});

test('a term matching nothing returns nothing', () => {
  assert.deepEqual(rank(INDEX, 'zzzzz'), []);
});

test('the limit is honoured', () => {
  assert.equal(rank(INDEX, 'inc', 2).length, 2);
});

// ---------------------------------------------------------------------------
// The reason the index is cached
// ---------------------------------------------------------------------------

test('the index is built once and cached, not queried per keystroke', () => {
  // A substring match over issuer names cannot use an index. Running it on
  // every keypress against 72,401 holdings rows is precisely the full scan the
  // admin guards exist to prevent - and this route is public.
  const src = readFileSync(new URL('./institutionalSecuritySearch.js', import.meta.url), 'utf8');
  assert.match(src, /CACHE_TTL_MS/, 'the index must be cached');
  assert.match(src, /building/, 'concurrent builds must share one in-flight promise');
  assert.match(src, /MAX_ROWS/, 'the build must be bounded so a large table cannot exhaust memory');
  assert.match(src, /is_active/, 'superseded filings would put withdrawn positions in the results');
});

test('the route refuses a one-character query before touching the index', () => {
  const routes = readFileSync(new URL('../routes/institutionalHoldings.js', import.meta.url), 'utf8');
  const handler = /router\.get\('\/securities\/search'[\s\S]*?\n  \}\);/.exec(routes)?.[0];
  assert.ok(handler, 'the search route is gone');
  assert.match(handler, /length < 2/, 'a single character must not trigger a search');
  assert.match(handler, /slice\(0, 64\)/, 'the term must be bounded');
  assert.match(handler, /Math\.min\(Math\.max\(Number\(req\.query\.limit\)/, 'the limit must be clamped');
});
