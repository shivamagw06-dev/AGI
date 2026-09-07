import test from 'node:test';
import assert from 'node:assert/strict';
import { candidateBases, recoverTicker } from '../services/venueTicker.js';
import { normaliseIssuerName as normalise } from '../services/thirteenFList.js';

const sec = new Map([
  ['HON', normalise('Honeywell International Inc')],
  ['LRCX', normalise('Lam Research Corp')],
  ['CCL', normalise('Carnival Corp')],
  ['BLK', normalise('BlackRock Inc')],
  ['ANET', normalise('Arista Networks Inc')],
  ['TRI', normalise('Thomson Reuters Corp')],
  ['CAT', normalise('Caterpillar Inc')],
]);
const recover = (sym, issuer) => recoverTicker(sym, issuer, sec, { normalise });

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
  assert.match(recover('22941EUR', 'ANYTHING').reason, /no currency suffix/);
});

test('a currency code alone does not trim to nothing', () => {
  assert.deepEqual(candidateBases('EUR'), []);
  assert.deepEqual(candidateBases('USD'), []);
});
