/**
 * Which securities to classify next.
 *
 * The nightly refresh took the first sixty distinct securities in holdings
 * order and classified those. Holdings order does not change between nights,
 * so it classified the same sixty every night and the table stopped at seventy
 * rows - not because the limit was too low, but because nothing advanced it.
 * Six months of nightly runs and one night's runs produce the same table.
 *
 * A queue that makes progress needs to know what is already done. Unclassified
 * securities come first, in the order given; once none are left the oldest
 * classifications are refreshed, so a sector that changed hands is eventually
 * revisited without ever starving a security that has never been looked at.
 */

const DAY_MS = 86_400_000;

/**
 * @param {object} options
 * @param {{key: string}[]} options.securities  distinct securities, most
 *   important first - the caller decides what important means
 * @param {{security_key: string, source_as_of?: string}[]} options.classified
 *   what the table already holds
 * @param {number} options.limit  how many to return
 * @param {Date} options.asOf
 * @param {number} options.staleAfterDays  a classification older than this is
 *   eligible for refresh once the backlog is clear
 */
export function classificationQueue({
  securities = [], classified = [], limit = 60, asOf = new Date(), staleAfterDays = 180,
} = {}) {
  if (!Number.isFinite(limit) || limit <= 0) return [];

  const seenAt = new Map();
  for (const row of classified) {
    const key = String(row?.security_key || '').trim().toUpperCase();
    if (!key) continue;
    const parsed = Date.parse(row?.source_as_of || row?.updated_at || '');
    // An unparseable or missing date sorts as infinitely old rather than as
    // null. Not knowing when something was classified is not evidence that it
    // was classified recently, and a real sentinel keeps the comparisons below
    // from resting on `null < number` coercing null to zero - which is true
    // here only by accident of the epoch.
    const at = Number.isFinite(parsed) ? parsed : -Infinity;
    const current = seenAt.get(key);
    // The newest observation of each key: a security can carry several rows,
    // one per valid_from, and it is only as stale as its freshest.
    if (current === undefined || at > current) seenAt.set(key, at);
  }

  const cutoff = asOf.getTime() - staleAfterDays * DAY_MS;
  const fresh = [];
  const stale = [];
  for (const security of securities) {
    const key = String(security?.key || '').trim().toUpperCase();
    if (!key) continue;
    if (!seenAt.has(key)) { fresh.push(security); continue; }
    const at = seenAt.get(key);
    if (at < cutoff) stale.push({ security, at });
  }

  if (fresh.length >= limit) return fresh.slice(0, limit);
  stale.sort((a, b) => a.at - b.at);
  return [...fresh, ...stale.slice(0, limit - fresh.length).map((row) => row.security)];
}
