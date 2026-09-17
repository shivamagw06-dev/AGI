/**
 * Market capitalisation from Yahoo, for cross-checking a derived figure.
 *
 * This is a check, not a source. AGI does not publish these numbers and does
 * not treat them as disclosure: they exist so that a market cap derived from
 * P/B and book equity has something independent to disagree with. Where the
 * two agree the derivation is usable; where they do not, the derivation is
 * refused and the disagreement is the finding.
 *
 * Two things this module is careful about.
 *
 * Units. Yahoo reports market cap in whole rupees; the Upstox statements this
 * is checked against are in crore. A missing 1e7 does not produce a slightly
 * wrong answer, it produces a cross-check that fails for every company by
 * seven orders of magnitude - which reads as "the derivation is always wrong"
 * rather than as a unit bug. So the conversion happens here, once, and the
 * unit is named in the return value.
 *
 * Currency. A quote that is not in INR cannot be compared with a rupee book
 * value at all. Yahoo returns the currency, so it is checked rather than
 * assumed from the .NS suffix.
 */

const BASE = 'https://query1.finance.yahoo.com/v7/finance/quote';
const RUPEES_PER_CRORE = 1e7;

/** NSE symbol to Yahoo's, matching the convention already used in this repo. */
export const yahooSymbolFor = (symbol) => `${String(symbol || '').trim().toUpperCase()}.NS`;

const numeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

/**
 * One Yahoo quote row, reduced to what the cross-check needs.
 *
 * A row in the wrong currency, or with no market cap, comes back with a
 * reason rather than a number: the caller has to be able to tell "Yahoo does
 * not know" from "Yahoo says zero".
 */
export function marketCapFromQuote(row) {
  const currency = String(row?.currency || '').trim().toUpperCase();
  const raw = numeric(row?.marketCap);
  if (raw === null) return { crore: null, currency: currency || null, reason: 'NO_MARKET_CAP' };
  if (currency !== 'INR') return { crore: null, currency: currency || null, reason: 'NOT_INR' };
  if (raw <= 0) return { crore: null, currency, reason: 'NON_POSITIVE_MARKET_CAP' };
  return {
    crore: raw / RUPEES_PER_CRORE,
    unit: 'inr_crore',
    currency,
    asOf: numeric(row?.regularMarketTime),
    reason: null,
  };
}

/**
 * Market caps for a list of NSE symbols, keyed by the symbol passed in.
 *
 * Every requested symbol appears in the result. A symbol Yahoo did not return
 * is present with a reason, because a short map would silently become a
 * screen that skipped companies rather than one that could not check them.
 */
export async function fetchMarketCaps(symbols, { fetchImpl = globalThis.fetch, timeoutMs = 8_000 } = {}) {
  const wanted = [...new Set((symbols || []).map((one) => String(one || '').trim().toUpperCase()).filter(Boolean))];
  const bySymbol = {};
  for (const symbol of wanted) bySymbol[symbol] = { crore: null, currency: null, reason: 'NOT_RETURNED' };
  if (!wanted.length) return { bySymbol, error: null };

  const url = `${BASE}?symbols=${encodeURIComponent(wanted.map(yahooSymbolFor).join(','))}`;
  try {
    const response = await fetchImpl(url, {
      headers: { Accept: 'application/json', 'User-Agent': 'AGI-Research/1.0' },
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!response.ok) {
      // Yahoo rate-limits. A failed check is "cannot verify", never "verified".
      return { bySymbol, error: `yahoo quote request failed (${response.status})` };
    }
    const body = await response.json();
    for (const row of body?.quoteResponse?.result || []) {
      const returned = String(row?.symbol || '').trim().toUpperCase();
      const symbol = wanted.find((one) => yahooSymbolFor(one) === returned);
      if (symbol) bySymbol[symbol] = marketCapFromQuote(row);
    }
    return { bySymbol, error: null };
  } catch (error) {
    return { bySymbol, error: String(error?.message || error) };
  }
}

export const UNITS = Object.freeze({ RUPEES_PER_CRORE });
