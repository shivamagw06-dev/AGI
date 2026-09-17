/**
 * Daily history for the basket: volume baselines, and the inputs Stage 2 of
 * the screen needs.
 *
 * Upstox daily candles are `[timestamp, open, high, low, close, volume, oi]`.
 * Everything here is computed from those and nothing is invented: a member
 * with too little history gets null and a reason, not a number derived from
 * three days pretending to be twenty.
 */

/** Minimum sessions before an average is worth quoting. */
export const MIN_SESSIONS = 15;

const numeric = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

/** Upstox's candle envelope, flattened and sorted oldest-first. */
export function candleRows(payload) {
  const raw = payload?.data?.candles || payload?.candles || [];
  const rows = [];
  for (const candle of raw) {
    if (!Array.isArray(candle) || candle.length < 6) continue;
    const at = Date.parse(candle[0]);
    const close = numeric(candle[4]);
    const volume = numeric(candle[5]);
    if (!Number.isFinite(at) || close === null || volume === null) continue;
    rows.push({ at, close, volume, turnover: close * volume });
  }
  return rows.sort((a, b) => a.at - b.at);
}

const median = (values) => {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
};

/**
 * Average daily volume and median daily turnover over a window.
 *
 * Turnover uses the median rather than the mean, because one block trade in a
 * thin name moves a mean enough to carry that name through a liquidity floor
 * it does not actually clear.
 */
export function liquidityFrom(payload, { sessions = 120, minSessions = MIN_SESSIONS } = {}) {
  const rows = candleRows(payload).slice(-sessions);
  if (rows.length < minSessions) {
    return {
      sessions: rows.length, averageDailyVolume: null, medianDailyTurnover: null,
      lastClose: rows.length ? rows[rows.length - 1].close : null,
      reason: 'INSUFFICIENT_HISTORY',
    };
  }
  const volumes = rows.map((one) => one.volume);
  return {
    sessions: rows.length,
    averageDailyVolume: Math.round(volumes.reduce((a, b) => a + b, 0) / volumes.length),
    medianDailyTurnover: Math.round(median(rows.map((one) => one.turnover))),
    lastClose: rows[rows.length - 1].close,
    reason: null,
  };
}

/**
 * Liquidity for every member, keyed by symbol.
 *
 * `fetchCandles` is injected so this is testable without a network and
 * without credentials. A member whose fetch fails is recorded with its error
 * rather than omitted, because a silently short baseline map is how a volume
 * ratio becomes null for reasons nobody can explain later.
 */
export async function liquidityForUniverse(universe, { fetchCandles, sessions = 120, to, from } = {}) {
  const members = (universe?.members || []).filter((one) => one.admitted !== false);
  const bySymbol = {};
  const failures = [];
  for (const member of members) {
    const key = String(member.instrumentKey || '').trim();
    if (!key.includes('|')) {
      failures.push({ symbol: member.symbol, error: 'MALFORMED_INSTRUMENT_KEY' });
      continue;
    }
    try {
      const payload = await fetchCandles(key, { unit: 'days', interval: 1, to, from });
      bySymbol[member.symbol] = liquidityFrom(payload, { sessions });
    } catch (error) {
      failures.push({ symbol: member.symbol, error: String(error?.message || error) });
    }
  }
  return { bySymbol, failures };
}

/** Just the volume baselines, for the live runtime. */
export function volumeBaselines(liquidity) {
  const baselines = {};
  for (const [symbol, row] of Object.entries(liquidity?.bySymbol || {})) {
    if (row.averageDailyVolume !== null) baselines[symbol] = row.averageDailyVolume;
  }
  return baselines;
}
