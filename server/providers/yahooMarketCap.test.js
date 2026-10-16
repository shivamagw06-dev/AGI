import test from 'node:test';
import assert from 'node:assert/strict';
import { UNITS, fetchMarketCaps, marketCapFromQuote, yahooSymbolFor } from './yahooMarketCap.js';

const quote = (fields) => ({ symbol: 'POWERINDIA.NS', currency: 'INR', marketCap: 1.349e12, ...fields });

const respond = (body, ok = true, status = 200) => async () => ({
  ok, status, json: async () => body,
});

test('NSE symbols take the .NS suffix', () => {
  assert.equal(yahooSymbolFor('powerindia'), 'POWERINDIA.NS');
  assert.equal(yahooSymbolFor(' CGPOWER '), 'CGPOWER.NS');
});

test('market cap is converted to crore, the unit the statements use', () => {
  // The trap this exists for: Yahoo reports whole rupees, the Upstox
  // statements are in crore. A missing 1e7 does not make the cross-check
  // slightly wrong, it makes it fail for every company by seven orders of
  // magnitude - which reads as "the derivation is always wrong".
  const row = marketCapFromQuote(quote({ marketCap: 1.349e12 }));
  assert.equal(row.crore, 134_900);
  assert.equal(row.unit, 'inr_crore');
  assert.equal(UNITS.RUPEES_PER_CRORE, 1e7);
});

test('a quote in the wrong currency is refused, not converted', () => {
  // A dollar market cap against a rupee book value is not a comparison.
  const row = marketCapFromQuote(quote({ currency: 'USD' }));
  assert.equal(row.crore, null);
  assert.equal(row.reason, 'NOT_INR');
  assert.equal(row.currency, 'USD');
});

test('a missing or zero market cap is a reason, not a number', () => {
  assert.equal(marketCapFromQuote(quote({ marketCap: null })).reason, 'NO_MARKET_CAP');
  assert.equal(marketCapFromQuote(quote({ marketCap: 0 })).reason, 'NON_POSITIVE_MARKET_CAP');
});

test('every requested symbol appears in the result', () => {
  // A short map would become a screen that skipped companies rather than one
  // that could not check them.
  return fetchMarketCaps(['POWERINDIA', 'CGPOWER'], {
    fetchImpl: respond({ quoteResponse: { result: [quote({ symbol: 'POWERINDIA.NS' })] } }),
  }).then(({ bySymbol }) => {
    assert.deepEqual(Object.keys(bySymbol).sort(), ['CGPOWER', 'POWERINDIA']);
    assert.equal(bySymbol.POWERINDIA.crore, 134_900);
    assert.equal(bySymbol.CGPOWER.crore, null);
    assert.equal(bySymbol.CGPOWER.reason, 'NOT_RETURNED');
  });
});

test('a rate-limited request means cannot verify, never verified', async () => {
  const { bySymbol, error } = await fetchMarketCaps(['POWERINDIA'], {
    fetchImpl: respond({}, false, 429),
  });
  assert.match(error, /429/);
  assert.equal(bySymbol.POWERINDIA.crore, null);
});

test('a thrown request does not take the caller down with it', async () => {
  const { bySymbol, error } = await fetchMarketCaps(['POWERINDIA'], {
    fetchImpl: async () => { throw new Error('ETIMEDOUT'); },
  });
  assert.match(error, /ETIMEDOUT/);
  assert.equal(bySymbol.POWERINDIA.crore, null);
});
