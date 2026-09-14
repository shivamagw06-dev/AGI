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
