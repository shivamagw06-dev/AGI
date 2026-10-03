/**
 * Whether a chain of period returns can be reported as one number.
 *
 * Coverage per period is already measured by value, and excluded positions are
 * already treated as holding flat rather than the priced ones being scaled up.
 * What was wrong is how the periods were judged together.
 *
 * The gate averaged them. A compounded return multiplies every period, so a
 * single quarter at twenty per cent coverage - four fifths of the book assumed
 * flat - carries its error into the product and every period after it. Against
 * eleven good quarters that average clears a seventy per cent floor
 * comfortably, and the resulting figure is presented as a measurement of the
 * whole book.
 *
 * The worst period governs what the chain is worth, so the worst period is
 * what the gate reads. The average is still reported, because it says
 * something different and useful: how complete the run was overall.
 *
 * The floor matches the screener's. Both answer "can this manager's
 * performance be stated", and two surfaces answering it at different bars is
 * how one of them ends up wrong.
 */

/** Coverage across a run: the worst period, the mean, and which period was worst. */
export function coverageProfile(periods) {
  // Number(null) is 0 and 0 is finite, so a coerce-first filter counts a
  // period with no coverage figure as a period with zero coverage - blocking
  // a run for something never measured rather than badly measured.
  const rows = (periods || []).filter((row) => {
    const value = row?.price_coverage;
    return value !== null && value !== undefined && Number.isFinite(Number(value));
  });
  if (!rows.length) return { worst: 0, average: 0, worstPeriod: null, periods: 0 };

  let worst = Infinity;
  let worstPeriod = null;
  let sum = 0;
  for (const row of rows) {
    const value = Number(row.price_coverage);
    sum += value;
    if (value < worst) { worst = value; worstPeriod = row.report_date || row.entry_date || null; }
  }
  return { worst, average: sum / rows.length, worstPeriod, periods: rows.length };
}

/**
 * Why a run cannot be reported, or null if it can.
 *
 * Every condition is checked rather than the first failure returned, because
 * an operator fixing one only to meet the next learns the state one round trip
 * at a time.
 */
export function backtestBlockers(profile, { periods, benchmarkComplete, skipped = [] }, { minPeriods = 3, minCoverage = 0.95 } = {}) {
  const blockers = [];
  if (!periods) blockers.push('No period could be priced.');
  else if (periods < minPeriods) blockers.push(`Only ${periods} priced period(s); at least ${minPeriods} are required.`);

  if (profile.periods && profile.worst < minCoverage) {
    // Named by its date. "Coverage was low somewhere" is not something an
    // operator can act on.
    blockers.push(`Price coverage in ${profile.worstPeriod || 'one period'} was `
      + `${(profile.worst * 100).toFixed(1)}% of the book by value, below the `
      + `${(minCoverage * 100).toFixed(0)}% floor every period must clear; `
      + `a compounded return carries that period's gap through every one after it.`);
  }
  if (!benchmarkComplete) {
    blockers.push('The benchmark is missing prices in at least one period, so excess return cannot be stated.');
  }
  if (skipped.length) blockers.push(`${skipped.length} period(s) could not be evaluated.`);
  return blockers;
}
