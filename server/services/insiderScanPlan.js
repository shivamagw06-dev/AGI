/**
 * Deciding whose insider filings to fetch, and which of them are new.
 *
 * The universe is roughly four thousand eight hundred held tickers, each with
 * its own stream of Form 4s. Fetching every document every run is forty-eight
 * thousand requests against an endpoint that allows five a second, so the
 * question is not how to fetch them but how to fetch only what changed.
 *
 * Two things make a run incremental. A scan log records when a ticker was last
 * looked at, so a run covers what has aged rather than starting again. And the
 * accession numbers already stored are known, so a ticker that has filed
 * nothing new costs one request for its index and no document fetches at all.
 *
 * The price backfill learned both of these the hard way - three attempts at
 * "when did we last look at this" before the answer was to record it rather
 * than infer it from what was written.
 */

/** Symbols worth asking about: a US ticker, and one we have a CIK for. */
export function planScans(tickers, { companies, scannedAt = null, asOf, maxAgeDays = 7 } = {}) {
  const plans = [];
  const skipped = { noCik: 0, recentlyScanned: 0 };
  const seen = new Set();

  for (const raw of tickers || []) {
    const ticker = String(raw || '').trim().toUpperCase();
    if (!ticker || seen.has(ticker)) continue;
    seen.add(ticker);

    const company = companies?.get?.(ticker);
    if (!company?.cik) { skipped.noCik += 1; continue; }

    // A ticker looked at recently is left alone. Form 4s arrive within two
    // business days of a trade, so a week-old scan misses little and a daily
    // sweep of the whole universe wastes most of its requests.
    const last = scannedAt?.get?.(ticker);
    if (last && asOf && daysBetween(last, asOf) <= maxAgeDays) { skipped.recentlyScanned += 1; continue; }

    plans.push({ ticker, cik: company.cik, title: company.title || null });
  }
  // Ordered by a hash, not alphabetically. A limited run must look like the
  // universe rather than like the front of the alphabet - the price backfill
  // aborted on a sample of digit-leading junk before that was fixed.
  plans.sort((a, b) => spread(a.ticker) - spread(b.ticker) || a.ticker.localeCompare(b.ticker));
  return { plans, skipped };
}

/**
 * The filings worth fetching for one issuer.
 *
 * Anything already stored is skipped by accession number, so a ticker that has
 * filed nothing new costs one index request and no document fetches. Amended
 * filings carry their own accession and are collected in their own right.
 */
export function newFilings(rows, known, { limit = 40, since = null } = {}) {
  return (rows || [])
    .filter((row) => /^4(\/A)?$/.test(String(row?.form || '')))
    .filter((row) => row?.accession && !known?.has?.(row.accession))
    .filter((row) => !since || !row.filedAt || String(row.filedAt).slice(0, 10) >= since)
    .sort((a, b) => String(b.filedAt || '').localeCompare(String(a.filedAt || '')))
    .slice(0, limit);
}

/**
 * Whether a run has gone wrong badly enough to stop.
 *
 * A run that keeps going while every document fails does not produce partial
 * coverage - it produces a table of filings nobody can read, indistinguishable
 * from issuers that simply did not file.
 */
export function abortReason(tally, { minSample = 40, maxUnreadable = 0.5 } = {}) {
  const done = tally.parsed + tally.unreadable;
  if (done < minSample) return null;
  if (tally.unreadable / done > maxUnreadable) {
    return `${((tally.unreadable / done) * 100).toFixed(1)}% of ${done} documents could not be parsed`
      + ' - the document shape or the fetch is wrong, not the individual filings';
  }
  return null;
}

function daysBetween(a, b) {
  const d = (Date.parse(b) - Date.parse(a)) / 86_400_000;
  return Number.isFinite(d) ? d : Infinity;
}

/** A stable pseudo-random ordering key. FNV-1a. */
function spread(value) {
  let h = 2166136261;
  for (let i = 0; i < value.length; i += 1) { h ^= value.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
