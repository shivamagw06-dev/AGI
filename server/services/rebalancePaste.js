/**
 * Turn a pasted rebalance table into rows.
 *
 * The input is whatever comes off the clipboard when a table is copied out of
 * a PDF or a spreadsheet: tab-separated if it came from Excel, run-together
 * spaces if it came from a PDF, with header text that differs between houses
 * and between quarters. So columns are matched by what the header says rather
 * than by position, and a column that cannot be matched is reported instead of
 * being guessed at.
 *
 * The rule throughout is that an unparseable value becomes null and is
 * reported, never a zero. A flow of zero and a flow that failed to parse look
 * identical downstream, and one of them means "this name does not matter" -
 * which is exactly the conclusion a reader would draw from a table full of
 * silent parse failures.
 */

/**
 * Header text to field. Matched loosely, because the same column is called
 * "Potential Net Passive Flows (US$mn)" in one note and "Est. Net Flow ($mn)"
 * in the next.
 */
const COLUMNS = [
  { field: 'source_ticker', patterns: [/^ticker$/i, /^symbol$/i, /^bbg/i] },
  { field: 'company_name', patterns: [/company/i, /^name$/i] },
  { field: 'sector', patterns: [/sector/i, /industry/i] },
  { field: 'change_type', patterns: [/type of change/i, /^change type$/i, /^action$/i] },
  { field: 'net_passive_flow_usd_mn', patterns: [/passive flow/i, /net flow/i, /^flows?\b.*mn/i] },
  { field: 'source_mkt_cap_usd_mn', patterns: [/mkt ?cap/i, /market cap/i] },
  { field: 'source_advt_usd_mn', patterns: [/advt/i, /adv\b/i, /daily traded/i] },
  { field: 'est_next_earnings', patterns: [/earnings/i] },
  { field: 'ex_dividend_on', patterns: [/ex-?div/i] },
];

/** Columns without which a row cannot be stored or shown. */
export const REQUIRED_FIELDS = Object.freeze(['source_ticker', 'change_type']);

/**
 * A number as research tables write them.
 *
 * Parentheses are negative - that is how every one of these tables marks an
 * outflow, and reading "(22)" as 22 flips a sell into a buy. Commas group
 * thousands. A dash, an empty cell or "n/a" is genuinely absent.
 */
export function parseNumber(raw) {
  const text = String(raw ?? '').trim();
  if (!text || /^(-|–|—|n\/?a|na|nm)$/i.test(text)) return null;

  const negative = /^\(.*\)$/.test(text);
  const digits = text.replace(/[(),\s$₹]/g, '').replace(/%$/, '');
  if (!/^-?\d*\.?\d+$/.test(digits)) return null;

  const value = Number(digits);
  if (!Number.isFinite(value)) return null;
  return negative ? -Math.abs(value) : value;
}

/**
 * The Bloomberg ticker in these tables carries a country code: "MEESHO IS".
 * The exchange symbol is the part before it.
 *
 * This is only ever a candidate. It is resolved against the instrument master
 * before anything is priced, and a miss is surfaced rather than assumed - the
 * cases where the Bloomberg ticker and the NSE symbol differ are exactly the
 * renamed and re-listed names, which are also the ones most likely to be in a
 * rebalance.
 */
export function exchangeSymbol(sourceTicker) {
  const text = String(sourceTicker || '').trim().toUpperCase();
  if (!text) return null;
  return text.replace(/\s+(IS|IN|IB|EQUITY)$/i, '').trim() || null;
}

/** Split a pasted line into cells: tabs if present, otherwise runs of spaces. */
function cells(line) {
  if (line.includes('\t')) return line.split('\t').map((cell) => cell.trim());
  return line.split(/\s{2,}/).map((cell) => cell.trim());
}

/**
 * Which column holds which field.
 *
 * Returns nulls for unmatched positions rather than shifting later columns
 * left, so one unrecognised header cannot silently move every value after it
 * into the wrong field.
 */
export function mapHeader(headerCells) {
  const mapping = (headerCells || []).map((cell) => {
    const text = String(cell || '');
    const hit = COLUMNS.find((column) => column.patterns.some((pattern) => pattern.test(text)));
    return hit ? hit.field : null;
  });
  const matched = new Set(mapping.filter(Boolean));
  return {
    mapping,
    missing: REQUIRED_FIELDS.filter((field) => !matched.has(field)),
    unmatched: (headerCells || []).filter((cell, index) => cell && !mapping[index]),
  };
}

const NUMERIC = new Set(['net_passive_flow_usd_mn', 'source_mkt_cap_usd_mn', 'source_advt_usd_mn']);

/**
 * Parse a pasted block into rows plus the problems found.
 *
 * Rows that cannot be used are returned in `rejected` with a reason rather than
 * dropped. A parser that silently discards eight of twenty-five names produces
 * a table that looks complete and is not, and nothing downstream can tell.
 */
export function parsePaste(text) {
  const lines = String(text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length) return { rows: [], rejected: [], header: null, missing: REQUIRED_FIELDS.slice() };

  const header = mapHeader(cells(lines[0]));
  if (header.missing.length) {
    return { rows: [], rejected: [], header, missing: header.missing };
  }

  const rows = [];
  const rejected = [];
  for (const line of lines.slice(1)) {
    const values = cells(line);
    const row = {};
    header.mapping.forEach((field, index) => {
      if (!field) return;
      const raw = values[index];
      row[field] = NUMERIC.has(field) ? parseNumber(raw) : (String(raw ?? '').trim() || null);
    });

    const absent = REQUIRED_FIELDS.filter((field) => !row[field]);
    if (absent.length) {
      // A section heading inside the table - "Stocks with potential passive
      // inflows..." - lands here, which is correct: it is not a row, and
      // reporting it lets the operator confirm nothing real was lost.
      rejected.push({ line, reason: `missing ${absent.join(', ')}` });
      continue;
    }
    row.exchange_symbol = exchangeSymbol(row.source_ticker);
    rows.push(row);
  }

  return { rows, rejected, header, missing: [] };
}
