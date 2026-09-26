/**
 * Collapsing per-quarter list rows into one row per identifier.
 *
 * Kept out of the loader script because a script runs on import: anything that
 * wants to test this would otherwise have to download thirty PDFs first.
 */
/**
 * Collapse per-quarter rows into one row per CUSIP.
 *
 * The class, name and description are taken from the *latest* quarter the
 * identifier appears in, because that is the description the SEC currently
 * stands behind. The quarter window keeps both ends: the last quarter is how a
 * superseded identifier is told apart from one that was never listed.
 */
export function aggregateByCusip(rows) {
  const byCusip = new Map();
  for (const row of rows || []) {
    if (!row?.cusip) continue;
    const existing = byCusip.get(row.cusip);
    if (!existing) {
      byCusip.set(row.cusip, {
        cusip: row.cusip,
        first_quarter: row.quarter,
        last_quarter: row.quarter,
        issuer_name: row.issuer_name,
        description: row.description,
        security_class: row.security_class,
        has_listed_options: Boolean(row.has_listed_options),
        observed_quarters: 1,
      });
      continue;
    }
    existing.observed_quarters += 1;
    if (row.quarter < existing.first_quarter) existing.first_quarter = row.quarter;
    if (row.quarter >= existing.last_quarter) {
      existing.last_quarter = row.quarter;
      existing.issuer_name = row.issuer_name;
      existing.description = row.description;
      existing.security_class = row.security_class;
    }
    // Options are ever-listed rather than currently-listed: an issue that had
    // options in any quarter is one whose 90/95 lines exist in our holdings.
    existing.has_listed_options = existing.has_listed_options || Boolean(row.has_listed_options);
  }
  return [...byCusip.values()];
}

