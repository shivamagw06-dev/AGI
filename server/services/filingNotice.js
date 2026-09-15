/**
 * A manager that files a notice instead of a holdings report.
 *
 * Form 13F comes in two shapes. 13F-HR carries the information table - the
 * holdings. 13F-NT is a notice, filed when the manager holds no section 13(f)
 * securities of its own because everything it would report is being reported
 * by a different filer.
 *
 * The parser correctly ignores notices: there is no table in one. But ignoring
 * a notice and having no filing at all are different facts, and the system
 * conflated them. Vanguard filed 13F-NT for 2026-03-31 and 2026-06-30, so its
 * newest holdings report is 2025-12-31 - and the fund page presented a
 * December book as the current one, while the manager was merely marked
 * `stale`, which reads as "late".
 *
 * It is not late. It is reporting somewhere else, and the distinction decides
 * whether a reader should wait for an update or go and find the other filer:
 *
 *   Scion   newest of any kind is 13F-HR 2025-09-30 -> stopped filing
 *   Vanguard newest is 13F-NT 2026-06-30            -> reports through another
 */

export const HOLDINGS_FORMS = Object.freeze(new Set(['13F-HR', '13F-HR/A']));
export const NOTICE_FORMS = Object.freeze(new Set(['13F-NT', '13F-NT/A']));

/**
 * Notices from an EDGAR filings block, newest report first.
 *
 * Kept separate from rowsFromBlock rather than folded into it. Anything that
 * reaches the ingest path gets its information table read, and a notice has
 * none - it would fail as "no 13F information table found", which is true and
 * useless.
 */
export function noticesFromBlock(block) {
  const forms = block?.form || [];
  return forms
    .map((form, index) => ({
      form_type: form,
      accession_number: block.accessionNumber?.[index],
      report_date: block.reportDate?.[index],
      filing_date: block.filingDate?.[index],
    }))
    .filter((row) => NOTICE_FORMS.has(row.form_type) && row.report_date)
    .sort((a, b) => String(b.report_date).localeCompare(String(a.report_date)));
}

/**
 * What a manager's filing record actually says about it.
 *
 * Three outcomes, and they call for three different things from a reader:
 *
 *   current          the newest filing of any kind is a holdings report
 *   reports_elsewhere a notice is newer than the newest holdings report
 *   stale            neither - the manager has simply not filed
 *
 * Ties go to the holdings report. A manager that files both an HR and an NT
 * for one period has disclosed holdings for it, and the notice covers some
 * other part of the group.
 */
export function filingPosture({ newestHoldingsReport, notices = [] } = {}) {
  const holdings = String(newestHoldingsReport || '') || null;
  const newestNotice = notices.length ? String(notices[0]?.report_date || '') || null : null;

  if (!newestNotice) return { posture: holdings ? 'current' : 'none', notice_period: null };
  // Strictly newer. Equal periods mean the manager filed both, and the
  // holdings report is the one that carries information.
  if (holdings && newestNotice <= holdings) return { posture: 'current', notice_period: null };
  return { posture: 'reports_elsewhere', notice_period: newestNotice };
}

/**
 * The sentence shown against the manager.
 *
 * It has to say what a reader should do, not just what happened. "Latest
 * available 13F reports 2025-12-31" invites waiting for the next one, which
 * will never come in that form.
 */
export function postureMessage({ posture, notice_period: noticePeriod, newestHoldingsReport }) {
  if (posture === 'reports_elsewhere') {
    return `Filed a 13F-NT notice for ${noticePeriod}, so its holdings are reported by another filer.`
      + `${newestHoldingsReport ? ` The last holdings report was ${newestHoldingsReport}.` : ''}`;
  }
  if (posture === 'none') return 'No Form 13F holdings report has been filed.';
  return null;
}
