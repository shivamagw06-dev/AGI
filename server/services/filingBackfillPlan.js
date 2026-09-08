/**
 * Which 13F filings a run still has to fetch.
 *
 * Every run re-downloaded and re-parsed every filing in its window, whether or
 * not the database already held it. At twelve quarters that is about twelve
 * hundred wasted EDGAR requests a night for tables that cannot change. At the
 * forty-two quarters a 2016 backfill needs, it is fatal:
 *
 *   51 managers x 42 periods x 2 requests = ~4,300 requests, which at the
 *   five-per-second limit is fifteen minutes of pure waiting before any
 *   parsing, against a fifty-minute ceiling that also has three million rows
 *   to write.
 *
 * A run that hits the ceiling is abandoned partway. Managers are ordered by
 * display_name, so the same alphabetical head is covered every time and the
 * tail is never reached - the next run starts over and redoes exactly the work
 * that already succeeded. Without this the backfill does not converge; it just
 * burns the rate budget on Appaloosa and AQR forever.
 *
 * With it, a completed manager costs one submissions request and no filing
 * fetches, so each run advances into work the last one did not reach.
 */

/**
 * A stored filing counts as done only if it actually has holdings.
 *
 * holdings_count is zero when a previous attempt stored the filing row and
 * then failed to parse its table. Treating that as done would make the gap
 * permanent, because nothing would ever fetch it again.
 *
 * Written to fail towards fetching. A null, a string, a missing field - all
 * fall through to "fetch it again", which costs a request. The other
 * direction costs a hole in the data that no later run repairs.
 */
export function isIngested(stored) {
  const count = Number(stored?.holdings_count);
  return Number.isFinite(count) && count > 0;
}

/**
 * Split the available filings into what to fetch and what to skip.
 *
 * An amendment is never skipped by accident: a 13F-HR/A carries its own
 * accession number, so it is simply not among the stored ones and falls into
 * fetch on its own.
 */
export function ingestPlan({ available = [], stored = [], refetch = false } = {}) {
  const done = new Set(
    (stored || [])
      .filter((row) => isIngested(row))
      .map((row) => String(row?.accession_number || '')),
  );

  const fetch = [];
  const skipped = [];
  for (const filing of available || []) {
    const accession = String(filing?.accession_number || '');
    // refetch exists for the case this cache is wrong: a parser fix means the
    // stored rows are stale in a way holdings_count cannot show.
    if (!refetch && accession && done.has(accession)) skipped.push(filing);
    else fetch.push(filing);
  }

  return {
    fetch,
    skipped: skipped.length,
    // Reported so a run that fetches nothing reads as "already complete"
    // rather than as a manager with no filings, which is an error elsewhere.
    total: (available || []).length,
  };
}
