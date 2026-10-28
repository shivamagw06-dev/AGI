import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveInstrument, resolveAll, normalizeName } from '../services/instrumentResolution.js';

const inst = (trading_symbol, name) => ({
  instrument_key: `NSE_EQ|${trading_symbol}`, trading_symbol, name,
});

/** A slice of the real NSE list, including the cases that caused trouble. */
const MASTER = [
  inst('MEESHO', 'MEESHO LIMITED'),
  inst('INFY', 'INFOSYS LIMITED'),
  inst('INFOMEDIA', 'INFOMEDIA PRESS LIMITED'),
  inst('INFOBEAN', 'INFOBEANS TECHNOLOGIES LTD'),
  inst('INDUSINDBK', 'INDUSIND BANK LIMITED'),
  inst('BHARTIARTL', 'BHARTI AIRTEL LIMITED'),
  inst('BHARTIHEXA', 'BHARTI HEXACOM LIMITED'),
  inst('ACMESOLAR', 'ACME SOLAR HOLDINGS LTD'),
  inst('STARHEALTH', 'STAR HEALTH & ALLIED INSU'),
  inst('BATAINDIA', 'BATA INDIA LIMITED'),
  inst('SKFINDUS', 'SKF IND (INDUSTRIAL) LTD'),
  // Share classes: both truncate to the same eight characters.
  inst('TATAMOTORS', 'TATA MOTORS LIMITED'),
  inst('TATAMOTORSDVR', 'TATA MOTORS LTD DVR'),
];

test('an exact symbol wins outright', () => {
  const result = resolveInstrument({ ticker: 'MEESHO', company: 'Meesho' }, MASTER);
  assert.equal(result.instrument_key, 'NSE_EQ|MEESHO');
  assert.equal(result.matched_by, 'symbol');
});

test('a legacy Bloomberg ticker resolves by company name', () => {
  // INFO is Infosys. Nothing about the string says so.
  const result = resolveInstrument({ ticker: 'INFO', company: 'Infosys' }, MASTER);
  assert.equal(result.instrument_key, 'NSE_EQ|INFY');
  assert.equal(result.matched_by, 'name');
});

test('name runs before prefix, so INFO never becomes INFOMEDIA', () => {
  // The failure this ordering prevents, and the reason it is not cosmetic:
  // a wrong instrument does not error. It returns perfectly good candles for
  // a different company and reports days-of-ADVT for a business nobody
  // flagged. INFO prefix-matches INFOMEDIA and INFOBEAN; neither is Infosys.
  const result = resolveInstrument({ ticker: 'INFO', company: 'Infosys' }, MASTER);
  assert.notEqual(result.instrument_key, 'NSE_EQ|INFOMEDIA');
  assert.equal(result.instrument_key, 'NSE_EQ|INFY');
});

test('an ambiguous prefix is refused, not resolved to the first row', () => {
  // Share classes are the real case: TATAMOTO truncates from both TATAMOTORS
  // and TATAMOTORSDVR, which are different securities at different prices.
  // Picking the first is a coin flip on which one the client reads about, and
  // it never errors - the wrong class returns perfectly good candles.
  const result = resolveInstrument({ ticker: 'TATAMOTO', company: null }, MASTER);
  assert.equal(result.instrument_key, null);
  assert.match(result.reason, /matches 2 instruments/);
});

test('an unmatchable prefix is refused too', () => {
  const result = resolveInstrument({ ticker: 'INFOBEANX', company: null }, MASTER);
  assert.equal(result.instrument_key, null);
});

test('a truncated eight-character ticker resolves by prefix', () => {
  // Bloomberg caps at eight, so ACMESOLA is ACMESOLAR with the tail cut off.
  const result = resolveInstrument({ ticker: 'ACMESOLA', company: 'ACME Solar' }, MASTER);
  assert.equal(result.instrument_key, 'NSE_EQ|ACMESOLAR');
});

