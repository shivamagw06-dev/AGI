/**
 * A record of what each ticker meant, built from Form 345 submissions.
 *
 * The SEC's company_tickers.json lists what is registered now. That is the
 * right authority for a live holding and the wrong one for a decade of them:
 * Activision, Pioneer, Seagen, Splunk, WestRock, Marathon Oil, Discover and
 * Electronic Arts have all left it, and a venue-coded holding in any of them
 * is refused because nothing can confirm a ticker that no longer exists.
 *
 * Every quarterly SUBMISSION.tsv names the issuer, its CIK and its trading
 * symbol as filed. The union across quarters says what each ticker meant while
 * it meant it - which is exactly the question, and one the live file cannot
 * answer by construction.
 *
 * The windows matter as much as the pairs. A ticker that changes hands appears
 * twice with disjoint windows, and PARA is the case that proves it: Paramount
 * Global until 2024, Banzai International after. A 2019 holding must resolve
 * to the first, and the only thing that can tell them apart is when.
 */

/**
 * Distinct issuer/ticker pairs from parsed SUBMISSION rows, with their window.
 *
 * Keyed on ticker and CIK together. The same company can change ticker and the
 * same ticker can change company; only the pair is stable, and collapsing on
 * either alone silently merges two facts into one.
 */
export function issuerTickerPairs(submissions, { bulkDate } = {}) {
  const toDate = typeof bulkDate === 'function' ? bulkDate : (value) => String(value || '').slice(0, 10) || null;
  const pairs = new Map();

  for (const row of submissions || []) {
    const ticker = String(row?.ISSUERTRADINGSYMBOL || '').trim().toUpperCase();
    const cik = String(row?.ISSUERCIK || '').trim();
    const name = String(row?.ISSUERNAME || '').trim();
    // All three are required. A row missing any of them is not a mapping, and
    // storing a blank ticker would make it match every unresolvable symbol.
    if (!ticker || !cik || !name) continue;

    const filed = toDate(row?.FILING_DATE);
    if (!filed) continue;

    const key = `${ticker}|${cik}`;
    const current = pairs.get(key);
    if (!current) {
      pairs.set(key, { cik, ticker, issuer_name: name, first_seen: filed, last_seen: filed, filings: 1 });
      continue;
    }
    if (filed < current.first_seen) current.first_seen = filed;
    if (filed > current.last_seen) current.last_seen = filed;
    current.filings += 1;
  }

  return [...pairs.values()];
}

/**
 * Merge a quarter's pairs into what is already stored.
 *
 * Windows widen rather than replace: a pair seen in 2024 and again in 2026 was
 * observed across both, and a later import must not narrow the record to
 * whatever it happened to load.
 */
export function mergePairs(stored, incoming) {
  const merged = new Map();
  for (const row of [...(stored || []), ...(incoming || [])]) {
    const key = `${row.ticker}|${row.cik}`;
    const current = merged.get(key);
    if (!current) { merged.set(key, { ...row }); continue; }
    if (row.first_seen < current.first_seen) current.first_seen = row.first_seen;
    if (row.last_seen > current.last_seen) current.last_seen = row.last_seen;
    current.filings += row.filings || 0;
    // The name from the later observation, because a company that renames
    // keeps its CIK and the newer spelling is the one a reader recognises.
    if (row.last_seen >= current.last_seen && row.issuer_name) current.issuer_name = row.issuer_name;
  }
  return [...merged.values()];
}

/**
 * Every name a ticker has been registered under, newest window first.
 *
 * Returned as a list rather than a single name because a reused ticker has
 * more than one right answer, and which is right depends on when the holding
 * was held. The caller decides that; this refuses to decide it for them.
 */
export function namesByTicker(rows) {
  const index = new Map();
  for (const row of rows || []) {
    const ticker = String(row?.ticker || '').toUpperCase();
    if (!ticker) continue;
    if (!index.has(ticker)) index.set(ticker, []);
    index.get(ticker).push(row);
  }
  index.forEach((list) => list.sort((a, b) => String(b.last_seen).localeCompare(String(a.last_seen))));
  return index;
}

/**
 * Whether a registry entry could describe a holding held over these dates.
 *
 * Overlap, not containment. A holding runs from a quarter-end while the
 * registry runs from a filing date, so the two never align exactly, and
 * requiring one to contain the other would refuse every true pair.
 */
export function windowOverlaps(entry, { earliest, latest } = {}) {
  if (!entry?.first_seen || !entry?.last_seen) return false;
  const from = String(earliest || '').slice(0, 10);
  const to = String(latest || '').slice(0, 10);
  if (!from || !to) return false;
  // A generous margin at both ends. An insider files within two business days
  // of a trade, but a company can be held for a quarter in which no insider
  // filed at all, and the registry only knows the quarters it saw.
  return String(entry.first_seen) <= addYears(to, 1) && String(entry.last_seen) >= addYears(from, -1);
}

function addYears(date, years) {
  const parsed = new Date(`${String(date).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return date;
  parsed.setUTCFullYear(parsed.getUTCFullYear() + years);
  return parsed.toISOString().slice(0, 10);
}
