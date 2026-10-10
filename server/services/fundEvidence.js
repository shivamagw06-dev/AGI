/**
 * Whether a registrant is a fund, from the forms it files.
 *
 * EDGAR gives trusts no SIC code. SPY, QQQ and Vanguard Index Funds all
 * report an empty one, so the sector map - which correctly refuses to guess
 * from a missing code - returned Unclassified for $466bn of SPY and QQQ
 * alone. They were never skipped; they were classified, as nothing.
 *
 * The forms are the evidence the SIC code is missing. A registered fund or
 * unit investment trust files under the Investment Company Act: 485BPOS to
 * amend its registration, 497 for its prospectus, 24F-2NT for shares sold,
 * NPORT-P and N-CEN for its portfolio. An operating company files none of
 * them, ever. That evidence is already inside the submissions payload the
 * classifier fetches, so this costs nothing.
 *
 * N-PX is deliberately absent from the list. Since 2022 every institutional
 * manager required to file 13F also files N-PX to report its say-on-pay
 * votes, so it is evidence of being an institution, not of being a fund - and
 * treating it as the latter would reclassify the managers themselves.
 */

/**
 * Forms only a registered investment company or UIT files.
 *
 * Prefix-matched, so 485BPOS covers 485BXT and N-CSR covers N-CSRS. Kept as a
 * list of what each one is, because the cost of a wrong entry here is a whole
 * sector being wrong on the chart.
 */
export const FUND_FORM_PREFIXES = [
  '485',      // post-effective amendments to an N-1A registration
  '497',      // prospectus and summary prospectus materials
  '24F-2NT',  // annual notice of securities sold
  'NPORT',    // monthly portfolio holdings
  'N-CEN',    // annual census of a registered fund
  'N-CSR',    // certified shareholder report
  'N-30',     // periodic shareholder reports and N-30B-2
  'N-1A',     // open-end fund registration
  'N-2',      // closed-end fund registration
  'N-3', 'N-4', 'N-6', // separate-account and variable-contract registrations
  'N-8',      // notification of registration, N-8A and N-8B-2
  'N-14',     // fund merger registration
  'N-MFP',    // money market fund portfolio
  'N-Q',      // quarterly portfolio schedule, retired but present in history
];

/**
 * True where the registrant's recent filings include an Investment Company
 * Act form. One is enough: an operating company never files any of them.
 */
export function filesAsFund(submission) {
  const forms = submission?.filings?.recent?.form;
  if (!Array.isArray(forms)) return false;
  return forms.some((form) => {
    const value = String(form || '').trim().toUpperCase();
    if (!value) return false;
    return FUND_FORM_PREFIXES.some((prefix) => value.startsWith(prefix));
  });
}
