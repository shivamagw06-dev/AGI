/**
 * Turning a quarterly 13F list PDF into rows.
 *
 * The list is published as PDF and nothing else - there is no txt, csv or xlsx
 * variant, each of which returns 404 on both of the paths the SEC serves these
 * from. So the columns have to be recovered from the page.
 *
 * Recovering them from *text order* is what a naive extractor does, and it is
 * fragile: the issuer name and the description are adjacent strings with no
 * delimiter between them, so "AERIES TECHNOLOGY INC" and "CL A ORD SHS" arrive
 * as one run of words and any split is a guess. The page itself knows better.
 * Every glyph carries an x coordinate and the columns are at fixed positions:
 *
 *    73  issuer number        150  options marker
 *   116  issue number         167  issuer name
 *   135  check digit          350  issuer description
 *                             466  status
 *
 * Reading the bands directly makes the split exact rather than inferred, and
 * makes the parse independent of how any given extractor happens to order or
 * join the text runs.
 */

/**
 * Column boundaries are read from the page, not hardcoded.
 *
 * Fixed x bands work until they do not. Measured across 2019Q1-2026Q2 the
 * layout drifts: in 2025Q4 every column moves two or three units left, which
 * puts the options asterisk at x=147 where a band starting at 148 expects the
 * check digit. The check digit becomes "8*", the row fails its shape test and
 * is dropped - and because only optioned securities carry an asterisk, exactly
 * the largest and most liquid names disappear. That quarter parsed 2,498
 * equities where its neighbours parsed about 7,000, with no error raised.
 *
 * The page already states where its columns are. The header line
 *
 *   CUSIP NO    ISSUER NAME    ISSUER DESCRIPTION    STATUS
 *
 * is reprinted on every page at the column positions, so reading it makes the
 * parse self-calibrating and immune to the drift. Where a page has no header -
 * the cover and notice pages - there is nothing to extract anyway.
 */
const HEADERS = [
  { field: 'name', match: /^ISSUER\s*NAME$/i },
  { field: 'description', match: /^ISSUER\s*DESCRIPTION$/i },
  { field: 'status', match: /^STATUS$/i },
];

/**
 * Learn a page's column boundaries from its header row.
 *
 * Returns null when the page carries no header, which is the signal to skip it
 * rather than to guess.
 */
export function columnsFromHeader(items) {
  const found = {};
  for (const item of items || []) {
    const text = String(item?.str || '').trim();
    if (!text) continue;
    for (const header of HEADERS) {
      if (header.match.test(text) && found[header.field] === undefined) {
        found[header.field] = Math.round(item.transform[4]);
      }
    }
  }
  if (found.name === undefined || found.description === undefined) return null;
  return {
    // A few units of slack on each side, because the header label and the
    // values beneath it are not always flush to the same pixel.
    name: found.name - 6,
    description: found.description - 6,
    status: (found.status ?? found.description + 110) - 6,
  };
}

function bandFor(x, columns) {
  if (x >= columns.status) return 'status';
  if (x >= columns.description) return 'description';
  if (x >= columns.name) return 'name';
  // Everything left of the name column is the CUSIP and its options marker.
  // They are split by shape rather than by position, because the asterisk sits
  // only a few units from the check digit and that gap is not stable.
  return 'left';
}

/**
 * Group positioned glyph runs into rows, then rows into fields.
 *
 * `items` is the shape pdf.js returns from getTextContent(): each carries a
 * transform whose fifth and sixth entries are x and y. Rows are keyed on
 * rounded y, because every glyph on a line shares a baseline.
 */
export function rowsFromTextItems(items) {
  const columns = columnsFromHeader(items);
  if (!columns) return [];
  const byLine = new Map();
  for (const item of items || []) {
    const t = item?.transform;
    if (!Array.isArray(t) || !item.str) continue;
    const y = Math.round(t[5]);
    if (!byLine.has(y)) byLine.set(y, []);
    byLine.get(y).push({ x: Math.round(t[4]), text: item.str });
  }

  const rows = [];
  // Descending y, because PDF user space puts the origin at the bottom of the
  // page and reading order runs down it.
  for (const y of [...byLine.keys()].sort((a, b) => b - a)) {
    const parts = { left: '', name: '', description: '', status: '' };
    for (const glyph of byLine.get(y).sort((a, b) => a.x - b.x)) {
      parts[bandFor(glyph.x, columns)] += glyph.text;
    }
    // The left column holds the CUSIP as three fields and, when present, the
    // options marker. Some quarters emit those as separate text runs and some
    // as one joined run - 2025Q2 gives "G0509J 11 5" in a single run, which a
    // per-run split drops entirely - so it is tokenised rather than positioned.
    const tokens = parts.left.replace(/\*/g, ' * ').trim().split(/\s+/).filter(Boolean);
    const options = tokens.includes('*');
    const parked = tokens.filter((token) => token !== '*');
    // The left column arrives in three shapes across the archive: three runs
    // with spacing runs between them, one joined run ("G0509J 11 5" in 2025Q2),
    // or three runs butted together with no space at all. Splitting on
    // whitespace handles the first two; a nine-character single token is the
    // third, and is cut at the CUSIP's own 6-2-1 boundaries.
    let [issuer = '', issue = '', check = ''] = parked;
    if (parked.length === 1 && parked[0].length === 9) {
      [issuer, issue, check] = [parked[0].slice(0, 6), parked[0].slice(6, 8), parked[0].slice(8)];
    }
    rows.push({
      issuer,
      issue,
      check,
      options: options ? '*' : '',
      name: parts.name.trim(),
      description: parts.description.trim(),
      status: parts.status.trim(),
    });
  }
  return rows;
}

const ISSUER = /^[0-9A-Z]{6}$/;
const ISSUE = /^[0-9A-Z]{2}$/;
const CHECK = /^[0-9]$/;

/**
 * Keep the rows that are securities.
 *
 * Page furniture - run date, page number, the repeated column header - lands in
 * these bands too and has to be discarded. A row is a security when its first
 * three fields have the shape of a CUSIP: six characters, two characters, one
 * digit. Nothing else on the page does.
 */
export function securitiesFromRows(rows, { quarter = null } = {}) {
  const out = [];
  for (const row of rows || []) {
    if (!ISSUER.test(row.issuer) || !ISSUE.test(row.issue) || !CHECK.test(row.check)) continue;
    out.push({
      cusip: row.issuer + row.issue + row.check,
      issuer_number: row.issuer,
      issue_number: row.issue,
      issuer_name: row.name,
      description: row.description,
      has_listed_options: row.options === '*',
      status: row.status === 'ADDED' || row.status === 'DELETED' ? row.status : '',
      quarter,
    });
  }
  return out;
}
