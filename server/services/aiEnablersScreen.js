/**
 * Stages 2 and 3 of the screen: size and tradability, then investment
 * intensity.
 *
 * Both stages are relative to the universe being screened, not to constants
 * invented here. A turnover floor of "one crore a day" is a number somebody
 * made up; "above the median of the universe we screened, and here is the
 * median" is a number somebody can argue with. Absolute floors are supported
 * because an index needs a tradability minimum that does not move every
 * month, but they are inputs, printed with the result.
 *
 * Nothing in this file invents an input. A company missing the data a stage
 * needs is `unscreened` for that stage - never a silent pass and never a
 * silent fail, both of which change the universe without anyone deciding to.
 */

// Number(null) is 0 and Number('') is 0, so a plain Number() here would read
// "we have no figure" as "the figure is zero" - the exact collapse this code
// exists to prevent. An absent key gives NaN and behaves; an explicit null,
// which is what JSON from a database actually carries, does not.
const numeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export function median(values) {
  const sorted = values.filter((one) => Number.isFinite(one)).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

/** Percentile by nearest rank, for reporting a distribution rather than a point. */
export function percentile(values, p) {
  const sorted = values.filter((one) => Number.isFinite(one)).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const rank = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[rank];
}

/**
 * The distribution of an input across the universe.
 *
 * Reported before any threshold is chosen, because a cut-off picked without
 * seeing the spread is a cut-off nobody can defend - including the person who
 * picked it.
 */
export function distribution(rows, pick) {
  const values = rows.map(pick).map(numeric).filter((one) => one !== null);
  return {
    count: values.length,
    missing: rows.length - values.length,
    min: values.length ? Math.min(...values) : null,
    p25: percentile(values, 25),
    median: median(values),
    p75: percentile(values, 75),
    max: values.length ? Math.max(...values) : null,
  };
}

/**
 * Stage 2 - size and tradability.
 *
 * `freeFloatMarketCap` and `medianDailyTurnover` are both required. A member
 * missing either is unscreened: it may be a perfectly good company, and we do
 * not know, which is a different state from failing.
 */
export function stageTwo(members, {
  minFreeFloatMarketCap = null,
  minMedianDailyTurnover = null,
  relativeTo = 'absolute',           // 'absolute' | 'median'
} = {}) {
  const rows = members.map((member) => ({
    symbol: member.symbol,
    freeFloatMarketCap: numeric(member.freeFloatMarketCap),
    medianDailyTurnover: numeric(member.medianDailyTurnover),
  }));

  const capDistribution = distribution(rows, (one) => one.freeFloatMarketCap);
  const turnoverDistribution = distribution(rows, (one) => one.medianDailyTurnover);

  const capFloor = relativeTo === 'median' ? capDistribution.median : minFreeFloatMarketCap;
  const turnoverFloor = relativeTo === 'median' ? turnoverDistribution.median : minMedianDailyTurnover;

  const passed = [];
  const failed = [];
  const unscreened = [];
  for (const row of rows) {
    if (row.freeFloatMarketCap === null || row.medianDailyTurnover === null) {
      unscreened.push({
        symbol: row.symbol,
        reason: row.freeFloatMarketCap === null ? 'NO_FREE_FLOAT_MARKET_CAP' : 'NO_TURNOVER_HISTORY',
      });
      continue;
    }
    const reasons = [];
    if (capFloor !== null && row.freeFloatMarketCap < capFloor) reasons.push('BELOW_SIZE_FLOOR');
    if (turnoverFloor !== null && row.medianDailyTurnover < turnoverFloor) reasons.push('BELOW_TURNOVER_FLOOR');
    if (reasons.length) failed.push({ ...row, reasons });
    else passed.push(row);
  }

  return {
    stage: 2,
    applied: capFloor !== null || turnoverFloor !== null,
    thresholds: { freeFloatMarketCap: capFloor, medianDailyTurnover: turnoverFloor, relativeTo },
    distributions: { freeFloatMarketCap: capDistribution, medianDailyTurnover: turnoverDistribution },
    passed, failed, unscreened,
  };
}

/**
 * Stage 3 - investment intensity.
 *
 * Any one of four tests admits, because a company can be building through
 * capex, through R&D, or through revenue growth that capex has already paid
 * for, and requiring all four would screen for a single financing style
 * rather than for building.
 *
 * Thresholds are the universe's own medians by default. Every input is
 * expected to come from the fact store, so a figure that reaches here is one
 * that has already been made to cite itself.
 */
export const INTENSITY_TESTS = Object.freeze([
  { key: 'revenueCagr3y', label: 'three-year revenue CAGR' },
  { key: 'capexGrowth', label: 'capex growth' },
  { key: 'capexToSales', label: 'capex to sales' },
  { key: 'rndToSales', label: 'R&D to sales' },
]);

export function stageThree(members, { thresholds = null } = {}) {
  const rows = members.map((member) => {
    const row = { symbol: member.symbol };
    for (const test of INTENSITY_TESTS) row[test.key] = numeric(member[test.key]);
    return row;
  });

  const distributions = {};
  const cutoffs = {};
  for (const test of INTENSITY_TESTS) {
    distributions[test.key] = distribution(rows, (one) => one[test.key]);
    cutoffs[test.key] = thresholds?.[test.key] ?? distributions[test.key].median;
  }

  const passed = [];
  const failed = [];
  const unscreened = [];
  for (const row of rows) {
    const available = INTENSITY_TESTS.filter((test) => row[test.key] !== null);
    if (!available.length) {
      unscreened.push({ symbol: row.symbol, reason: 'NO_INTENSITY_INPUTS' });
      continue;
    }
    const met = available.filter((test) => {
      const cutoff = cutoffs[test.key];
      return cutoff !== null && row[test.key] >= cutoff;
    });
    if (met.length) passed.push({ ...row, met: met.map((test) => test.key) });
    else failed.push({ ...row, tested: available.map((test) => test.key) });
  }

  return {
    stage: 3,
    tests: INTENSITY_TESTS.map((one) => one.key),
    thresholds: cutoffs,
    distributions,
    passed, failed, unscreened,
  };
}

/**
 * Both stages, in order, with the count at each step.
 *
 * Stage 3 screens only what Stage 2 passed. Unscreened members do not
 * advance: not knowing whether something is tradable is not the same as
 * knowing that it is, and carrying it forward would let a gap in the data
 * become a member of the index.
 */
export function runScreen(members, { stage2 = {}, stage3 = {} } = {}) {
  const two = stageTwo(members, stage2);
  const bySymbol = new Map(members.map((one) => [one.symbol, one]));
  const advanced = two.passed.map((one) => bySymbol.get(one.symbol)).filter(Boolean);
  const three = stageThree(advanced, stage3);
  return {
    started: members.length,
    stage2: two,
    stage3: three,
    admitted: three.passed.map((one) => one.symbol),
    funnel: [
      { stage: 'universe', count: members.length },
      { stage: 'stage2_size_tradability', count: two.passed.length, failed: two.failed.length, unscreened: two.unscreened.length },
      { stage: 'stage3_investment_intensity', count: three.passed.length, failed: three.failed.length, unscreened: three.unscreened.length },
    ],
  };
}
