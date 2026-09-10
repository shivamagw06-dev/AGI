import test from 'node:test';
import assert from 'node:assert/strict';
import { nameIndex, matchByName } from '../services/issuerNameMatch.js';

const directory = (...rows) => new Map(rows.map(([ticker, cik, title, kind = 'company']) => [ticker, { cik, title, kind }]));

test('the securities this exists for', () => {
  // Real CUSIPs, no ticker from any filer, and no other issue of the same
  // issuer to borrow a sector from.
  const index = nameIndex(directory(
    ['GTLS', '0000892553', 'Chart Industries, Inc.'],
    ['NUVL', '0001861560', 'Nuvalent, Inc.'],
    ['CPRX', '0001369568', 'Catalyst Pharmaceuticals, Inc.'],
    ['SEE', '0001012100', 'Sealed Air Corp'],
  ));
  assert.equal(matchByName('CHART INDS INC', index)?.ticker, 'GTLS');
  assert.equal(matchByName('NUVALENT INC', index)?.ticker, 'NUVL');
  assert.equal(matchByName('CATALYST PHARMACEUTICALS INC', index)?.ticker, 'CPRX');
  assert.equal(matchByName('SEALED AIR CORP NEW', index)?.ticker, 'SEE');
});

test('two companies matching is a refusal, not a choice', () => {
  // The failure this tier could produce if it were built to reach: a whole
  // position attributed to the wrong company, silently and plausibly.
  const index = nameIndex(directory(
    ['AAA', '0000000001', 'Acme Corp'],
    ['BBB', '0000000002', 'Acme Corporation'],
  ));
  assert.equal(matchByName('ACME', index), null);
});

test('one company reached twice is still one match', () => {
  // A company with two share classes appears under two tickers with the same
  // CIK. Counting that as ambiguity would refuse every dual-class issuer.
  const index = nameIndex(directory(
    ['GOOGL', '0001652044', 'Alphabet Inc.'],
    ['GOOG', '0001652044', 'Alphabet Inc.'],
  ));
  assert.equal(matchByName('ALPHABET INC', index)?.cik, '0001652044');
});

test('nothing matching is a refusal too', () => {
  const index = nameIndex(directory(['AAA', '1', 'Acme Corp']));
  assert.equal(matchByName('ZYMOGENETICS INC', index), null);
});

test('a different company with the same first word does not match', () => {
  // The bucket only narrows the search. sameCompany still has to agree, and
  // it compares words in order.
  const index = nameIndex(directory(['AAPL', '1', 'Apple Inc.'], ['APH', '2', 'Amphenol Corp']));
  assert.equal(matchByName('APPLE HOSPITALITY REIT INC', index), null);
});

test('a name that is only corporate noise matches nothing', () => {
  // "THE CORPORATION" tokenises to nothing, and an empty token list must not
  // match everything.
  const index = nameIndex(directory(['AAA', '1', 'Acme Corp']));
  for (const name of ['INC', 'THE CO', '', null, undefined, '   ', '...']) {
    assert.equal(matchByName(name, index), null, `${JSON.stringify(name)} must not match`);
  }
});

test('an entry with no title is not indexed', () => {
  // Fund entries carry no title. A blank one would bucket under nothing and
  // could never match, but storing it invites a later change to try.
  const index = nameIndex(new Map([['VOO', { cik: '1', title: null, kind: 'fund' }]]));
  assert.equal(index.size, 0);
});

test('the index is keyed on the first significant word, not the first word', () => {
  // "The Boeing Company" must be reachable from BOEING, since the words this
  // drops are exactly the ones filers vary.
  const index = nameIndex(directory(['BA', '1', 'The Boeing Company']));
  assert.equal(matchByName('BOEING CO', index)?.ticker, 'BA');
});

test('abbreviations agree in both directions', () => {
  // The filer writes one and the SEC writes the other, unpredictably.
  const index = nameIndex(directory(['JHG', '1', 'Janus Henderson Group plc'], ['X', '2', 'Intl Business Corp']));
  assert.equal(matchByName('JANUS HENDERSON GRP PLC', index)?.ticker, 'JHG');
  assert.equal(matchByName('INTERNATIONAL BUSINESS CORP', index)?.ticker, 'X');
});

test('nothing in yields nothing out, without throwing', () => {
  assert.equal(nameIndex().size, 0);
  assert.equal(nameIndex([]).size, 0);
  assert.equal(matchByName('ANYTHING', undefined), null);
  assert.equal(matchByName('ANYTHING', new Map()), null);
});

test('a longer holding name never matches a shorter SEC one', () => {
  // The bug this tier would otherwise have shipped. venueTicker's sameCompany
  // accepts the shorter name as a prefix of the longer, which is right when a
  // symbol has already narrowed the candidates and wrong against thirty-nine
  // thousand companies: "Apple Inc." is one token, so every company beginning
  // with Apple matches it.
  const index = nameIndex(directory(['AAPL', '1', 'Apple Inc.']));
  assert.equal(matchByName('APPLE HOSPITALITY REIT INC', index), null);
  assert.equal(matchByName('APPLE GREEN HOLDING INC', index), null);
  // And the same in the other direction.
  const enterprises = nameIndex(directory(['FERG', '2', 'Ferguson Enterprises Inc.']));
  assert.equal(matchByName('FERGUSON', enterprises), null);
});

test('the strictness is on words, not on spelling', () => {
  // Refusing a real match because the filer abbreviated would leave most of
  // the population unresolved for no gain in safety.
  const index = nameIndex(directory(['GTLS', '1', 'Chart Industries, Inc.']));
  for (const spelling of ['CHART INDS INC', 'Chart Industries Inc', 'CHART  INDUSTRIES,  INC.', 'chart inds']) {
    assert.equal(matchByName(spelling, index)?.ticker, 'GTLS', spelling);
  }
});
