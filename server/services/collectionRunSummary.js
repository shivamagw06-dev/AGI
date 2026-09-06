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
export function deriveStatus({ attempted, succeeded, error, aborted, roster = 0 }) {
  if (aborted) return 'aborted';
  if (error && !succeeded) return 'failed';
  if (!attempted) return error ? 'failed' : 'success';
  if (!succeeded) return 'failed';
  if (succeeded < attempted) return 'partial';

  // `attempted` counts the managers that reported finishing, so on a run that
  // was cut short it always equals `succeeded` - the first version of this
  // reported "48/48 success" for a run a database timeout had killed with
  // three of fifty-one never started. Two things therefore override the count:
  //
  //   an error at all means the run did not finish cleanly, whatever it wrote;
  //   and covering fewer managers than the roster means it is incomplete.
  if (error) return 'partial';
  if (roster && succeeded < roster) return 'partial';
  return 'success';
}

/**
 * Turn a refresh result into the counters the run record stores.
 *
 * Kept separate from the collector so it can be tested against real result
 * shapes without a database, and so the meaning of each counter lives in one
 * place rather than being reconstructed at each call site.
 */
export function summariseRefresh(result, rosterSize = 0) {
  const rows = Array.isArray(result?.results) ? result.results : [];
  const succeeded = rows.filter((row) => row?.ok);

  // Two result shapes reach here and only one used to be handled.
  //
  // A single-manager refresh returns { filing, ingestion }. A bulk refresh -
  // which is what the scheduled collector runs - returns { filings: [...] },
  // one entry per filing ingested. Reading only the first shape meant every
  // completed bulk run reported filings: 0, holdings rows: 0, amendments: 0
  // however much it had actually written.
  const ingestedFilings = (row) => {
    if (Array.isArray(row?.filings)) return row.filings;
    return row?.ingestion ? [{ ...row.ingestion, form_type: row?.filing?.form_type }] : [];
  };

  const allFilings = succeeded.flatMap(ingestedFilings);
  const isAmendment = (filing) => String(filing?.form_type || '').toUpperCase().endsWith('/A');

  return {
    // What the run was asked to cover, when the caller knows it. Distinct from
    // `managersAttempted`, which is only what reported back.
    managersInRoster: Number(rosterSize) || 0,
    managersAttempted: rows.length,
    managersSucceeded: succeeded.length,
    filingsIngested: allFilings.filter((filing) => filing?.status === 'ingested').length,
    holdingsRows: allFilings.reduce((total, filing) => total + (Number(filing?.holdings) || 0), 0),
    amendmentsDetected: allFilings.filter(isAmendment).length,
    failures: rows.filter((row) => !row?.ok).map((row) => ({
      manager: row?.manager?.slug || row?.slug || row?.manager?.display_name || 'unknown',
      error: String(row?.error || 'no reason recorded').slice(0, 500),
    })),
  };
}
