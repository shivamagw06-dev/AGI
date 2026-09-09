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

test('a base neither register knows is refused', () => {
  // DWDPEUR trims to DWDP - DowDuPont, which stopped trading in 2019. There
  // is no US listing to recover it to and no prices to be had either.
  const r = recover('DWDPEUR', 'DOWDUPONT INC');
  assert.equal(r.ticker, null);
  assert.match(r.reason, /neither the SEC register nor past filings know/);
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

test('a share-class word does not make it a different company', () => {
  // The holding reads "Petrobras Pref ADR"; the SEC registers "PETROBRAS -
  // PETROLEO BRASILEIRO SA". PREF describes the line, not the issuer, and
  // the class is already carried by the ticker: PBR/A resolves to PBR-A.
  const secList = new Map([['PBR-A', 'PETROBRAS - PETROLEO BRASILEIRO SA']]);
  assert.equal(recoverTicker('PBR/A', 'Petrobras Pref ADR', secList).ticker, 'PBR-A');
});

test('dropping the class word does not merge two different companies', () => {
  assert.equal(sameCompany('ACME PREFERRED INC', 'Beta Preferred Inc'), false);
});

/**
 * The historical registry, built from SEC bulk Form 345 submissions. It knows
 * what a ticker meant while it meant it, which the live register cannot.
 */
const registry = new Map([
  ['MASI', [{ issuer_name: 'MASIMO CORP', first_seen: '2024-02-01', last_seen: '2025-11-17' }]],
  // Also in the live register, so precedence between the two is observable.
  // Without an overlap nothing can tell whether the historical tier is being
  // consulted when it should not be.
  ['LRCX', [{ issuer_name: 'LAM RESEARCH CORP', first_seen: '2016-01-04', last_seen: '2026-08-01' }]],
  ['PARA', [
    { issuer_name: 'Banzai International, Inc.', first_seen: '2026-01-05', last_seen: '2026-08-01' },
    { issuer_name: 'Paramount Global', first_seen: '2020-02-01', last_seen: '2024-06-01' },
  ]],
]);
const held = (earliest, latest) => ({ earliest, latest });

test('a delisted ticker is recovered from past filings when the live register has gone quiet', () => {
  // Masimo is not in company_tickers.json any more, so the live check refuses
  // it. Past filings still name MASI as MASIMO CORP, and the company check is
  // the same one - only the register it runs against has changed.
  const r = recoverTicker('MASI*', 'MASIMO CORP', sec, { registry, window: held('2023-09-30', '2025-12-31') });
  assert.equal(r.ticker, 'MASI');
  assert.match(r.via, /SEC filings/);
});

test('a reused ticker resolves to the company that held it at the time', () => {
  // The case the windows exist for. PARA was Paramount Global until 2024 and
  // is Banzai International now; a 2021 holding must not be attributed to a
  // company that did not own the symbol until five years later.
  const r = recoverTicker('PARAEUR', 'PARAMOUNT GLOBAL', sec, { registry, window: held('2021-03-31', '2021-12-31') });
  assert.equal(r.ticker, 'PARA');
});

test('a name that matches the wrong era is still refused', () => {
  // Banzai genuinely owns PARA now. A holding from 2021 does not become
  // Banzai's because the ticker later became theirs.
  const r = recoverTicker('PARAEUR', 'Banzai International, Inc.', sec, { registry, window: held('2021-03-31', '2021-12-31') });
  assert.equal(r.ticker, null);
});

test('the live register still wins when it has an answer', () => {
  // A currently-registered ticker must never be overruled by what it used to
  // be, so the historical tier only runs when the live one found nothing.
  // LRCX is in both registers, which is what makes the precedence testable:
  // if the historical tier ran anyway it would claim the answer as its own,
  // and a clean live match could be turned into an ambiguity by a second base
  // arriving from the past.
  const r = recoverTicker('LRCXEUR', 'LAM RESEARCH CORP', sec, { registry, window: held('2020-03-31', '2026-06-30') });
  assert.equal(r.ticker, 'LRCX');
  assert.equal(r.via, 'the SEC register');
});

test('without a registry the behaviour is exactly as before', () => {
  const r = recoverTicker('MASI*', 'MASIMO CORP', sec);
  assert.equal(r.ticker, null);
});

const nameRegistry = new Map([
  ['HOLX', [{ issuer_name: 'HOLOGIC INC', first_seen: '2016-02-01', last_seen: '2026-08-01' }]],
  ['CFLT', [{ issuer_name: 'Confluent, Inc.', first_seen: '2021-07-01', last_seen: '2026-08-01' }]],
  ['ACME', [{ issuer_name: 'ACME CORP', first_seen: '2016-01-01', last_seen: '2020-01-01' }]],
  ['ACMX', [{ issuer_name: 'ACME CORP', first_seen: '2020-02-01', last_seen: '2026-01-01' }]],
]);

test('a symbol with no ticker in it is recovered from the issuer name', () => {
  // HO1 is a venue line number and carries nothing to extract. The holding
  // still names Hologic, and past filings say Hologic filed under HOLX.
  const r = recoverTicker('HO1', 'HOLOGIC INC', sec, {
    registry: nameRegistry, window: { earliest: '2019-03-31', latest: '2024-12-31' },
  });
  assert.equal(r.ticker, 'HOLX');
  assert.match(r.via, /issuer name/);
});

test('a name that fits two tickers is refused, not resolved to the first', () => {
  // ACME CORP filed under ACME and later ACMX. Over a window covering both,
  // there is no single right answer and picking one is the guess this whole
  // module exists to avoid.
  const r = recoverTicker('8QR', 'ACME CORP', sec, {
    registry: nameRegistry, window: { earliest: '2016-03-31', latest: '2025-12-31' },
  });
  assert.equal(r.ticker, null);
  assert.match(r.reason, /fits 2 of them/);
});

test('the window narrows a name that would otherwise be ambiguous', () => {
  // The same name over a window that only one of the two tickers covers.
  const r = recoverTicker('8QR', 'ACME CORP', sec, {
    registry: nameRegistry, window: { earliest: '2016-03-31', latest: '2017-12-31' },
  });
  assert.equal(r.ticker, 'ACME');
});

test('name recovery only runs when the symbol yields nothing', () => {
  // MASI* has a ticker in it. Falling back to a name search would let an
  // unrelated issuer with a similar name overrule what the symbol plainly says.
  const r = recoverTicker('MASI*', 'HOLOGIC INC', sec, { registry: nameRegistry });
  assert.equal(r.ticker, null);
  assert.doesNotMatch(String(r.reason), /issuer name fits/);
});

test('an unrecoverable symbol with no matching issuer says both things', () => {
  const r = recoverTicker('62C', 'NOBODY AT ALL INC', sec, { registry: nameRegistry });
  assert.equal(r.ticker, null);
  assert.match(r.reason, /no filing names this issuer/);
});
