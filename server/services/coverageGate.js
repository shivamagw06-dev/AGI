/**
 * Whether a manager's book can be measured.
 *
 * The gate this replaces asked two questions by counting securities: is price
 * coverage above a threshold, and are there any holdings without a ticker. The
 * second was absolute - one unresolved holding withheld the manager entirely.
 *
 * Counting is the wrong unit. It weighs a $200 odd-lot the same as a $70bn
 * position, and a real 13F book always contains something obscure: a small
 * fund, a preferred line, a converted note. Requiring every one of them to
 * resolve is not a target that gets closer with work - across 15,098
 * identifiers, 9,588 have no ticker, and the tail thins without ever ending.
 * The gate could not be passed, which reads from outside as missing data
 * rather than as a rule nobody can satisfy.
 *
 * Value is the unit that matches the claim. A return is a value-weighted
 * quantity, so what matters is the share of the book that can be priced, not
 * the share of line items. A manager 99.9% priced by value can be measured,
 * and the 0.1% belongs in a footnote.
 *
 * Both numbers are still reported. Count coverage says how complete the
 * mapping is; value coverage says whether a return means anything.
 */

/**
 * Coverage for one manager's holdings.
 *
 * `holdings` are that manager's positions as at one report date - the current
 * book, not every position ever held, because that is what a reader is being
 * told about. Each carries a security key, a ticker or null, and a value.
 */
export function coverageFor(holdings, priced) {
  let totalValue = 0;
  let pricedValue = 0;
  let unmappedValue = 0;
  let total = 0;
  let covered = 0;
  let unmapped = 0;

  const seen = new Set();
  for (const row of holdings || []) {
    const key = row?.security_key || row?.cusip;
    if (!key || seen.has(key)) continue;
    seen.add(key);

    const value = Number(row?.value_usd) || 0;
    total += 1;
    totalValue += value;

    const ticker = row?.ticker ? String(row.ticker).toUpperCase() : null;
    if (!ticker) {
      unmapped += 1;
      unmappedValue += value;
      continue;
    }
    if (priced?.has(ticker) || priced?.has(String(key).toUpperCase())) {
      covered += 1;
      pricedValue += value;
    }
  }

  return {
    securities_held: total,
    securities_priced: covered,
    securities_unmapped: unmapped,
    // Kept for transparency about how complete the mapping is. It is not what
    // the gate turns on, because it counts line items rather than money.
    price_coverage: total > 0 ? covered / total : null,
    value_held: totalValue,
    value_priced: pricedValue,
    value_unmapped: unmappedValue,
    // What the gate turns on. A return is value-weighted, so this is the
    // share of the claim that rests on real prices.
    value_coverage: totalValue > 0 ? pricedValue / totalValue : null,
  };
}

/**
 * What stops this manager being evaluated, if anything.
 *
 * An unresolved holding is reported as a disclosure rather than a blocker.
 * It is a fact the reader should have; it is not a reason to withhold a
 * number that rests on the other 99.9% of the book.
 */
export function blockersFor({ periods, coverage }, { minPeriods = 3, minValueCoverage = 0.95 } = {}) {
  const blockers = [];
  if (periods < minPeriods) blockers.push(`only ${periods} filed period(s); ${minPeriods} required`);
  if (!coverage || coverage.securities_held === 0) blockers.push('no holdings recorded');
  else if (coverage.value_coverage === null) blockers.push('holdings carry no reported value');
  else if (coverage.value_coverage < minValueCoverage) {
    blockers.push(`priced value ${(coverage.value_coverage * 100).toFixed(1)}% of the book;`
      + ` ${(minValueCoverage * 100).toFixed(0)}% required`);
  }
  return blockers;
}

/** What the reader should be told even when the manager is evaluable. */
export function disclosuresFor(coverage) {
  const out = [];
  if (!coverage) return out;
  if (coverage.securities_unmapped > 0) {
    const share = coverage.value_held > 0 ? (coverage.value_unmapped / coverage.value_held) * 100 : 0;
    out.push(`${coverage.securities_unmapped} holding(s) have no resolved ticker,`
      + ` ${share.toFixed(2)}% of the book by value`);
  }
  const gap = coverage.value_coverage === null ? 0 : (1 - coverage.value_coverage) * 100;
  if (gap > 0.01) out.push(`${gap.toFixed(2)}% of the book by value has no adjusted price`);
  return out;
}
