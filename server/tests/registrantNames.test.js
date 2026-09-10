import test from 'node:test';
import assert from 'node:assert/strict';
import { canonicalName, parseRegistrant, resolveRegistrants } from '../services/registrantNames.js';

// CIKs are ten digits in cik-lookup-data.txt, and parseRegistrant requires
// that shape. Padded here so the fixtures match the file rather than a
// convenient shorthand - the first version of these tests did not, and three
// of them failed against correct code.
const line = (name, cik) => `${name}:${String(cik).padStart(10, '0')}:`;

test('the fund trusts this exists for', () => {
  // The tail after every other tier: no ticker, because the trust issues
  // dozens of ETFs and the trust is the issuer.
  const lines = [
    line('TIDAL TRUST II', '0001924868'),
    line('TIDAL TRUST IV', '0001964764'),
    line('DIREXION SHARES ETF TRUST', '0001424958'),
    line('FIRST TRUST EXCHANGE-TRADED FUND VI', '0001552740'),
    line('NORTHERN LIGHTS FUND TRUST IV', '0001668374'),
    line('PROSHARES TRUST II', '0001415311'),
  ];
  const out = resolveRegistrants(
    ['TIDAL TRUST II', 'TIDAL TR IV', 'DIREXION SHARES ETF TRUST', 'FIRST TR EXCHNG TRADED FD VI', 'NORTHERN LTS FD TR IV', 'PROSHARES TR II'],
    lines,
  );
  assert.equal(out.get('TIDAL TRUST II').cik, '0001924868');
  assert.equal(out.get('TIDAL TR IV').cik, '0001964764');
  assert.equal(out.get('FIRST TR EXCHNG TRADED FD VI').cik, '0001552740');
  assert.equal(out.get('NORTHERN LTS FD TR IV').cik, '0001668374');
  assert.equal(out.get('PROSHARES TR II').cik, '0001415311');
});

test('TRUST and FUND are identity here, not filler', () => {
  // The measured failure that made this a separate tokeniser. venueTicker
  // drops both as noise, which collapsed forty Tidal registrants into one
  // ambiguous match and resolved none of them.
  assert.equal(canonicalName('TIDAL TRUST II'), 'TIDAL TRUST II');
  assert.equal(canonicalName('TIDAL TR IV'), 'TIDAL TRUST IV');
  assert.notEqual(canonicalName('TIDAL TRUST II'), canonicalName('TIDAL TRUST III'));
});

test('a roman numeral distinguishes two registrants', () => {
  // Trust II and Trust III file separately and hold different funds.
  const lines = [line('PROSHARES TRUST', '1'), line('PROSHARES TRUST II', '2')];
  const out = resolveRegistrants(['PROSHARES TR', 'PROSHARES TR II'], lines);
  assert.equal(out.get('PROSHARES TR').cik, '0000000001');
  assert.equal(out.get('PROSHARES TR II').cik, '0000000002');
});

test("filer abbreviations reach the SEC's spelling", () => {
  assert.equal(canonicalName('CHART INDS INC'), canonicalName('CHART INDUSTRIES INC'));
  assert.equal(canonicalName('WEBSTER FINL CORP'), canonicalName('WEBSTER FINANCIAL CORP'));
  assert.equal(canonicalName('GATES INDL CORP PLC'), canonicalName('GATES INDUSTRIAL CORP PLC'));
  assert.equal(canonicalName('SELECT MED HLDGS CORP'), canonicalName('SELECT MEDICAL HOLDINGS CORP'));
  assert.equal(canonicalName('SSGA ACTIVE TR'), canonicalName('SSGA ACTIVE TRUST'));
});

test('corporate form is dropped, so INC and CORP never decide a match', () => {
  assert.equal(canonicalName('AIR LEASE CORP'), 'AIR LEASE');
  assert.equal(canonicalName('The Boeing Company'), 'BOEING');
  assert.equal(canonicalName('STELLAR BANCORP. INC.'), 'STELLAR BANCORP');
});

test('two registrants matching is a refusal, not a choice', () => {
  // The failure this tier could produce: a whole position attributed to the
  // wrong company, silently and plausibly.
  const lines = [line('ACME HOLDINGS', '1'), line('ACME HLDGS', '2')];
  assert.equal(resolveRegistrants(['ACME HOLDINGS'], lines).size, 0);
});

test('one registrant listed twice under one CIK is still one match', () => {
  // A company respelled over time keeps its CIK. Counting that as ambiguity
  // would refuse every registrant that ever changed its punctuation.
  const lines = [line('CATALYST PHARMACEUTICALS INC', '1'), line('CATALYST PHARMACEUTICALS, INC.', '1')];
  assert.equal(resolveRegistrants(['CATALYST PHARMACEUTICALS INC'], lines).get('CATALYST PHARMACEUTICALS INC').cik, '0000000001');
});

test('a name that is only corporate form matches nothing', () => {
  // It normalises to nothing, and a blank key must not match every other
  // blank key.
  for (const name of ['INC', 'THE CO', 'LTD', '', null, undefined, '   ', '...']) {
    assert.equal(canonicalName(name), '', `${JSON.stringify(name)} should normalise to nothing`);
  }
  assert.equal(resolveRegistrants(['INC'], [line('INC', '1')]).size, 0);
});

test('a longer holding name does not match a shorter registrant', () => {
  // Equality, not prefix. Measured: allowing a truncated holding name to
  // match a longer registrant resolved four more and made eleven ambiguous
  // that had been exact, because a name cut at twenty-eight characters is a
  // prefix of many registrants at once.
  const lines = [line('APPLE INC', '1'), line('APPLE HOSPITALITY REIT, INC.', '2')];
  const out = resolveRegistrants(['APPLE HOSPITALITY REIT INC'], lines);
  assert.equal(out.get('APPLE HOSPITALITY REIT INC').cik, '0000000002', 'the REIT, not Apple');
  assert.equal(resolveRegistrants(['FERGUSON'], [line('FERGUSON ENTERPRISES INC', '3')]).size, 0);
});

test('the CIK is read from the end, because a name can contain a colon', () => {
  assert.deepEqual(parseRegistrant('ACME: THE COMPANY:0000000123:'), { name: 'ACME: THE COMPANY', cik: '0000000123' });
  assert.deepEqual(parseRegistrant('PLAIN NAME:0000000456:'), { name: 'PLAIN NAME', cik: '0000000456' });
});

test('a malformed line contributes nothing rather than throwing', () => {
  // Forty megabytes of it arrive over the network; the shape is not
  // guaranteed and one bad line must not end the run.
  for (const bad of ['', '   ', ':0001003197:', 'NO CIK HERE', 'NAME:12:', 'NAME:notdigits:', null, undefined]) {
    assert.equal(parseRegistrant(bad), null, JSON.stringify(bad));
  }
});

test('nothing in yields nothing out, without throwing', () => {
  assert.equal(resolveRegistrants().size, 0);
  assert.equal(resolveRegistrants([], []).size, 0);
  assert.equal(resolveRegistrants(['ACME'], []).size, 0);
  assert.equal(resolveRegistrants([], [line('ACME', '1')]).size, 0);
});
