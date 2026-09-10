import test from 'node:test';
import assert from 'node:assert/strict';
import { securityCandidates } from '../services/securityCandidates.js';

const hold = (over = {}) => ({
  cusip: '30231G102', ticker: 'XOM', issuer_name: 'EXXON MOBIL CORP',
  report_date: '2026-06-30', value_usd: 1_000_000, ...over,
});

test('the case this exists for: one filer\'s mangled symbol does not decide the security', () => {
  // 30231G102 is Exxon Mobil whatever a single filer typed. The code this
  // replaces kept one holding per security and let the last win, so EXMOC
  // could become the identity of $144.9bn.
  const [security] = securityCandidates([
    hold({ ticker: 'XOM' }), hold({ ticker: 'XOM' }), hold({ ticker: 'XOM' }),
    hold({ ticker: 'EXMOC' }),
  ]);
  assert.deepEqual(security.tickers, ['XOM', 'EXMOC']);
  assert.equal(security.cusip, '30231G102');
});

test('the mangled symbol is kept, not discarded', () => {
  // It is still the only symbol some filers used, and if the majority symbol
  // resolves to nothing the next one is the remaining chance.
  const [security] = securityCandidates([hold({ ticker: 'XOM' }), hold({ ticker: 'EXMOC' })]);
  assert.equal(security.tickers.length, 2);
});

test('ties break alphabetically, so the order is total', () => {
  // Two symbols filed once each must not depend on holdings order, or two
  // runs classify the same security differently.
  const forwards = securityCandidates([hold({ ticker: 'BBB' }), hold({ ticker: 'AAA' })]);
  const backwards = securityCandidates([hold({ ticker: 'AAA' }), hold({ ticker: 'BBB' })]);
  assert.deepEqual(forwards[0].tickers, ['AAA', 'BBB']);
  assert.deepEqual(backwards[0].tickers, ['AAA', 'BBB']);
});

test('securities come back largest first', () => {
  // A run that is cut short should have spent its requests on the positions
  // that carry the weight.
  const out = securityCandidates([
    hold({ cusip: 'SMALL', ticker: 'S', value_usd: 5 }),
    hold({ cusip: 'HUGE', ticker: 'H', value_usd: 900 }),
    hold({ cusip: 'MID', ticker: 'M', value_usd: 100 }),
  ]);
  assert.deepEqual(out.map((s) => s.key), ['HUGE', 'MID', 'SMALL']);
});

test('value is summed across every filer of the security', () => {
  const [security] = securityCandidates([hold({ value_usd: 10 }), hold({ value_usd: 15 }), hold({ value_usd: 5 })]);
  assert.equal(security.value_usd, 30);
});

test('a non-numeric value does not poison the total', () => {
  // Number(null) is 0 and Number(undefined) is NaN; one addition of NaN makes
  // the whole security sort last for ever.
  const [security] = securityCandidates([hold({ value_usd: 10 }), hold({ value_usd: null }), hold({ value_usd: 'x' }), hold({ value_usd: undefined })]);
  assert.equal(security.value_usd, 10);
});

test('the window spans every report the security appears in', () => {
  const [security] = securityCandidates([
    hold({ report_date: '2026-06-30' }), hold({ report_date: '2025-03-31' }), hold({ report_date: '2026-03-31' }),
  ]);
  assert.equal(security.earliest, '2025-03-31');
  assert.equal(security.latest, '2026-06-30');
});

test('the most-filed issuer name is the one kept', () => {
  const [security] = securityCandidates([
    hold({ issuer_name: 'EXXON MOBIL CORP' }), hold({ issuer_name: 'EXXON MOBIL CORP' }), hold({ issuer_name: 'EXXON  MOBIL' }),
  ]);
  assert.equal(security.issuer_name, 'EXXON MOBIL CORP');
});

test('tickers are upper-cased and trimmed before they are counted', () => {
  // Otherwise ' xom' and 'XOM' are two securities' worth of evidence split
  // across two entries, and neither has a majority.
  const [security] = securityCandidates([hold({ ticker: ' xom ' }), hold({ ticker: 'XOM' }), hold({ ticker: 'EXMOC' })]);
  assert.deepEqual(security.tickers, ['XOM', 'EXMOC']);
});

test('security_key wins over cusip where a row carries one', () => {
  const [security] = securityCandidates([hold({ security_key: 'EXPLICIT' })]);
  assert.equal(security.key, 'EXPLICIT');
});

test('a row with nothing to key on is skipped rather than grouped under blank', () => {
  const out = securityCandidates([{ cusip: '', ticker: '', issuer_name: '' }, hold()]);
  assert.equal(out.length, 1);
});

test('a security with no ticker at all still comes back', () => {
  // INVESCO QQQ TR arrives on one CUSIP with a null ticker. It is a real
  // position and the caller decides what to do about it; dropping it here
  // would hide it.
  const [security] = securityCandidates([hold({ ticker: null, cusip: '46090E953' })]);
  assert.deepEqual(security.tickers, []);
  assert.equal(security.key, '46090E953');
});

test('nothing in yields nothing out, without throwing', () => {
  assert.deepEqual(securityCandidates(), []);
  assert.deepEqual(securityCandidates([]), []);
});
