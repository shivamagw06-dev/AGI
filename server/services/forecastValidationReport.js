import { spearmanRankIc } from './forecastV2Validation.js';

/**
 * How good are the daily probabilistic forecasts?
 *
 * Each forecast states an expected sector-adjusted return and a probability
 * that the return is positive. Directional accuracy alone flatters a model
 * that leans with the market's drift, so this also reports:
 *
 * - Brier skill: the forecast probabilities against always predicting the
 *   observed base rate. Zero or below means the probabilities add nothing.
 * - Calibration: in each probability band, how often the stock actually beat
 *   its sector. A calibrated model's 60% band comes true about 60% of the time.
 * - Rank IC: whether stocks ranked higher by expected return did better than
 *   those ranked lower on the same day, averaged over days with a t-statistic.
 * - Top minus bottom quintile: the same-day return gap between the fifth of
 *   stocks the model liked most and the fifth it liked least.
 *
 * Every figure is research only; none of it is a trading result.
 */

const round = (value, digits = 4) => (value == null || !Number.isFinite(value) ? null : Number(value.toFixed(digits)));
const mean = (values) => (values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null);
const BAND_WIDTH = 0.05;
// Below this many forecast days a rank IC or a quintile gap is anecdote.
const MINIMUM_DAYS = 20;
const MINIMUM_OBSERVATIONS = 500;

function normalize(row) {
  const forecast = row.forecast || {};
  const actual = Number(row.actual_alpha_pct);
  const expected = Number(forecast.expected_alpha_pct);
  const probability = Number(forecast.probability_positive);
  if (![actual, expected, probability].every(Number.isFinite)) return null;
  return {
    symbol: String(forecast.symbol || '').toUpperCase(),
    horizon: forecast.horizon,
    day: String(forecast.forecast_time || '').slice(0, 10),
    actual,
    expected,
    probability,
  };
}

function dailyCrossSections(rows) {
  const days = new Map();
  for (const row of rows) {
    if (!days.has(row.day)) days.set(row.day, []);
    days.get(row.day).push(row);
  }
  const ics = [];
  const spreads = [];
  for (const group of days.values()) {
    if (group.length < 10) continue;
    const ic = spearmanRankIc(group.map((row) => row.expected), group.map((row) => row.actual));
    if (ic != null) ics.push(ic);
    const sorted = [...group].sort((a, b) => a.expected - b.expected);
    const fifth = Math.floor(sorted.length / 5);
    if (fifth >= 2) spreads.push(mean(sorted.slice(-fifth).map((row) => row.actual)) - mean(sorted.slice(0, fifth).map((row) => row.actual)));
  }
  const icMean = mean(ics);
  const icSd = ics.length > 1 ? Math.sqrt(ics.reduce((sum, value) => sum + (value - icMean) ** 2, 0) / (ics.length - 1)) : null;
  return {
    days_with_cross_section: ics.length,
    rank_ic_daily_mean: round(icMean),
    rank_ic_t_stat: icSd ? round(icMean / (icSd / Math.sqrt(ics.length)), 2) : null,
    top_minus_bottom_quintile_pct: round(mean(spreads)),
  };
}

function calibration(rows) {
  const bands = new Map();
  for (const row of rows) {
    const low = Math.floor(row.probability / BAND_WIDTH) * BAND_WIDTH;
    const key = low.toFixed(2);
    if (!bands.has(key)) bands.set(key, []);
    bands.get(key).push(row);
  }
  return [...bands.entries()]
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([low, group]) => ({
      band: `${low}–${(Number(low) + BAND_WIDTH).toFixed(2)}`,
      n: group.length,
      mean_probability: round(mean(group.map((row) => row.probability)), 3),
      observed_rate: round(mean(group.map((row) => (row.actual > 0 ? 1 : 0))), 3),
    }));
}

export function summarizeHorizon(rows, horizon, { crossSection = true } = {}) {
  if (!rows.length) return { horizon, observations: 0, calibrated: false, sample_adequate: false };
  const outcomes = rows.map((row) => (row.actual > 0 ? 1 : 0));
  const baseRate = mean(outcomes);
  const brier = mean(rows.map((row, index) => (row.probability - outcomes[index]) ** 2));
  const reference = mean(outcomes.map((outcome) => (baseRate - outcome) ** 2));
  const directional = rows.filter((row) => row.expected !== 0);
  const days = new Set(rows.map((row) => row.day));
  const sampleAdequate = days.size >= MINIMUM_DAYS && rows.length >= MINIMUM_OBSERVATIONS;
  return {
    horizon,
    observations: rows.length,
    stocks: new Set(rows.map((row) => row.symbol)).size,
    forecast_days: days.size,
    first_forecast_day: [...days].sort()[0],
    last_forecast_day: [...days].sort().at(-1),
    target: 'sector_adjusted_return_pct',
    directional_accuracy: round(100 * mean(directional.map((row) => (Math.sign(row.expected) === Math.sign(row.actual) ? 1 : 0))), 2),
    base_rate_positive_pct: round(100 * baseRate, 2),
    brier_score: round(brier),
    brier_reference: round(reference),
    brier_skill: reference > 0 ? round(1 - brier / reference) : null,
    // reduce, not Math.min(...rows): spreading 100k+ values overflows the stack.
    probability_range: [round(rows.reduce((low, row) => Math.min(low, row.probability), 1), 3), round(rows.reduce((high, row) => Math.max(high, row.probability), 0), 3)],
    calibration: calibration(rows),
    mae: round(mean(rows.map((row) => Math.abs(row.actual - row.expected)))),
    mean_error: round(mean(rows.map((row) => row.actual - row.expected))),
    mean_expected_pct: round(mean(rows.map((row) => row.expected))),
    mean_actual_pct: round(mean(rows.map((row) => row.actual))),
    // Ranking only means something within one horizon.
    ...(crossSection ? {
      rank_ic_pooled: spearmanRankIc(rows.map((row) => row.expected), rows.map((row) => row.actual)),
      ...dailyCrossSections(rows),
    } : {}),
    sample_adequate: sampleAdequate,
    // Kept for existing readers: true only once the sample can support a verdict.
    calibrated: sampleAdequate,
    minimum_for_verdict: { forecast_days: MINIMUM_DAYS, observations: MINIMUM_OBSERVATIONS },
  };
}

export function summarizeForecastValidation(rawRows, { horizon = 'all' } = {}) {
  const rows = rawRows.map(normalize).filter(Boolean);
  if (horizon !== 'all') return summarizeHorizon(rows.filter((row) => row.horizon === horizon), horizon);
  const horizons = [...new Set(rows.map((row) => row.horizon))].sort();
  return {
    ...summarizeHorizon(rows, 'all', { crossSection: false }),
    by_horizon: Object.fromEntries(horizons.map((name) => [name, summarizeHorizon(rows.filter((row) => row.horizon === name), name)])),
  };
}
