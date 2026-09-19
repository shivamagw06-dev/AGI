/**
 * Which part of a filing a page belongs to.
 *
 * Reliance's report states operating cash flow twice. Page 61 says 79,059
 * crore and page 103 says 1,92,113 crore, and both lines read "Net Cash Flow
 * from Operating Activities". One is the standalone company and the other is
 * the group. A search for the label alone finds page 61 first and writes a
 * figure less than half the right size, with a citation that checks out
 * against the document, under a definition that says nothing about scope.
 *
 * So a search has to know which section it is looking in before it looks. The
 * running header carries that - every page of the consolidated statements
 * begins "Consolidated Financial Statements", every page of the standalone
 * ones begins "Standalone Financial Statements" - and so does the column year,
 * which is the other thing a statement page cannot be read without. A
 * two-column statement is this year and last year, and which is which is
 * printed at the top rather than left to the convention that the current year
 * comes first.
 */

/**
 * Markers in the order they are looked for, most specific first.
 *
 * Notes come before statements because a notes page's header names both, and
 * the answer to "which section is this" is the narrower one.
 */
const MARKERS = [
  { marker: 'Notes to the Consolidated Financial Statement', scope: 'consolidated', kind: 'notes' },
  { marker: 'Notes To the Consolidated Financial Statement', scope: 'consolidated', kind: 'notes' },
  { marker: 'Notes to the Standalone Financial Statement', scope: 'standalone', kind: 'notes' },
  { marker: 'Notes To the Standalone Financial Statement', scope: 'standalone', kind: 'notes' },
  { marker: 'Consolidated Financial Statements', scope: 'consolidated', kind: 'statements' },
  { marker: 'Standalone Financial Statements', scope: 'standalone', kind: 'statements' },
  { marker: 'Management Discussion and Analysis', scope: null, kind: 'mda' },
  { marker: 'Corporate Governance Report', scope: null, kind: 'governance' },
  { marker: 'Business Responsibility', scope: null, kind: 'brsr' },
  { marker: "Board's Report", scope: null, kind: 'board_report' },
];

/**
 * How much of a page counts as its header.
 *
 * Far enough in to clear the publisher's name and the page numbers, and not so
 * far that a cross-reference in the body is mistaken for the section the page
 * is in. A mention of the consolidated statements inside a standalone note is
 * a reference, not a location.
 */
export const HEADER = 200;

/** The section a page belongs to, read from its running header. */
export function sectionOf(page, { header = HEADER } = {}) {
  const top = String(page ?? '').replace(/\s+/g, ' ').slice(0, header);
  let found = null;
  for (const entry of MARKERS) {
    const at = top.indexOf(entry.marker);
    if (at === -1) continue;
    // The earliest marker wins, so a header naming two sections resolves to
    // the one it leads with rather than to whichever was checked last.
    if (!found || at < found.at) found = { ...entry, at };
  }
  return found ? { scope: found.scope, kind: found.kind } : { scope: null, kind: null };
}

/**
 * What a statement page's column header declares.
 *
 * Two formats, because one filing uses both. The cash flow statement heads its
 * columns "2025-26  2024-25" and the balance sheet heads them "Notes  As at
 * 31st March, 2026  As at 31st March, 2025" - three columns, the first of
 * which is a note reference and not a figure. A reader that knows only the
 * first format finds one year on the balance sheet, counts three cells against
 * it, and skips every row on the page.
 *
 * The running title carries a year too - "Integrated Annual Report 2025-26" -
 * and counting it would add a column that does not exist, so it is removed
 * before anything is read.
 */
export function columnPlan(page, { header = HEADER } = {}) {
  const top = String(page ?? '').replace(/\s+/g, ' ').slice(0, header)
    .replace(/(?:Integrated\s+)?Annual\s+Report\s+\d{4}\s*-\s*\d{2}/gi, ' ');
  // "As at ... 2026" is a balance sheet date; "2025-26" is a period. A page
  // uses one or the other.
  const dated = [...top.matchAll(/As\s+at\b[^,]{0,30},?\s*(\d{4})/gi)].map((found) => Number(found[1]));
  const fiscal = [...top.matchAll(/(\d{4})\s*-\s*(\d{2})(?!\d)/g)].map((found) => Number(found[1]) + 1);
  const years = (dated.length ? dated : fiscal).filter((year, at, all) => all.indexOf(year) === at);
  // A note column sits before the figures and holds a reference, so a row has
  // one more cell than it has years.
  const notes = /\bNotes?\b\s*(?:As\s+at|\d{4})/i.test(top);
  return { years, notes, cells: years.length + (notes ? 1 : 0) };
}

/**
 * The fiscal years a statement page declares for its columns.
 *
 * In the order printed, because that is the order the figures are in. A
 * statement that prints last year first is unusual and entirely legal, and
 * assuming otherwise puts every figure a year out.
 */
