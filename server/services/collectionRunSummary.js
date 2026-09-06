/**
 * The judgement behind a collection run record: which status a run earns, what
 * its counters mean, and when the next run is due.
 *
 * Separate from the recorder because none of it needs a database. The recorder
 * imports the Supabase client at module load, so a test of this arithmetic
 * could not run without the driver installed - which made the fast, no-install
 * CI job that guards it impossible. Logic with no I/O should not be reachable
 * only through something that has some.
 */

/**
 * Next occurrence of a five-field cron expression, in UTC.
 *
 * Deliberately supports only what the collection schedule uses: fixed minute,
 * fixed hour, every day. Anything else returns null rather than guessing, so
 * the CMS shows "unknown" instead of a confidently wrong time. A general cron
 * parser is a dependency and a source of subtle bugs for a field that exists
 * to tell an operator roughly when to look again.
 */
export function nextScheduledAt(expression, from = new Date()) {
  const match = /^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*$/.exec(String(expression || '').trim());
  if (!match) return null;
  const minute = Number(match[1]);
  const hour = Number(match[2]);
  if (minute > 59 || hour > 23) return null;
  const next = new Date(Date.UTC(
    from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate(), hour, minute, 0, 0,
  ));
  if (next <= from) next.setUTCDate(next.getUTCDate() + 1);
  return next.toISOString();
}

/**
 * Close a run.
 *
 * `status` is derived from the work, not passed in as an opinion: a run where
 * nothing succeeded is 'failed' even if it threw no exception, and one where
 * some managers failed is 'partial' rather than 'success'. A dashboard that
 * shows green while half the universe is missing is worse than no dashboard.
 */
export function deriveStatus({ attempted, succeeded, error, aborted }) {
  if (aborted) return 'aborted';
  if (error && !succeeded) return 'failed';
  if (!attempted) return error ? 'failed' : 'success';
  if (!succeeded) return 'failed';
  if (succeeded < attempted) return 'partial';
  return 'success';
}

/**
 * Turn a refresh result into the counters the run record stores.
 *
 * Kept separate from the collector so it can be tested against real result
 * shapes without a database, and so the meaning of each counter lives in one
 * place rather than being reconstructed at each call site.
 */
export function summariseRefresh(result) {
  const rows = Array.isArray(result?.results) ? result.results : [];
  const succeeded = rows.filter((row) => row?.ok);

  // An amendment is a filing whose SEC form type ends in /A. The service
  // already classifies these at ingestion; this only counts what it found.
  const amendments = succeeded.filter((row) => {
    const form = row?.filing?.form_type || '';
    return typeof form === 'string' && form.toUpperCase().endsWith('/A');
  });

  return {
    managersAttempted: rows.length,
    managersSucceeded: succeeded.length,
    filingsIngested: succeeded.filter((row) => row?.ingestion?.status === 'ingested').length,
    holdingsRows: succeeded.reduce((total, row) => total + (Number(row?.ingestion?.holdings) || 0), 0),
    amendmentsDetected: amendments.length,
    failures: rows.filter((row) => !row?.ok).map((row) => ({
      manager: row?.manager?.slug || row?.slug || row?.manager?.display_name || 'unknown',
      error: String(row?.error || 'no reason recorded').slice(0, 500),
    })),
  };
}
