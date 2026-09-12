/**
 * What a manager did this quarter, and how long it has held what it holds.
 *
 * These are the standard descriptive statistics of a disclosed portfolio -
 * concentration, turnover, holding period, the count of positions opened and
 * closed. They are arithmetic on filings already stored, needing no prices and
 * no vendor, and every one states its own formula so a reader can check it.
 *
 * Holding period is the figure that was impossible before: it counts the
 * consecutive quarters a position has appeared, so it is bounded by how much
 * history has been collected. Twelve quarters of filings cannot show a
 * position held for thirty-six, and would report the truncation as the answer.
 * Every holding-period figure here therefore carries how many quarters it had
 * to work with, and says when it is a floor rather than a measurement.
 */

const n = (value) => (Number.isFinite(Number(value)) ? Number(value) : 0);

/** Positions opened, added to, trimmed and closed this quarter. */
export function activityCounts(changes) {
  const counts = { new: 0, increased: 0, reduced: 0, exited: 0 };
  for (const row of changes || []) {
    if (Object.hasOwn(counts, row?.change_type)) counts[row.change_type] += 1;
  }
  return counts;
}

/**
 * Share of the book in its ten largest positions.
 *
 * Weight is recomputed from value rather than trusting a stored weight, so a
 * filing whose weights were written under a different value scale cannot
 * report a concentration that its own numbers contradict.
 */
export function topWeight(holdings, count = 10) {
  const values = (holdings || [])
    .filter((row) => !row?.put_call)
    .map((row) => n(row.value_usd))
    .sort((a, b) => b - a);
  const total = values.reduce((sum, value) => sum + value, 0);
  if (!total) return null;
  return (values.slice(0, count).reduce((sum, value) => sum + value, 0) / total) * 100;
}

/**
 * Turnover, both ways it is normally stated.
 *
 * `byCount` is positions opened plus positions closed, over positions held -
 * how much of the list changed. `byValue` is the smaller of what was bought
 * and what was sold, over the book - how much of the money moved. They answer
 * different questions and a manager can score high on one and low on the
 * other, so both are reported rather than one being chosen.
 */
export function turnover(changes, holdings) {
  const counts = activityCounts(changes);
  const positions = (holdings || []).filter((row) => !row?.put_call).length;
  const bought = (changes || [])
    .filter((row) => row?.change_type === 'new')
    .reduce((sum, row) => sum + Math.abs(n(row.value_change ?? row.current_value)), 0);
  const sold = (changes || [])
    .filter((row) => row?.change_type === 'exited')
    .reduce((sum, row) => sum + Math.abs(n(row.value_change ?? row.previous_value)), 0);
  const total = (holdings || []).reduce((sum, row) => sum + n(row.value_usd), 0);
  return {
    byCount: positions ? ((counts.new + counts.exited) / positions) * 100 : null,
    byValue: total ? (Math.min(bought, sold) / total) * 100 : null,
  };
}

/**
 * How many consecutive quarters each currently held position has been held.
 *
 * Counted back from the current period through the ordered list of report
 * dates, stopping at the first quarter the position is absent. A gap ends the
 * run: a position sold and later rebought has been held since the rebuy, not
 * since before the sale.
 */
export function holdingTenure(periods, holdingsByPeriod, current) {
  const ordered = [...new Set(periods || [])].sort().reverse();
  const currentIndex = ordered.indexOf(current);
  if (currentIndex < 0) return new Map();

  const tenure = new Map();
  for (const key of holdingsByPeriod.get(current) || []) {
    let quarters = 0;
    for (let i = currentIndex; i < ordered.length; i += 1) {
      if (!(holdingsByPeriod.get(ordered[i]) || new Set()).has(key)) break;
      quarters += 1;
    }
    tenure.set(key, quarters);
  }
  return tenure;
}

/**
 * Average holding period, and whether the history could measure it.
 *
 * `truncated` says the answer is a floor: at least one position has been held
 * for every quarter collected, so the real figure is larger and unknowable
 * from what is stored. Reporting the floor as a measurement is how a manager
 * that has held a position for thirty quarters is described as holding it for
 * the twelve that happen to have been fetched.
 */
export function averageTenure(tenure, keys, quartersAvailable) {
  const values = [...keys].map((key) => tenure.get(key)).filter((value) => Number.isFinite(value));
  if (!values.length) return { quarters: null, truncated: false, sample: 0 };
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  return {
    quarters: mean,
    truncated: values.some((value) => value >= quartersAvailable),
    sample: values.length,
  };
}

/** The largest positions by value, as security keys. */
export function topKeys(holdings, count, keyOf) {
  return (holdings || [])
    .filter((row) => !row?.put_call)
    .slice()
    .sort((a, b) => n(b.value_usd) - n(a.value_usd))
    .slice(0, count)
    .map(keyOf)
    .filter(Boolean);
}

/** Quarter-over-quarter change in disclosed value. */
export function valueFlow(currentTotal, priorTotal) {
  const current = n(currentTotal);
  const prior = n(priorTotal);
  if (!prior) return { current, prior, changePct: null };
  return { current, prior, changePct: ((current - prior) / prior) * 100 };
}
