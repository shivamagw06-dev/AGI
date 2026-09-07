/**
 * How a security search result is ordered, and how a typed term is folded
 * before matching.
 *
 * Separate from the search service because none of it touches a database. The
 * service imports the Supabase client at module load, so a test of this
 * ordering could not run without the driver installed - which is what the
 * no-install CI job that guards it cannot provide. This is the second time
 * that has bitten; logic with no I/O should not be reachable only through
 * something that has some.
 */

/** Fold accents and punctuation so "Moet" finds "Moët" and "AT&T" finds "AT T". */
export function normalise(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toUpperCase()
    .replace(/[^A-Z0-9 ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Rank matches the way a person expects them.
 *
 * An exact ticker first - someone typing AAPL means AAPL and nothing else.
 * Then names that start with the term, because "APP" should surface Apple
 * before Applied Materials. Then anything containing it. Breadth of ownership
 * breaks remaining ties, since a name fifty managers hold is more likely the
 * one being looked for than a single position somewhere.
 */
export function rank(index, rawTerm, limit = 8) {
  const term = normalise(rawTerm);
  if (term.length < 2) return [];

  const scored = [];
  for (const entry of index) {
    const ticker = normalise(entry.ticker);
    const name = normalise(entry.issuer_name);
    let tier;
    if (ticker && ticker === term) tier = 0;
    else if (name.startsWith(term)) tier = 1;
    else if (ticker && ticker.startsWith(term)) tier = 2;
    else if (entry.haystack.includes(term)) tier = 3;
    else continue;
    scored.push({ entry, tier });
  }

  scored.sort((a, b) =>
    a.tier - b.tier
    || b.entry.owners - a.entry.owners
    || String(a.entry.issuer_name || '').localeCompare(String(b.entry.issuer_name || '')));

  return scored.slice(0, limit).map(({ entry }) => ({
    cusip: entry.cusip,
    ticker: entry.ticker,
    issuer_name: entry.issuer_name,
    owners: entry.owners,
    // What the page should navigate to. A ticker when we have one, because the
    // URL is shareable and readable; the CUSIP when we do not.
    key: entry.ticker || entry.cusip,
  }));
}
