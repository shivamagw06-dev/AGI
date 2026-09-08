import test from 'node:test';
import assert from 'node:assert/strict';
import { parsePaste, parseNumber, exchangeSymbol, mapHeader } from '../services/rebalancePaste.js';

test('parentheses are an outflow, not a magnitude', () => {
  // Every one of these tables marks a sell with parentheses. Reading "(22)" as
  // 22 turns Swiggy's outflow into an inflow and ranks it at the top of the
  // buy list - a wrong sign is worse than a missing number.
  assert.equal(parseNumber('(22)'), -22);
  assert.equal(parseNumber('(13.4)'), -13.4);
  assert.equal(parseNumber('88'), 88);
});

test('an absent value is null, never zero', () => {
  // Zero means "no expected flow", which is a real and actionable statement.
  // A failed parse must not be able to say it.
  for (const blank of ['', '-', '–', 'n/a', 'NA', 'nm', '   ']) {
    assert.equal(parseNumber(blank), null, `${JSON.stringify(blank)} should be null`);
  }
  assert.equal(parseNumber('88'), 88);
});

test('unparseable text is null rather than a coerced number', () => {
  // Number('') is 0 and Number(null) is 0. Anything that reaches the field
  // must go through a check that rejects rather than coerces.
  assert.equal(parseNumber('tbd'), null);
  assert.equal(parseNumber('~90'), null);
  assert.equal(parseNumber(null), null);
  assert.equal(parseNumber(undefined), null);
});

test('thousands separators and currency marks survive', () => {
  assert.equal(parseNumber('121,645'), 121645);
  assert.equal(parseNumber('$1,569'), 1569);
  assert.equal(parseNumber('(1,234.5)'), -1234.5);
});

test('the country code comes off the Bloomberg ticker', () => {
  assert.equal(exchangeSymbol('MEESHO IS'), 'MEESHO');
  assert.equal(exchangeSymbol('TVSHLTD IS'), 'TVSHLTD');
  assert.equal(exchangeSymbol('INFO IS'), 'INFO');
  assert.equal(exchangeSymbol(''), null);
});

test('a ticker with no country code is left alone', () => {
  // Stripping a trailing word unconditionally would corrupt any symbol that
  // legitimately ends in one.
  assert.equal(exchangeSymbol('RELIANCE'), 'RELIANCE');
});

test('headers are matched by text, and an unmatched one does not shift the rest', () => {
  // The failure this prevents: dropping the unrecognised column and shifting
  // everything after it one place left, so sector lands in change_type and
  // every row is quietly wrong rather than visibly missing.
  const header = mapHeader(['Ticker', 'Company Name', 'Wingdings', 'Sector', 'Type of Change']);
  assert.equal(header.mapping[0], 'source_ticker');
  assert.equal(header.mapping[2], null);
  assert.equal(header.mapping[3], 'sector');
  assert.equal(header.mapping[4], 'change_type');
  assert.deepEqual(header.unmatched, ['Wingdings']);
});

test('a paste missing a required column is refused with the reason', () => {
  const result = parsePaste('Company Name\tSector\nMeesho\tConsumer');
  assert.deepEqual(result.rows, []);
  assert.ok(result.missing.includes('source_ticker'));
  assert.ok(result.missing.includes('change_type'));
});

test('a tab-separated paste parses into rows', () => {
  const pasted = [
    'Ticker\tCompany Name\tSector\tPotential Net Passive Flows (US$mn)\tType of Change',
    'MEESHO IS\tMeesho\tConsumer Retail & Services\t88\tHigher Adj Shr.',
    'SWIGGY IS\tSwiggy\tConsumer Retail & Services\t(22)\tLower Adj Shr.',
  ].join('\n');

  const { rows, rejected } = parsePaste(pasted);
  assert.equal(rejected.length, 0);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].source_ticker, 'MEESHO IS');
  assert.equal(rows[0].exchange_symbol, 'MEESHO');
  assert.equal(rows[0].net_passive_flow_usd_mn, 88);
  assert.equal(rows[1].net_passive_flow_usd_mn, -22, 'the outflow must stay negative');
});

test('a space-aligned paste from a PDF parses too', () => {
  const pasted = [
    'Ticker      Company Name   Sector      Potential Net Passive Flows   Type of Change',
    'MEESHO IS   Meesho         Consumer    88                            Higher Adj Shr.',
  ].join('\n');
  const { rows } = parsePaste(pasted);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].net_passive_flow_usd_mn, 88);
});

test('section headings are rejected with a reason rather than dropped', () => {
  // These tables carry banner rows - "Stocks with potential passive inflows
  // within India post FTSE Global Index Series rebalancing". They are not
  // rows. Discarding them silently is how a parser loses eight real names and
  // still looks like it worked.
  const pasted = [
    'Ticker\tCompany Name\tPotential Net Passive Flows\tType of Change',
    'Stocks with potential passive inflows within India\t\t\t',
    'MEESHO IS\tMeesho\t88\tHigher Adj Shr.',
  ].join('\n');

  const { rows, rejected } = parsePaste(pasted);
  assert.equal(rows.length, 1);
  assert.equal(rejected.length, 1);
  assert.match(rejected[0].reason, /change_type/);
});

test('an empty paste returns nothing and says what it needed', () => {
  const result = parsePaste('');
  assert.deepEqual(result.rows, []);
  assert.deepEqual(result.missing, ['source_ticker', 'change_type']);
});

test('only plain decimals are accepted, not every notation Number() takes', () => {
  // Number('1e5') is 100000 and Number('0x10') is 16. Neither belongs in a
  // rebalance table, and both would arrive as a confident, wrong figure.
  // Number.isFinite alone does not catch them - it is happy with both - so the
  // format check is what makes these null and therefore reported.
  assert.equal(parseNumber('1e5'), null);
  assert.equal(parseNumber('0x10'), null);
  assert.equal(parseNumber('1E+05'), null);
  // And it must not start rejecting the shapes that do appear.
  assert.equal(parseNumber('.5'), 0.5);
  assert.equal(parseNumber('1234.56'), 1234.56);
});
