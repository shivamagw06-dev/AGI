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
 *   votes      - how a manager voted, rather than whether it could. N-PX is
 *                the record of every proxy vote cast.
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
  '10-K', '10-K405', '10-Q', '20-F', '40-F',
  // A material event, described by the company.
  '8-K', '6-K',
  // Registered funds: the shareholder report carries manager commentary.
  'N-CSR', 'N-CSRS',
  // Business development companies and closed-end funds.
  'N-2', 'N-30D',
  // A proxy explains compensation, governance and often strategy.
  'DEF 14A', 'DEFA14A', 'PRE 14A',
  //
  // Proxy contests, and the reason this set is worth having at all.
  //
  // Every other narrative form above comes from an operating company - the six
  // managers filing 10-Ks do so because they are registrants in their own
  // right, not because they manage money. These are the exception: a manager
  // soliciting against a board writes at length, publicly, about a holding and
  // why. The N and C suffixes mark non-management and contested solicitations;
  // DFAN14A is additional material filed by a non-management soliciting party.
  // The fifty managers have 282 of these between them.
  'DFAN14A', 'DEFN14A', 'PREN14A', 'DEFC14A', 'PREC14A', 'PRRN14A', 'DFRN14A',
  // The registrant answering the SEC in its own words.
  'CORRESP',
  // Prospectuses and their supplements describe the strategy as sold.
  '485BPOS', '497', '424B3',
]);

/**
 * EDGAR labels the same schedule two ways.
 *
 * The older label is "SC 13D"; filings made through the current system carry
 * "SCHEDULE 13D". Both appear in one filer's history, and knowing only the
 * first left 8,275 filings unclassified across the fifty managers - roughly as
 * many again as were being counted. Every intent number was understated by
 * about half, silently, because the miss looked like an unfamiliar form rather
 * than like a bug.
 */
const INTENT = new Set([
  // Item 4, Purpose of Transaction: what the holder means to do.
  'SC 13D', 'SCHEDULE 13D',
  // The passive counterpart. Its content is the choice to file it.
  'SC 13G', 'SCHEDULE 13G',
  // A tender offer states terms and reasoning.
  'SC TO-T', 'SC 14D9', 'SC TO-I',
]);

/**
 * How a manager voted, rather than whether it could.
 *
 * N-PX is the annual record of every proxy vote cast. The strategy fingerprint
 * already reports voting authority from the 13F, which says only that a
 * manager holds the right; this says what it did with it. Structured records
 * rather than prose, so it is not narrative - but it is not a holdings table
 * either, and filing it under positions would lose the distinction.
 */
const VOTES = new Set(['N-PX', 'N-PX/A']);

const POSITIONS = new Set([
  '13F-HR', '13F-NT', '3', '4', '5', 'N-PORT-P', 'NPORT-P', 'N-Q', 'N-MFP',
  // The request to withhold a 13F information table. Norges Bank files these,
  // and they are the paperwork behind the placeholder filings the collector
  // now recognises rather than storing as a one-position book.
  '13FCONP',
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
  if (VOTES.has(base)) return 'votes';
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
    votes: rows.filter((row) => row.kind === 'votes'),
    positions: rows.filter((row) => row.kind === 'positions'),
    unclassified: rows.filter((row) => row.kind === null),
    total: formTypes.length,
  };
}