test('prefix rescues a name that does not match the exchange spelling', () => {
  // STARHEAL: the exchange truncates its own name field to "STAR HEALTH &
  // ALLIED INSU", so the note's fuller name does not prefix-match it. The
  // eight-character ticker does.
  const result = resolveInstrument({ ticker: 'STARHEAL', company: 'Star Health & Allied Insurance' }, MASTER);
  assert.equal(result.instrument_key, 'NSE_EQ|STARHEALTH');
  assert.equal(result.matched_by, 'truncated symbol');
});

test('a short ticker does not prefix-match a longer symbol', () => {
  // BHARTI is six characters, so it was never truncated - and it prefixes two
  // different companies. Only the name may decide it.
  const result = resolveInstrument({ ticker: 'BHARTI', company: 'Bharti Airtel' }, MASTER);
  assert.equal(result.instrument_key, 'NSE_EQ|BHARTIARTL');
  assert.equal(result.matched_by, 'name');
});

test('a short ticker with no usable name is refused rather than prefixed', () => {
  const result = resolveInstrument({ ticker: 'BHARTI', company: null }, MASTER);
  assert.equal(result.instrument_key, null);
  assert.match(result.reason, /no NSE instrument matched/i);
});

test('a name matching several companies is refused and says how many', () => {
  const result = resolveInstrument({ ticker: 'ZZZZ', company: 'Bharti' }, MASTER);
  assert.equal(result.instrument_key, null);
  assert.match(result.reason, /matches 2 instruments/);
});

test('legal suffixes and punctuation do not decide a match', () => {
  assert.equal(normalizeName('Bata India'), normalizeName('BATA INDIA LIMITED'));
  assert.equal(normalizeName('Star Health & Allied'), 'STARHEALTHANDALLIED');
  const result = resolveInstrument({ ticker: 'ZZZZ', company: 'Bata India Ltd.' }, MASTER);
  assert.equal(result.instrument_key, 'NSE_EQ|BATAINDIA');
});

test('a two-letter company fragment is not allowed to match', () => {
  // 'ME' matches exactly one instrument - MEESHO - so ambiguity does not save
  // us here. Only the four-character floor does, and without it any stub in a
  // company_name column resolves to whichever name happens to start with it.
  const result = resolveInstrument({ ticker: 'ZZZZ', company: 'ME' }, MASTER);
  assert.equal(result.instrument_key, null);
});

test('a missing ticker is refused before anything else runs', () => {
  assert.equal(resolveInstrument({}, MASTER).instrument_key, null);
  assert.equal(resolveInstrument({ ticker: '  ' }, MASTER).reason, 'no ticker');
});

test('a batch reports which tier resolved each name', () => {
  // The tier counts are how a reviewer knows whether the mapping is solid or
  // leaning on guesses: all-symbol is clean, mostly-prefix deserves a look.
  const { resolved, unresolved, tiers } = resolveAll([
    { source_ticker: 'MEESHO', exchange_symbol: 'MEESHO', company_name: 'Meesho' },
    { source_ticker: 'INFO', exchange_symbol: 'INFO', company_name: 'Infosys' },
    // STARHEAL, not ACMESOLA: "ACME Solar" prefixes "ACME SOLAR HOLDINGS LTD"
    // so the name tier claims it first, which is the intended precedence.
    // STARHEAL has no name match because the exchange truncates its own name
    // field, so it is the case that actually exercises the prefix tier.
    { source_ticker: 'STARHEAL', exchange_symbol: 'STARHEAL', company_name: 'Star Health & Allied Insurance' },
    { source_ticker: 'RJEX', exchange_symbol: 'RJEX', company_name: 'Rajesh Exports' },
  ], MASTER);

  assert.equal(resolved.length, 3);
  assert.equal(unresolved.length, 1);
  assert.equal(unresolved[0].source_ticker, 'RJEX');
  assert.deepEqual(tiers, { symbol: 1, name: 1, 'truncated symbol': 1 });
});
