export const VALIDATION_HORIZONS = Object.freeze(['5m', '15m', '30m', '1h', 'close', 'next_day', '5d']);

function finite(value) {
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function average(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function standardDeviation(values) {
  if (values.length < 2) return null;
  const avg = average(values);
  return Math.sqrt(values.reduce((sum, value) => sum + ((value - avg) ** 2), 0) / (values.length - 1));
}

function pearson(left, right) {
  if (left.length < 3 || left.length !== right.length) return null;
  const leftMean = average(left);
  const rightMean = average(right);
  const numerator = left.reduce((sum, value, index) => sum + (value - leftMean) * (right[index] - rightMean), 0);
  const leftScale = Math.sqrt(left.reduce((sum, value) => sum + ((value - leftMean) ** 2), 0));
  const rightScale = Math.sqrt(right.reduce((sum, value) => sum + ((value - rightMean) ** 2), 0));
  return leftScale && rightScale ? numerator / (leftScale * rightScale) : null;
}

function maximumDrawdown(returns) {
  let wealth = 1;
  let peak = 1;
  let drawdown = 0;
  for (const value of returns) {
    wealth *= 1 + value / 100;
    peak = Math.max(peak, wealth);
    drawdown = Math.min(drawdown, ((wealth / peak) - 1) * 100);
  }
  return drawdown;
}

function rounded(value, digits = 4) {
  return value === null || !Number.isFinite(value) ? null : Number(value.toFixed(digits));
}

/**
 * Validate completed signal outcomes for one forecast horizon.
 * Percent returns are expected (0.25 means 25 basis points).
 */
export function evaluateSignalOutcomes(observations, { horizon, minimumSample = 100 } = {}) {
  if (!VALIDATION_HORIZONS.includes(horizon)) throw new Error(`Unsupported validation horizon: ${horizon}.`);
  if (!Array.isArray(observations)) throw new Error('observations must be an array.');
  const rows = observations.map((row, index) => {
    const signalScore = finite(row.signalScore ?? row.signal_score);
    const strategyReturn = finite(row.strategyReturn ?? row.strategy_return);
    const benchmarkReturn = finite(row.benchmarkReturn ?? row.benchmark_return);
    const costBps = finite(row.estimatedCostBps ?? row.estimated_cost_bps) ?? 0;
    const turnover = finite(row.turnover) ?? 0;
    if ([signalScore, strategyReturn, benchmarkReturn].some((value) => value === null) || costBps < 0 || turnover < 0) {
      throw new Error(`Invalid validation observation at index ${index}.`);
    }
    const grossAlpha = strategyReturn - benchmarkReturn;
    const netAlpha = grossAlpha - costBps / 100;
    return { signalScore, strategyReturn, benchmarkReturn, costBps, turnover, grossAlpha, netAlpha };
  });
  const returns = rows.map((row) => row.netAlpha);
  const winners = returns.filter((value) => value > 0);
  const losers = returns.filter((value) => value <= 0);
  const avgWinner = average(winners);
  const avgLoser = average(losers);
  const hitRate = rows.length ? winners.length / rows.length : null;
  const expectedValue = hitRate === null ? null : hitRate * (avgWinner ?? 0) + (1 - hitRate) * (avgLoser ?? 0);
  const deviation = standardDeviation(returns);
  return {
    horizon,
    sample_size: rows.length,
    validation_status: rows.length >= minimumSample ? 'eligible' : 'insufficient_sample',
    hit_rate_pct: rounded(hitRate === null ? null : hitRate * 100, 2),
    average_net_alpha_pct: rounded(average(returns)),
    median_net_alpha_pct: rounded(median(returns)),
    average_winner_pct: rounded(avgWinner),
    average_loser_pct: rounded(avgLoser),
    win_loss_ratio: rounded(avgWinner !== null && avgLoser ? Math.abs(avgWinner / avgLoser) : null),
    expected_value_pct: rounded(expectedValue),
    information_coefficient: rounded(pearson(rows.map((row) => row.signalScore), returns)),
    signal_sharpe: rounded(deviation ? average(returns) / deviation : null),
    maximum_drawdown_pct: rounded(maximumDrawdown(returns)),
    average_turnover: rounded(average(rows.map((row) => row.turnover))),
    average_estimated_cost_bps: rounded(average(rows.map((row) => row.costBps))),
    gross_alpha_pct: rounded(rows.reduce((sum, row) => sum + row.grossAlpha, 0)),
    net_alpha_pct: rounded(rows.reduce((sum, row) => sum + row.netAlpha, 0)),
  };
}

export function validateAcrossHorizons(outcomesByHorizon, options = {}) {
  return VALIDATION_HORIZONS.map((horizon) => evaluateSignalOutcomes(outcomesByHorizon?.[horizon] || [], { ...options, horizon }));
}
