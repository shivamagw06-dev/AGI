/**
 * Find a security by the name people actually know it by.
 *
 * The stock box asked for "a US ticker or verified CUSIP" and navigated
 * straight to whatever was typed. Typing APPLE produced a page for a security
 * called APPLE, which does not exist. Almost nobody outside a desk knows that
 * Alphabet Class C is GOOG and Class A is GOOGL, or that Taiwan Semiconductor
 * files as TSM - and a search box that only rewards people who already know
 * the answer is not doing any work.
 *
 * The index is built once and cached rather than queried per keystroke. The
 * holdings table is 72,401 rows and a substring match against issuer names
 * cannot use an index, so doing that on every keypress is exactly the kind of
 * full scan the admin guards exist to prevent. Built once, it is a few
 * thousand distinct securities held in memory and searched in microseconds.
 */

import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
// Re-exported so callers keep one import for the whole concern, while the pure
// half stays reachable without a database driver.
import { normalise, rank } from './securityRanking.js';

export { normalise, rank };

const CACHE_TTL_MS = 15 * 60_000;
const PAGE = 1000;
/** A ceiling, so a runaway table cannot pull unbounded rows into memory. */
const MAX_ROWS = 60_000;

let cached = null;      // { at, index }
let building = null;    // shared in-flight build

function db() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Institutional security search is not configured.');
  return client;
}

/**
 * One entry per security, carrying how widely it is held so the ranking can
 * prefer a name fifty managers own over one that appears once.
 */
async function buildIndex() {
  const client = db();

  // Only active filings: a superseded amendment's rows would otherwise put
  // withdrawn positions in the search results.
  const { data: filings, error: filingError } = await client
    .from('institutional_filings')
    .select('id')
    .eq('is_active', true);
  if (filingError) throw new Error(filingError.message);

  const filingIds = (filings || []).map((row) => row.id);
  if (!filingIds.length) return [];

  const byKey = new Map();
  for (let i = 0; i < filingIds.length && byKey.size < MAX_ROWS; i += 100) {
    const slice = filingIds.slice(i, i + 100);
    for (let from = 0; from < MAX_ROWS; from += PAGE) {
      const { data, error } = await client
        .from('institutional_holdings')
        .select('cusip,ticker,issuer_name,manager_id')
        .in('filing_id', slice)
        .range(from, from + PAGE - 1);
      if (error) throw new Error(error.message);
      if (!data?.length) break;

      for (const row of data) {
        const key = String(row.cusip || row.ticker || '').trim().toUpperCase();
        if (!key) continue;
        let entry = byKey.get(key);
        if (!entry) {
          entry = {
            cusip: row.cusip || null,
            ticker: row.ticker || null,
            issuer_name: row.issuer_name || null,
            owners: new Set(),
          };
          byKey.set(key, entry);
        }
        // A later filing may resolve a ticker an earlier one lacked.
        if (!entry.ticker && row.ticker) entry.ticker = row.ticker;
        if (!entry.issuer_name && row.issuer_name) entry.issuer_name = row.issuer_name;
        if (row.manager_id) entry.owners.add(row.manager_id);
      }
      if (data.length < PAGE) break;
    }
  }

  return [...byKey.values()].map((entry) => ({
    cusip: entry.cusip,
    ticker: entry.ticker,
    issuer_name: entry.issuer_name,
    owners: entry.owners.size,
    haystack: normalise(`${entry.issuer_name || ''} ${entry.ticker || ''}`),
  }));
}

async function getIndex() {
  if (cached && Date.now() - cached.at < CACHE_TTL_MS) return cached.index;
  if (building) return building;
  building = buildIndex()
    .then((index) => { cached = { at: Date.now(), index }; return index; })
    .finally(() => { building = null; });
  return building;
}

export async function searchSecurities(term, limit = 8) {
  const index = await getIndex();
  return rank(index, term, limit);
}

/**
 * Build the index before anyone asks for it.
 *
 * The first query after a deploy otherwise pays for the whole build - paging
 * every active filing's holdings - and the first person to type in the box got
 * a request that ran long enough to look broken. Warm, a query answers in
 * under two tenths of a second.
 *
 * Failures are swallowed deliberately: this is a cache warm, and a database
 * that is not ready at boot must not take the router down with it. The next
 * request rebuilds.
 */
export function warmSecuritySearchIndex() {
  getIndex().catch((error) => {
    console.warn(`[institutional-holdings] security index warm failed: ${error.message}`);
  });
}

/** Test seam and admin refresh. */
export function clearSecuritySearchCache() { cached = null; building = null; }
