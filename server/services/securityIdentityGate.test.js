import assert from 'node:assert/strict';
import test from 'node:test';
import { partitionByClass, expandThroughChains, UNRESOLVABLE_CLASSES } from './securityIdentityGate.js';

const classes = new Map([
  ['958102AT2', 'debt'],       // Western Digital convertible note
  ['097023204', 'preferred'],  // Boeing depositary convertible preferred
  ['G0344N123', 'derivative'], // a SPAC unit
  ['037833900', 'option'],
  ['670703107', 'equity'],     // Nuvalent
  ['464287200', 'other'],      // iShares Core S&P 500
]);
const c = (cusip) => ({ cusip });

test('debt, preferred, options and derivatives are never asked about', () => {
  // 1,630 securities across 12,395 rows. Each consumed a vendor call on every
  // run and could never produce a ticker, because a convertible note has none.
  const { askable, excluded } = partitionByClass(
    ['958102AT2', '097023204', 'G0344N123', '037833900'].map(c), classes,
  );
  assert.equal(askable.length, 0);
  assert.equal(excluded.length, 4);
  assert.deepEqual(excluded.map((e) => e.security_class).sort(),
    ['debt', 'derivative', 'option', 'preferred']);
});

test('funds are asked about, because "other" is not a verdict', () => {
  // For funds the SEC description carries the fund's name, not a class code,
  // so a fifth of the list lands in "other" - 3,394 unmapped securities and
  // $101bn of holdings. Excluding them on a truncated string would repeat the
  // mistake that reported 147 blue chips as private placements.
  const { askable, excluded } = partitionByClass([c('464287200'), c('670703107')], classes);
  assert.equal(excluded.length, 0);
  assert.deepEqual(askable.map((a) => a.cusip), ['464287200', '670703107']);
});

test('an identifier the list has never seen is asked about, not discarded', () => {
  const { askable, excluded } = partitionByClass([c('ZZZZZZZZZ')], classes);
  assert.equal(excluded.length, 0);
  assert.equal(askable.length, 1);
});

test('"other" is deliberately not in the unresolvable set', () => {
  // Mutation guard: adding it here is a one-word change that silently drops
  // every fund.
  assert.equal(UNRESOLVABLE_CLASSES.has('other'), false);
  assert.equal(UNRESOLVABLE_CLASSES.has('unknown'), false);
});

test('a resolved ticker carries to the other identifiers of the same security', () => {
  // Aptiv's holdings sit under G6095L109 for seven years and G3265R107 since.
  // The vendor knows only the second. 1,872 unmapped identifiers have a
  // sibling that already carries a ticker.
  const extra = expandThroughChains(
    [{ cusip: 'G3265R107', ticker: 'APTV', valid_from: '2024-12-31', source: 'openfigi' }],
    {
      keyByCusip: new Map([['G3265R107', 'G6095L109']]),
      cusipsByKey: new Map([['G6095L109', ['G6095L109', 'G3265R107']]]),
      observedFrom: new Map([['G6095L109', '2019-03-31']]),
    },
  );
  assert.equal(extra.length, 1);
  assert.equal(extra[0].cusip, 'G6095L109');
  assert.equal(extra[0].ticker, 'APTV');
});

test('the sibling claims only the window its own evidence covers', () => {
  // Applying the resolved identifier's start date to the sibling would relabel
  // filings the mapping says nothing about - the error valid_from exists for.
  const extra = expandThroughChains(
    [{ cusip: 'G3265R107', ticker: 'APTV', valid_from: '2024-12-31' }],
    {
      keyByCusip: new Map([['G3265R107', 'G6095L109']]),
      cusipsByKey: new Map([['G6095L109', ['G6095L109']]]),
      observedFrom: new Map([['G6095L109', '2019-03-31']]),
    },
  );
  assert.equal(extra[0].valid_from, '2019-03-31');
  assert.notEqual(extra[0].valid_from, '2024-12-31');
});

test('a sibling with no observation of its own claims nothing', () => {
  const extra = expandThroughChains(
    [{ cusip: 'G3265R107', ticker: 'APTV', valid_from: '2024-12-31' }],
    {
      keyByCusip: new Map([['G3265R107', 'G6095L109']]),
      cusipsByKey: new Map([['G6095L109', ['UNSEEN123']]]),
      observedFrom: new Map(),
    },
  );
  assert.equal(extra.length, 0);
});

test('a chain-derived mapping records where it came from', () => {
  const [extra] = expandThroughChains(
    [{ cusip: 'G3265R107', ticker: 'APTV', valid_from: '2024-12-31', source: 'openfigi' }],
    {
      keyByCusip: new Map([['G3265R107', 'G6095L109']]),
      cusipsByKey: new Map([['G6095L109', ['G6095L109']]]),
      observedFrom: new Map([['G6095L109', '2019-03-31']]),
    },
  );
  // Told apart from a direct vendor answer, and traceable to the identifier it
  // was inferred from if it turns out to be wrong.
  assert.equal(extra.source, 'chain:G3265R107');
});

test('an identifier the vendor already answered is not overwritten by a sibling', () => {
  const extra = expandThroughChains(
    [{ cusip: 'A', ticker: 'AAA', valid_from: '2020-01-01' },
     { cusip: 'B', ticker: 'BBB', valid_from: '2021-01-01' }],
    {
      keyByCusip: new Map([['A', 'A'], ['B', 'A']]),
      cusipsByKey: new Map([['A', ['A', 'B']]]),
      observedFrom: new Map([['A', '2019-01-01'], ['B', '2019-01-01']]),
    },
  );
  assert.equal(extra.length, 0);
});
