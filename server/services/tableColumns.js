/**
 * Which column a number in a table row came from.
 *
 * A ten-year table flattens to one long line, and citing that line as the
 * source of a figure proves only that the figure is somewhere in it. Reliance's
 * revenue row carries eleven numbers; a fact claiming 7,88,743 is FY 2021-22
 * passes a sentence check whether or not it is, because the digits are in the
 * line either way. The year would be asserted rather than read.
 *
 * So the row is aligned against its header and the figure is taken by
 * position. A row whose count of cells does not match the header's count of
 * columns is refused rather than aligned approximately - an off-by-one in a
 * ten-year table puts every figure under the wrong year, and the result looks
 * entirely reasonable.
 */

/**
 * The columns a header row declares.
 *
 * Reliance's reads "US$ Million FY 2025-26 FY 2024-25 ... FY 2016-17", so the
 * first column is a different currency and a different unit from the ten that
 * follow it. It is returned like any other; deciding to skip it is the
 * caller's, and a caller that does not notice would produce dollar figures
 * labelled as crore.
 */
export function headerColumns(header) {
  const cleaned = String(header ?? '');
  const years = [...cleaned.matchAll(/FY\s*(\d{4})\s*-\s*(\d{2,4})/g)].map((found) => ({
    label: `FY ${found[1]}-${found[2]}`,
    // A fiscal year written FY 2025-26 ends in the later of the two years.
    ends_in: Number(found[1]) + 1,
    at: found.index,
  }));
  if (!years.length) return [];
  const before = cleaned.slice(0, years[0].at).trim();
  return [
    ...(before ? [{ label: before, ends_in: null, at: 0 }] : []),
    ...years,
  ].map(({ label, ends_in }, position) => ({ position, label, ends_in }));
}

/**
 * A cell is a number, possibly in accounting parentheses, or a dash. A dash
 * has to match: it holds a column, and a row whose dashes went unmatched would
 * come back one cell short for every year the issuer reported nothing. It
 * needs no special case after that - it parses to NaN and so to null.
 */
// A cell must contain a digit. `[\d,]+` matches a lone comma, which turned the
// comma in "Earnings Before Depreciation, Finance Cost and Tax Expenses" into a
// cell and split one row into two.
const CELL = /\(?-?\d[\d,]*(?:\.\d+)?\)?|[-\u2013\u2014]/g;

const valueOf = (text) => {
  const trimmed = text.trim();
  const negative = /^\(.*\)$/.test(trimmed);
  const value = Number(trimmed.replace(/[(),]/g, ''));
  return Number.isFinite(value) ? (negative ? -value : value) : null;
};

/**
 * Runs of cells, separated by the words between them.
 *
 * A flattened table is rows of figures with labels in between, so a run of
 * figures uninterrupted by words is one row's worth. Two runs in one slice
 * means the slice holds two rows.
 */
function cellRuns(text) {
  const runs = [];
  for (const match of text.matchAll(CELL)) {
    const held = runs[runs.length - 1];
    if (held && !/[A-Za-z]{2,}/.test(text.slice(held.end, match.index))) {
      held.cells.push(match[0]);
      held.end = match.index + match[0].length;
      continue;
    }
    runs.push({ start: match.index, end: match.index + match[0].length, cells: [match[0]] });
  }
  return runs;
}

/**
 * The label a row starts with and the cells that follow it.
 *
 * A slice holding two runs is refused rather than resolved. The first version
 * of this took the last run, which is how a slice running from "Depreciation
 * and Amortisation" through the next row returned the exceptional items
 * figures - eleven cells against eleven columns, aligned perfectly, and every
 * number a year and a line item away from what it claimed to be. Refusing is
 * stricter than it needs to be for a label containing a number, and a refusal
 * is visible where wrong data is not.
 */
export function rowCells(row) {
  const text = String(row ?? '');
  const runs = cellRuns(text);
  if (!runs.length) return { label: text.trim(), cells: [], problem: null };
  if (runs.length > 1) {
    return { label: text.slice(0, runs[0].start).trim(), cells: [],
      problem: `the text holds ${runs.length} runs of figures, so more than one row` };
  }
  return {
    label: text.slice(0, runs[0].start).trim(),
    cells: runs[0].cells.map(valueOf),
    problem: null,
  };
}

/**
 * A region of a flattened table, split into its rows.
 *
 * Each row runs from the end of the previous row's figures to the end of its
 * own, so the label between them belongs to the row it introduces. Callers
 * that guess at row boundaries by looking for the labels they care about skip
 * the rows they do not, and take the following row's figures.
 */
export function splitRows(region) {
  const text = String(region ?? '');
  const rows = [];
  let from = 0;
  for (const run of cellRuns(text)) {
    rows.push({
      label: text.slice(from, run.start).trim(),
      text: text.slice(from, run.end).trim(),
      cells: run.cells.map(valueOf),
    });
    from = run.end;
  }
  return rows;
}

/**
 * A row read against its header, or the reason it cannot be.
 *
 * Refusing a mismatched row is the point. Aligning ten figures against eleven
 * columns shifts every one of them by a year and produces a table that reads
 * perfectly.
 */
export function alignRow(header, row) {
  const columns = headerColumns(header);
  if (!columns.length) return { label: null, cells: [], problem: 'the header declares no columns' };
  const { label, cells, problem } = rowCells(row);
  if (problem) return { label, cells: [], problem };
  if (cells.length !== columns.length) {
    return { label, cells: [],
      problem: `the row has ${cells.length} cells and the header has ${columns.length} columns` };
  }
  return {
    label,
    cells: columns.map((column, at) => ({ ...column, value: cells[at] })),
    problem: null,
  };
}

/** The cell for one fiscal year, by the year its period ends in. */
export function cellEndingIn(aligned, year) {
  return (aligned?.cells || []).find((cell) => cell.ends_in === year) || null;
}
