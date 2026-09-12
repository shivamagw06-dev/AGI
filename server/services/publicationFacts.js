/**
 * Facts pulled out of a manager's own publication.
 *
 * A 13F shows US-listed long equity at a quarter end and nothing else. A
 * manager's annual report can show what no filing does: cost basis, the
 * percentage of a company owned, and holdings that are not 13F-reportable at
 * all. Berkshire's 2025 report discloses five Japanese trading houses worth
 * $35.4bn against $15.4bn of cost, none of which appears in any 13F because
 * Japanese listings are not reportable.
 *
 * Nothing here reads prose and nothing here guesses. It matches the shape of a
 * disclosed-holdings table - an issuer, a percentage owned, and figures - and
 * returns only rows that match it completely. A line it cannot parse is not a
 * row it half-parses; it is a line it does not return, because a holding with
 * an invented number is worse than a holding nobody recorded.
 *
 * Two things are deliberately not inferred.
 *
 * Scale is read from the document or left null. "$ 6,255" means six thousand
 * dollars or six billion depending on a header line elsewhere on the page, and
 * this codebase has already shipped a thousand-fold value error once. Where no
 * unit declaration precedes a table, the figures are returned as written with
 * `unit: null` and nothing downstream may multiply them.
 *
 * Provenance travels with every fact. Each row carries the line it came from,
 * so a reviewer approves a number against the text that produced it rather
 * than against an assurance that the parse went well.
 */

/** "(Dollars in millions)" and its relatives, as a multiplier name. */
const UNIT = /\(?\s*(?:dollars|amounts|\$)\s+in\s+(thousands|millions|billions)\s*\)?/gi;

/**
 * One row of a disclosed-holdings table.
 *
 * Issuer, then a percentage owned, then three figures - cost, market value and
 * dividends in Berkshire's layout. The issuer is matched non-greedily up to
 * the percentage so that a name carrying its own punctuation survives: "Mitsui
 * & Co., Ltd." and "Moody's Corporation" both parse, and a greedy match would
 * swallow the percentage into the name.
 */
const ROW = /^\s*(\S.*?)\s+(\d{1,3}(?:\.\d+)?)\s*%\s+\$?\s*([\d,]+)\s+\$?\s*([\d,]+)\s+\$?\s*([\d,]+)\s*$/;

const number = (value) => {
  const parsed = Number(String(value || '').replace(/,/g, ''));
  return Number.isFinite(parsed) ? parsed : null;
};

/**
 * Lines that look like a row but are not a holding.
 *
 * A total is the sum of the rows above it and storing it as a sixth holding
 * would double the book. It has no percentage in Berkshire's layout so it does
 * not match ROW anyway - this is the guard for a layout where it does.
 */
const NOT_AN_ISSUER = /^(total|subtotal|aggregate|all other|others?)\b/i;

/** The unit declared closest above a position in the text, or null. */
export function unitBefore(text, index) {
  let found = null;
  for (const match of String(text || '').matchAll(UNIT)) {
    // Compared against where the declaration ends, not where it starts. A
    // declaration beginning at the same offset as the row being asked about
    // has not been passed yet, and treating it as applying would let a unit
    // apply to text above itself.
    if (match.index + match[0].length > index) break;
    found = match[1].toLowerCase();
  }
  return found;
}

/**
 * Disclosed holdings in a pasted publication.
 *
 * Returns one fact per parsed row, each with the line it came from. Rows are
 * not deduplicated: the same issuer appearing in two tables of one report is
 * two disclosures, and collapsing them would hide a restatement.
 */
export function extractDisclosedHoldings(text) {
  const source = String(text || '');
  const facts = [];
  let cursor = 0;
  for (const line of source.split('\n')) {
    const at = source.indexOf(line, cursor);
    cursor = at >= 0 ? at + line.length : cursor;
    const match = ROW.exec(line);
    if (!match) continue;
    const [, issuer, percent, first, second, third] = match;
    if (NOT_AN_ISSUER.test(issuer.trim())) continue;
    // An issuer reduced to punctuation or a bare number is a table artefact,
    // not a company.
    if (!/[A-Za-z]{2}/.test(issuer)) continue;
    facts.push({
      kind: 'disclosed_holding',
      issuer: issuer.trim().replace(/\s+/g, ' '),
      percent_owned: number(percent),
      cost_basis: number(first),
      market_value: number(second),
      dividends: number(third),
      // Read from the document, never assumed. Null means the figures are as
      // written and nothing may scale them.
      unit: unitBefore(source, at >= 0 ? at : 0),
      source_excerpt: line.trim().slice(0, 300),
    });
  }
  return facts;
}

/**
 * A stable identity for a pasted document.
 *
 * Whitespace collapses because the same report pasted twice out of a PDF
 * differs in line wrapping and nothing else, and re-pasting it should be
 * recognised rather than stored again as a second publication.
 */
export function documentDigest(text, hasher) {
  const normalised = String(text || '').replace(/\s+/g, ' ').trim();
  return hasher(normalised);
}
