/**
 * Which SEC forms carry a manager's own words.
 *
 * The intelligence layer reads publications, and the first question is which
 * managers publish anything to read. A 13F-HR is a table of positions with no
 * prose in it at all; an ARS is the annual report to shareholders, which is
 * where Berkshire's letter lives. Both come from the same filer, and only one
 * is worth handing to an extractor.
 *
 * Three kinds, because they are worth different things:
 *
 *   narrative  - the manager writing at length about what it holds and why.
 *                Annual reports, 10-Ks and fund shareholder reports.
 *   intent     - short, structured, and the most direct statement of purpose
 *                in the public record. Schedule 13D Item 4 says what the
 *                holder intends to do with the stake; 13G says only that it
 *                intends nothing.
 *   positions  - holdings without commentary. Already collected; listed here
 *                so a form is classified rather than silently ignored.
 *
 * Anything unrecognised is left unclassified rather than guessed at. A form
 * type this file has not seen is a question, not a default.
 */

/** Base form, without the /A that marks an amendment. */
export function baseForm(formType) {
  return String(formType || '').trim().toUpperCase().replace(/\/A$/, '');
}

const NARRATIVE = new Set([
  // The annual report to shareholders. Berkshire's letter is filed here.
  'ARS',
  // Operating companies. Item 1 and Item 7 are the business in its own words.
  '10-K', '10-K405', '20-F', '40-F',
  // Registered funds: the shareholder report carries manager commentary.
  'N-CSR', 'N-CSRS',
  // Business development companies and closed-end funds.
  'N-2', 'N-30D',
  // A proxy explains compensation, governance and often strategy.
  'DEF 14A', 'DEFA14A',
  // Prospectuses and their supplements describe the strategy as sold.
  '485BPOS', '497', '424B3',
]);

const INTENT = new Set([
  // Item 4, Purpose of Transaction: what the holder means to do.
  'SC 13D',
  // The passive counterpart. Its content is the choice to file it.
  'SC 13G',
  // A tender offer states terms and reasoning.
  'SC TO-T', 'SC 14D9',
]);

const POSITIONS = new Set([
  '13F-HR', '13F-NT', '3', '4', '5', 'N-PORT-P', 'NPORT-P', 'N-Q', 'N-MFP',
]);

/**
 * What a form is worth to the intelligence layer.
 *
 * Returns null for a form nothing here recognises, which is the honest answer
 * and keeps an unfamiliar type visible in the report rather than filed under
 * a guess.
 */
export function formKind(formType) {
  const base = baseForm(formType);
  if (!base) return null;
  if (NARRATIVE.has(base)) return 'narrative';
  if (INTENT.has(base)) return 'intent';
  if (POSITIONS.has(base)) return 'positions';
  return null;
}

/**
 * Form types grouped by what they are worth, with counts.
 *
 * Takes the raw list EDGAR returns for a filer. Amendments fold into their
 * base form - a 13F-HR/A is still a holdings table - but the count records
 * every filing, because a manager that amends constantly is telling you
 * something too.
 */
export function summariseForms(formTypes = []) {
  const counts = new Map();
  for (const formType of formTypes) {
    const base = baseForm(formType);
    if (!base) continue;
    counts.set(base, (counts.get(base) || 0) + 1);
  }
  const rows = [...counts.entries()]
    .map(([form, count]) => ({ form, count, kind: formKind(form) }))
    .sort((a, b) => b.count - a.count || a.form.localeCompare(b.form));
  return {
    rows,
    narrative: rows.filter((row) => row.kind === 'narrative'),
    intent: rows.filter((row) => row.kind === 'intent'),
    positions: rows.filter((row) => row.kind === 'positions'),
    unclassified: rows.filter((row) => row.kind === null),
    total: formTypes.length,
  };
}
