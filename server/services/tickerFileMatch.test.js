import assert from 'node:assert/strict';
import test from 'node:test';
import { indexTickerFile, proposeFromTickerFile } from './tickerFileMatch.js';
import { normaliseIssuerName as normalise } from './thirteenFList.js';

const FILE = {
  0: { cik_str: 106040, ticker: 'WDC', title: 'WESTERN DIGITAL CORP' },
  1: { cik_str: 12927, ticker: 'BA', title: 'BOEING CO' },
  2: { cik_str: 72971, ticker: 'WFC', title: 'WELLS FARGO & COMPANY/MN' },
  3: { cik_str: 670703, ticker: 'NUVL', title: 'NUVALENT INC' },
  4: { cik_str: 1, ticker: 'GOOGL', title: 'Alphabet Inc.' },
  5: { cik_str: 2, ticker: 'GOOG', title: 'Alphabet Inc.' },
};

const securities = new Map([
  // The three that a 2019 name match got wrong. All are the issuer's debt or
  // preferred, all carry the issuer's name, none is common stock.
  ['958102AT2', { issuer_name: 'WESTERN DIGITAL CORP', security_class: 'debt' }],
  ['097023204', { issuer_name: 'BOEING CO', security_class: 'preferred' }],
  ['949746804', { issuer_name: 'WELLS FARGO & CO', security_class: 'preferred' }],
  // And the equity that should match.
  ['670703107', { issuer_name: 'NUVALENT INC', security_class: 'equity' }],
]);
const observedFrom = new Map([
  ['958102AT2', '2020-03-31'], ['097023204', '2020-03-31'],
  ['949746804', '2020-03-31'], ['670703107', '2021-12-31'],
]);

test('a name that maps to two tickers is dropped from the index', () => {
  // Alphabet is GOOGL and GOOG under one title. 1,032 names in the real file
  // do this. Letting the last one win assigns a class A ticker to class B.
  const { byName, ambiguous } = indexTickerFile(FILE, normalise);
  assert.equal(ambiguous.has(normalise('Alphabet Inc.')), true);
  assert.equal(byName.has(normalise('Alphabet Inc.')), false);
});

test('the bond, the preferred and the preferred are never asked about', () => {
  // This is the whole safety argument. A 2019 name match produced
  // WESTERN DIGITAL -> WDC, BOEING -> BA and WELLS FARGO -> WFC for a
  // convertible note and two preferreds. Restricting to equity removes the
  // failure by never asking, not by matching more carefully.
  const { byName, ambiguous } = indexTickerFile(FILE, normalise);
  const { proposals, skipped } = proposeFromTickerFile(
    ['958102AT2', '097023204', '949746804'],
    { securities, byName, ambiguousNames: ambiguous, observedFrom, takenTickers: new Map(), normalise },
  );
  assert.equal(proposals.length, 0);
  assert.equal(skipped.notEquity, 3);
});

test('an equity with an exact name match is proposed', () => {
  const { byName, ambiguous } = indexTickerFile(FILE, normalise);
  const { proposals } = proposeFromTickerFile(['670703107'],
    { securities, byName, ambiguousNames: ambiguous, observedFrom, takenTickers: new Map(), normalise });
  assert.equal(proposals.length, 1);
  assert.equal(proposals[0].ticker, 'NUVL');
  assert.equal(proposals[0].valid_from, '2021-12-31');
  assert.equal(proposals[0].source, 'sec_ticker_file');
});

test('a ticker another security already carries is not assigned twice', () => {
  // One ticker describes one security. Assigning it to a second merges two
  // companies' holdings under one symbol.
  const { byName, ambiguous } = indexTickerFile(FILE, normalise);
  const { proposals, skipped } = proposeFromTickerFile(['670703107'], {
    securities, byName, ambiguousNames: ambiguous, observedFrom,
    takenTickers: new Map([['NUVL', 'SOMEOTHER1']]), normalise,
  });
  assert.equal(proposals.length, 0);
  assert.equal(skipped.tickerTaken, 1);
});

test('an identifier never seen in a filing claims nothing', () => {
  const { byName, ambiguous } = indexTickerFile(FILE, normalise);
  const { proposals } = proposeFromTickerFile(['670703107'],
    { securities, byName, ambiguousNames: ambiguous, observedFrom: new Map(), takenTickers: new Map(), normalise });
  assert.equal(proposals.length, 0);
});

