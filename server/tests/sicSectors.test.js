import test from 'node:test';
import assert from 'node:assert/strict';
import { classifySic, noOverlappingPeers, SECTOR_RANGES } from '../services/sicSectors.js';

const sectorOf = (code) => classifySic(code).sector;

test('the table cannot be ambiguous', () => {
  // Narrowest-match resolves an overlap only when one range is strictly
  // narrower. A partial overlap or two equal-width ranges covering the same
  // code would make the answer depend on the order they were written in, and
  // this scheme's whole claim is that it does not.
  assert.deepEqual(noOverlappingPeers(), []);
});

test('the companies the old map got wrong', () => {
  // Every one of these was Industrials or Consumer Discretionary before, and
  // between them they are most of the value in a large-cap 13F book.
  assert.equal(sectorOf(3571), 'Information Technology'); // Apple, electronic computers
  assert.equal(sectorOf(3674), 'Information Technology'); // Nvidia, semiconductors
  assert.equal(sectorOf(7372), 'Information Technology'); // Microsoft, prepackaged software
  assert.equal(sectorOf(7370), 'Information Technology'); // Alphabet, computer services
  assert.equal(sectorOf(2834), 'Health Care');            // Eli Lilly, pharmaceutical preparations
  assert.equal(sectorOf(3841), 'Health Care');            // Abbott, surgical & medical instruments
  assert.equal(sectorOf(4813), 'Communication Services'); // AT&T, telephone communications
  assert.equal(sectorOf(4841), 'Communication Services'); // Comcast, cable
});

test('a narrower range beats the division it sits inside', () => {
  // 3600-3699 is electrical equipment; 3670-3679 within it is semiconductors.
  assert.equal(sectorOf(3690), 'Industrials');
  assert.equal(sectorOf(3674), 'Information Technology');
  // 3500-3599 is industrial machinery; 3570-3579 is computers.
  assert.equal(sectorOf(3550), 'Industrials');
  assert.equal(sectorOf(3571), 'Information Technology');
  // 6700-6799 is holding and investment offices; 6798 alone is the REIT code.
  assert.equal(sectorOf(6770), 'Financials');
  assert.equal(sectorOf(6798), 'Real Estate');
});

test('the answer does not depend on the order of the table', () => {
  // The property the narrowest-match rule exists to provide. Reversed, every
  // code must still classify identically.
  const reversed = [...SECTOR_RANGES].reverse();
  const pick = (code, ranges) => {
    let best = null;
    for (const range of ranges) {
      const [from, to] = range;
      if (code < from || code > to) continue;
      if (!best || (to - from) < (best[1] - best[0])) best = range;
    }
    return best?.[2] || 'Unclassified';
  };
  for (let code = 100; code <= 9999; code += 1) {
    assert.equal(pick(code, reversed), pick(code, SECTOR_RANGES), `code ${code} depends on order`);
  }
});

test('chemicals and drugs are not the same sector', () => {
  // The old map put 2800-2899 entirely in Health Care, so Dow and Sherwin
  // Williams were health care companies.
  assert.equal(sectorOf(2821), 'Materials');      // plastics materials
  assert.equal(sectorOf(2834), 'Health Care');    // pharmaceutical preparations
  assert.equal(sectorOf(2836), 'Health Care');    // biological products
  assert.equal(sectorOf(2840), 'Consumer Staples'); // soap & detergents
  assert.equal(sectorOf(2851), 'Materials');      // paints
});

test('fuels are energy and other mining is materials', () => {
  assert.equal(sectorOf(1311), 'Energy');    // crude petroleum & natural gas
  assert.equal(sectorOf(1221), 'Energy');    // bituminous coal
  assert.equal(sectorOf(1040), 'Materials'); // gold mining
  assert.equal(sectorOf(2911), 'Energy');    // petroleum refining
  assert.equal(sectorOf(4610), 'Energy');    // pipelines
});

test('food and drug retail are staples, everything else discretionary', () => {
  assert.equal(sectorOf(5411), 'Consumer Staples');        // grocery stores
  assert.equal(sectorOf(5912), 'Consumer Staples');        // drug stores
  assert.equal(sectorOf(5651), 'Consumer Discretionary');  // family clothing
  assert.equal(sectorOf(5961), 'Consumer Discretionary');  // catalog & mail-order
});

test('an unknown code is Unclassified, never the nearest guess', () => {
  // A wrong sector is worse than a missing one: this feeds an aggregate that
  // reports weights, and a misfiled position moves two sectors at once.
  assert.equal(sectorOf(0), 'Unclassified');
  assert.equal(sectorOf(null), 'Unclassified');
  assert.equal(sectorOf(undefined), 'Unclassified');
  assert.equal(sectorOf(''), 'Unclassified');
  assert.equal(sectorOf('not a number'), 'Unclassified');
  assert.equal(sectorOf(1150), 'Unclassified'); // between metal mining and coal
  assert.equal(sectorOf(9050), 'Unclassified'); // between services and public administration
});

test('a code arrives from EDGAR as a string', () => {
  // sec.sic comes off the submissions JSON, and it is not consistently typed.
  assert.equal(sectorOf('3674'), 'Information Technology');
  assert.equal(sectorOf(' 3674 '), 'Information Technology');
  assert.equal(classifySic('3674').industry, 'Semiconductors & Components');
});

test("the registrant's own description wins over our label", () => {
  // It is more specific than anything a range can carry, and it comes from
  // the filer rather than from us.
  assert.equal(classifySic(3674, 'Semiconductors & Related Devices').industry, 'Semiconductors & Related Devices');
  assert.equal(classifySic(3674).industry, 'Semiconductors & Components');
  // Including when the code itself is unusable - the description is still the
  // best thing available, and the sector still refuses to guess.
  assert.deepEqual(classifySic(0, 'Blank Checks'), { sector: 'Unclassified', industry: 'Blank Checks' });
});

test('every range is well formed', () => {
  for (const [from, to, sector, industry] of SECTOR_RANGES) {
    assert.ok(Number.isInteger(from) && Number.isInteger(to), `${from}-${to} is not integral`);
    assert.ok(from <= to, `${from}-${to} is inverted`);
    assert.ok(sector && industry, `${from}-${to} is missing a label`);
    assert.notEqual(sector, 'Unclassified', `${from}-${to} classifies to Unclassified`);
  }
});
