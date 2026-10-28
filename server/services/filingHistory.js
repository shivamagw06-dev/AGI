/**
 * How far back a manager's 13F history reaches.
 *
 * EDGAR splits a filer's index in two. `filings.recent` holds the most recent
 * thousand filings of every type, and everything older is in separate files
 * listed under `filings.files`. Only the first was ever read, and the selection
 * was then capped at sixteen quarters and asked for twelve.
 *
 * For Berkshire that is 12 of 211. The recent block alone carries 44 quarters
 * of 13F back to 2016; the archive file carries 167 more, to 1998. The cap was
 * the binding limit, not the data.
 *
 * The archive is only fetched when the recent block cannot satisfy the request,
 * so a daily run asking for a few quarters still makes one request per manager.
 * A deep backfill pays one extra request and reaches the beginning.
 */

const THIRTEEN_F = new Set(['13F-HR', '13F-HR/A']);

/**
 * Turn EDGAR's columnar block into rows.
 *
 * Both blocks use the same shape - parallel arrays keyed by field - and both
 * carry acceptanceDateTime, which the point-in-time rules depend on. Where it
 * is absent the filing date stands in at midnight UTC, which is earlier than
 * any real acceptance and therefore never lets a backtest trade sooner than it
 * could have.
 */
export function rowsFromBlock(block) {
  const forms = block?.form || [];
  return forms.map((form, index) => ({
    form_type: form,
    accession_number: block.accessionNumber?.[index],
    report_date: block.reportDate?.[index],
    filing_date: block.filingDate?.[index],
    accepted_at: block.acceptanceDateTime?.[index] || `${block.filingDate?.[index]}T00:00:00Z`,
    primary_document: block.primaryDocument?.[index] || '',
  })).filter((row) => THIRTEEN_F.has(row.form_type) && row.report_date && row.accession_number);
}

/** The distinct report dates present, newest first. */
export function periodsOf(rows) {
  return [...new Set((rows || []).map((row) => row.report_date))].sort().reverse();
}

/**
 * Whether the archive files are worth fetching.
 *
 * Only when the recent block cannot cover the request. A daily run asking for
 * a few quarters gets them from the block it already has, and pays nothing.
 */
export function needsArchive(recentRows, quarters) {
  const wanted = Math.max(1, Number(quarters) || 1);
  return periodsOf(recentRows).length < wanted;
}

/** The archive files that could hold 13F filings, newest first. */
export function archiveFiles(submissions) {
  return (submissions?.filings?.files || [])
    .filter((file) => file?.name)
    .sort((a, b) => String(b.filingTo || '').localeCompare(String(a.filingTo || '')));
}

/**
 * Select the filings to ingest: every filing for the newest N report dates.
 *
 * Every filing for a period, not the newest one - an amendment and the original
 * it restates are both needed, and they are ordered by acceptance so the
 * amendment is applied after the filing it corrects rather than before it.
 */
export function selectThirteenF(rows, quarters, { maxQuarters = 400 } = {}) {
  const wanted = Math.max(1, Math.min(Number(quarters) || 4, maxQuarters));
  const periods = new Set(periodsOf(rows).slice(0, wanted));
  return (rows || [])
    .filter((row) => periods.has(row.report_date))
    .sort((a, b) => String(a.accepted_at).localeCompare(String(b.accepted_at)));
}
