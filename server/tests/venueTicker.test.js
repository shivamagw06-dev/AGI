import test from 'node:test';
import assert from 'node:assert/strict';
import { candidateBases, recoverTicker, sameCompany } from '../services/venueTicker.js';

const sec = new Map([
  ['HON', 'Honeywell International Inc'],
  ['LRCX', 'Lam Research Corp'],
  ['CCL', 'Carnival Corp'],
  ['BLK', 'BlackRock Inc'],
  ['ANET', 'Arista Networks Inc'],
  ['TRI', 'Thomson Reuters Corp'],
  ['CAT', 'Caterpillar Inc'],
  ['BRK-B', 'Berkshire Hathaway Inc'],
  ['BRK-A', 'Berkshire Hathaway Inc'],
  ['EA', 'Electronic Arts Inc'],
  ['HEI-A', 'Heico Corp'],
  ['RNA', 'Atrium Therapeutics Inc'],
  ['FERG', 'Ferguson Enterprises Inc'],
]);
const recover = (sym, issuer) => recoverTicker(sym, issuer, sec);

test('a currency suffix is stripped from the observed venue symbols', () => {
  assert.deepEqual(candidateBases('HONGBP'), ['HON']);
  assert.deepEqual(candidateBases('LRCXEUR'), ['LRCX']);
  assert.deepEqual(candidateBases('BLKCHF'), ['BLK']);
});

test('a venue line number is not part of the ticker', () => {
  // Carnival is CCL1EUR on Xetra and CCL in New York.
  assert.ok(candidateBases('CCL1EUR').includes('CCL'));
  assert.ok(candidateBases('TRI4EUR').includes('TRI'));
});

test('the real symbols from the holdings recover to their US tickers', () => {
  assert.equal(recover('HONGBP', 'HONEYWELL INTERNATIONAL INC').ticker, 'HON');
  assert.equal(recover('LRCXEUR', 'LAM RESEARCH CORP').ticker, 'LRCX');
  assert.equal(recover('CCL1EUR', 'CARNIVAL CORP').ticker, 'CCL');
  assert.equal(recover('BLKCHF', 'BLACKROCK INC').ticker, 'BLK');
  assert.equal(recover('ANETEUR', 'ARISTA NETWORKS INC').ticker, 'ANET');
});

test('a trimmed string that spells a real ticker is not enough on its own', () => {
  // This is the whole safety of the method. CATEUR trims to CAT, which is a
  // real and heavily held ticker - but if the position is not Caterpillar,
  // accepting it hands that holding to an unrelated company.
  const wrong = recover('CATEUR', 'SOME OTHER HOLDINGS PLC');
  assert.equal(wrong.ticker, null);
  assert.match(wrong.reason, /not/);
  assert.equal(recover('CATEUR', 'CATERPILLAR INC').ticker, 'CAT');
});

test('a symbol with no currency suffix is left alone', () => {
  // HO1, AM6, 8QR and 0VVB are pure venue codes carrying no US ticker to
  // recover. They stay unresolved rather than being guessed at.
  for (const s of ['HO1', 'AM6', '8QR', '0VVB', '07WA', '8L8C']) {
    assert.equal(recover(s, 'ANYTHING').ticker, null, s);
  }
});

test('a base the SEC does not list is refused', () => {
  // DWDPEUR trims to DWDP - DowDuPont, which stopped trading in 2019. There
  // is no US listing to recover it to and no prices to be had either.
  const r = recover('DWDPEUR', 'DOWDUPONT INC');
  assert.equal(r.ticker, null);
  assert.match(r.reason, /none of which the SEC lists/);
});

test('a holding with no issuer name cannot be checked, so it is not recovered', () => {
  const r = recover('HONGBP', '');
  assert.equal(r.ticker, null);
  assert.match(r.reason, /no issuer name/);
});

test('the reason says what was tried, so a rejection can be reviewed', () => {
  assert.match(recover('HONGBP', 'WRONG CO').reason, /HON/);
});

test('a stem that is not ticker-shaped is not treated as one', () => {
  // 22941EUR appears in the holdings. Trimming leaves "22941", which is a
  // line number, not a ticker. Without the shape check it would be carried
  // forward as a candidate and looked up as though it could be a company.
  assert.deepEqual(candidateBases('22941EUR'), []);
  assert.equal(recover('22941EUR', 'ANYTHING').ticker, null);
  assert.match(recover('22941EUR', 'ANYTHING').reason, /no recoverable ticker/);
});

test('a currency code alone does not trim to nothing', () => {
  assert.deepEqual(candidateBases('EUR'), []);
  assert.deepEqual(candidateBases('USD'), []);
});

test('a slash is a share class, and it is the largest block in the book', () => {
  // BRK/B and BRK/A are $725bn between them - the biggest single group of
  // unpriceable holdings. They were refused for having no currency suffix,
  // which was true and beside the point. Yahoo and the SEC both write BRK-B.
  assert.deepEqual(candidateBases('BRK/B'), ['BRK-B']);
  assert.equal(recover('BRK/B', 'BERKSHIRE HATHAWAY INC DEL').ticker, 'BRK-B');
  assert.equal(recover('BRK/A', 'BERKSHIRE HATHAWAY INC DEL').ticker, 'BRK-A');
  assert.equal(recover('HEI/A', 'HEICO CORP NEW').ticker, 'HEI-A');
});

test('a trailing asterisk marks the line, not the security', () => {
  assert.deepEqual(candidateBases('EA*'), ['EA']);
  assert.equal(recover('EA*', 'ELECTRONIC ARTS INC').ticker, 'EA');
});

test("a filer's abbreviation is the same company", () => {
  // The 13F says HONEYWELL INTL; the SEC registers HONEYWELL INTERNATIONAL.
  // Requiring the strings to match refused $74bn on a spelling difference.
  assert.ok(sameCompany('HONEYWELL INTL INC', 'Honeywell International Inc'));
  assert.equal(recover('HONGBP', 'HONEYWELL INTL INC').ticker, 'HON');
});

test('a name that says less is still the same company', () => {
  assert.ok(sameCompany('FERGUSON PLC NEW', 'Ferguson Enterprises Inc'));
  assert.ok(sameCompany('THOMSON REUTERS CORP', 'Thomson Reuters Corp Can'));
});

test('a different company is still refused, however similar the shape', () => {
  // RNA reads as AVIDITY BIOSCIENCES on the holding and ATRIUM THERAPEUTICS
  // at the SEC. That is a real reassignment and the whole point of the check.
  assert.equal(sameCompany('AVIDITY BIOSCIENCES INC', 'Atrium Therapeutics Inc'), false);
  const r = recover('RNAGBP', 'AVIDITY BIOSCIENCES INC');
  assert.equal(r.ticker, null);
  assert.match(r.reason, /not/);
});

test('a shared first word is not enough on its own', () => {
  // Loosening to a prefix match must not let one Liberty entity answer for
  // another; every word of the shorter name has to line up in order.
  assert.equal(sameCompany('LIBERTY MEDIA CORP', 'Liberty Broadband Corp'), false);
  assert.ok(sameCompany('LIBERTY MEDIA CORP DEL', 'Liberty Media Corp'));
});