export function columnYears(page, options) {
  return columnPlan(page, options).years;
}

const MONTHS = {
  january: 1, february: 2, march: 3, april: 4, may: 5, june: 6, july: 7,
  august: 8, september: 9, october: 10, november: 11, december: 12,
};
const pad = (value) => String(value).padStart(2, '0');

/**
 * The balance sheet dates a page's header states, as ISO dates.
 *
 * Both orders, because both are common: "As at 31st March, 2026" and "As of
 * December 31, 2025". A header that states a year without a day and month -
 * "2025-26" - gives no date here, and is not given one by assumption.
 */
export function statedDates(page, { header = HEADER * 2 } = {}) {
  const top = String(page ?? '').replace(/\s+/g, ' ').slice(0, header);
  const dates = [];
  const dayFirst = /As\s+(?:at|of)\s+(\d{1,2})\s*(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})/gi;
  const monthFirst = /As\s+(?:at|of)\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})/gi;
  for (const found of top.matchAll(dayFirst)) {
    const month = MONTHS[found[2].toLowerCase()];
    if (month) dates.push(`${found[3]}-${pad(month)}-${pad(found[1])}`);
  }
  for (const found of top.matchAll(monthFirst)) {
    const month = MONTHS[found[1].toLowerCase()];
    if (month) dates.push(`${found[3]}-${pad(month)}-${pad(found[2])}`);
  }
  return [...new Set(dates)];
}

/**
 * The periods a filing reports, read from its own statements.
 *
 * A reader uploading an annual report should not have to say which year it
 * covers - the document says, on every statement page. Without this a first
 * upload, with nothing yet stored, resolved no periods at all and answered
 * nothing, while reporting every figure as something nobody knew how to find.
 *
 * The year comes from the column headers and the day and month from a balance
 * sheet date. A filing whose statements state years but no date gives years
 * and no periods, with the reason: a fiscal year of 2025-26 ends on 31 March
 * in India and on other dates elsewhere, and choosing one would put every
 * figure under a period the filing never named.
 */
export function documentPeriods(pages, { accounting_scope = 'consolidated' } = {}) {
  const sections = mapSections(pages);
  const statements = sections.filter((entry) => entry.kind === 'statements'
    && (!accounting_scope || entry.scope === accounting_scope));
  const years = new Set();
  const dates = new Set();
  for (const entry of statements) {
    for (const year of entry.years) years.add(year);
    for (const date of statedDates(pages[entry.page - 1])) dates.add(date);
  }
  // An opening balance is the day after the previous year-end. Reliance's
  // statement of changes in equity opens "Balance as at 1st April, 2024" and
  // closes "Balance as at 31st March, 2025", and reading the first as a period
  // end gives the filing two year-ends and an extra year it does not report.
  // So a month-day falling exactly one day after another candidate is dropped.
  const dayAfter = (monthDay) => {
    const [month, day] = monthDay.split('-').map(Number);
    const next = new Date(Date.UTC(2001, month - 1, day + 1));
    return `${pad(next.getUTCMonth() + 1)}-${pad(next.getUTCDate())}`;
  };
  const candidates = [...new Set([...dates].map((date) => date.slice(5)))];
  const openings = new Set(candidates.map(dayAfter).filter((next) => candidates.includes(next)));
  const closing = candidates.filter((monthDay) => !openings.has(monthDay));

  if (!dates.size) {
    return {
      period_ends: [], month_end: null, years: [...years].sort((a, b) => b - a),
      reason: years.size
        ? 'the statements state years but no balance sheet date, so the period ends are not known'
        : 'no statement page states which years it covers',
    };
  }
  if (closing.length !== 1) {
    return {
      period_ends: [], month_end: null, years: [...years].sort((a, b) => b - a),
      reason: `the statements give more than one year-end date (${closing.join(', ')})`,
    };
  }
  const [monthEnd] = closing;
  // The dates the filing states, not every year paired with the month: a year
  // that appears only as an opening balance is not a period it reports.
  const periodEnds = [...dates].filter((date) => date.slice(5) === monthEnd)
    .sort((a, b) => b.localeCompare(a));
  return {
    period_ends: periodEnds,
    month_end: monthEnd,
    years: periodEnds.map((date) => Number(date.slice(0, 4))),
    reason: null,
  };
}

/** Every page of a filing, with the section it belongs to. */
export function mapSections(pages) {
  return (pages || []).map((page, at) => ({
    page: at + 1,
    ...sectionOf(page),
    ...columnPlan(page),
  }));
}

/** The pages a search should look at for a given scope and kind. */
export function pagesFor(sections, { accounting_scope = null, kind = null } = {}) {
  return (sections || []).filter((entry) => (!accounting_scope || entry.scope === accounting_scope)
    && (!kind || entry.kind === kind));
}
