/**
 * One record per security, carrying every ticker it has been filed under.
 *
 * Classification is keyed on the CUSIP, but the lookup that finds a company at
 * the SEC is keyed on the ticker - and managers do not agree on the ticker.
 * The same CUSIP arrives as XOM from most filers and as EXMOC from at least
 * one. The code this replaces built a Map keyed on the security and let the
 * last holding win, so a single filer's mangled symbol could decide the
 * identity of the whole position: 30231G102 is unambiguously Exxon Mobil, and
 * $144.9bn of it sat unclassified because the representative holding said
 * EXMOC.
 *
 * Every distinct ticker is kept instead, most-filed first, so the caller can
 * try the next one when the first resolves to nothing. Agreement among filers
 * is the signal: a symbol one manager typed is not evidence against the symbol
 * forty of them typed.
 *
 * Securities come back largest first. A classification run that is cut short -
 * by a rate limit, a timeout, an operator - should have spent its requests on
 * the positions that carry the weight.
 */

const clean = (value) => String(value ?? '').trim();
const upper = (value) => clean(value).toUpperCase();

/**
 * @param {object[]} holdings rows carrying cusip, ticker, issuer_name,
 *   report_date and value_usd
 * @returns {{key: string, cusip: string|null, issuer_name: string|null,
 *   tickers: string[], earliest: string|null, latest: string|null,
 *   value_usd: number}[]}
 */
export function securityCandidates(holdings) {
  const byKey = new Map();

  for (const row of holdings || []) {
    const cusip = upper(row?.cusip);
    const ticker = upper(row?.ticker || row?.mapped_ticker);
    const key = upper(row?.security_key) || cusip || ticker || upper(row?.issuer_name);
    if (!key) continue;

    let entry = byKey.get(key);
    if (!entry) {
      entry = { key, cusip: cusip || null, tickers: new Map(), names: new Map(), earliest: null, latest: null, value_usd: 0 };
      byKey.set(key, entry);
    }

    if (ticker) entry.tickers.set(ticker, (entry.tickers.get(ticker) || 0) + 1);
    const name = clean(row?.issuer_name);
    if (name) entry.names.set(name, (entry.names.get(name) || 0) + 1);

    const value = Number(row?.value_usd);
    if (Number.isFinite(value)) entry.value_usd += value;

    const date = clean(row?.report_date).slice(0, 10);
    if (date) {
      if (!entry.earliest || date < entry.earliest) entry.earliest = date;
      if (!entry.latest || date > entry.latest) entry.latest = date;
    }
  }

  const out = [...byKey.values()].map((entry) => ({
    key: entry.key,
    cusip: entry.cusip,
    issuer_name: mostCommon(entry.names),
    tickers: rank(entry.tickers),
    earliest: entry.earliest,
    latest: entry.latest,
    value_usd: entry.value_usd,
  }));

  // Largest first, then by key so the order is total and a run is repeatable.
  out.sort((a, b) => (b.value_usd - a.value_usd) || a.key.localeCompare(b.key));
  return out;
}

/** Keys by count, highest first, ties broken alphabetically so it is total. */
function rank(counts) {
  return [...counts.entries()]
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
    .map(([value]) => value);
}

function mostCommon(counts) {
  return rank(counts)[0] || null;
}