test('matching is exact after normalisation, never by similarity', () => {
  // The 13F list truncates at 28 characters and carries typos. A near-miss
  // resolved by edit distance is a guess, and a wrong guess puts one company's
  // holdings under another company's ticker.
  const { byName, ambiguous } = indexTickerFile(
    { 0: { ticker: 'TWO', title: 'Two Harbors Investment Corp' } }, normalise);
  const { proposals } = proposeFromTickerFile(['90187B804'], {
    securities: new Map([['90187B804', { issuer_name: 'TWO HARBORS INVENTMENT CORPO', security_class: 'equity' }]]),
    byName, ambiguousNames: ambiguous,
    observedFrom: new Map([['90187B804', '2019-03-31']]), takenTickers: new Map(), normalise,
  });
  assert.equal(proposals.length, 0);
});

test('an identifier the SEC list does not carry is not matched', () => {
  const { byName, ambiguous } = indexTickerFile(FILE, normalise);
  const { proposals } = proposeFromTickerFile(['ZZZZZZZZZ'],
    { securities, byName, ambiguousNames: ambiguous, observedFrom, takenTickers: new Map(), normalise });
  assert.equal(proposals.length, 0);
});

test('two identifiers cannot take one ticker unless a chain vouches for them', () => {
  // "A K A BRANDS HLDG CORP" is the issuer of both 00152K101 and 00152K200.
  // That shape is a reverse split, where the ticker legitimately survives an
  // identifier change, and it is also two share classes, where it does not. A
  // name cannot separate them. Three of the first fifteen proposals in the
  // real run had this shape.
  const file = { 0: { ticker: 'AKA', title: 'A.K.A. Brands Holding Corp' } };
  const { byName, ambiguous } = indexTickerFile(file, normalise);
  const args = {
    securities: new Map([
      ['00152K101', { issuer_name: 'A K A BRANDS HLDG CORP', security_class: 'equity' }],
      ['00152K200', { issuer_name: 'A K A BRANDS HLDG CORP', security_class: 'equity' }],
    ]),
    byName,
    ambiguousNames: ambiguous,
    observedFrom: new Map([['00152K101', '2023-09-30'], ['00152K200', '2023-12-31']]),
    takenTickers: new Map(),
    normalise,
  };

  // No chain link: neither is trusted, and the first is withdrawn too.
  const unvouched = proposeFromTickerFile(['00152K101', '00152K200'], { ...args, keyByCusip: new Map() });
  assert.equal(unvouched.proposals.length, 0);
  assert.equal(unvouched.collisions.length, 1);
  assert.deepEqual(unvouched.collisions[0].cusips, ['00152K101', '00152K200']);

  // Chain says one security: both may carry it, as a reverse split does.
  const vouched = proposeFromTickerFile(['00152K101', '00152K200'], {
    ...args,
    keyByCusip: new Map([['00152K101', '00152K101'], ['00152K200', '00152K101']]),
  });
  assert.equal(vouched.proposals.length, 2);
  assert.equal(vouched.collisions.length, 0);
});

test('an uncontested ticker is unaffected by a collision elsewhere', () => {
  const file = { 0: { ticker: 'AKA', title: 'A.K.A. Brands Holding Corp' },
                 1: { ticker: 'NUVL', title: 'NUVALENT INC' } };
  const { byName, ambiguous } = indexTickerFile(file, normalise);
  const { proposals } = proposeFromTickerFile(['00152K101', '00152K200', '670703107'], {
    securities: new Map([
      ['00152K101', { issuer_name: 'A K A BRANDS HLDG CORP', security_class: 'equity' }],
      ['00152K200', { issuer_name: 'A K A BRANDS HLDG CORP', security_class: 'equity' }],
      ['670703107', { issuer_name: 'NUVALENT INC', security_class: 'equity' }],
    ]),
    byName, ambiguousNames: ambiguous, takenTickers: new Map(), keyByCusip: new Map(), normalise,
    observedFrom: new Map([['00152K101', '2023-09-30'], ['00152K200', '2023-12-31'], ['670703107', '2021-12-31']]),
  });
  assert.deepEqual(proposals.map((p) => p.ticker), ['NUVL']);
});
