const MAX_SIGNAL_AGE_MS = 15 * 60_000;
const MAX_PRICE_AGE_MS = 90_000;
const MAX_COMPONENT_GAP_MS = 5 * 60_000;

function positiveNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function recent(timestamp, now, maxAge) {
  const age = now.getTime() - Date.parse(timestamp || '');
  return Number.isFinite(age) && age >= 0 && age <= maxAge;
}

// A measured opening range yields a transparent, unvalidated price projection.
// Other engines do not contain a calibrated price target in their output.
function rangeProjection(row, direction, signalPrice) {
  const breakout = row.active.find((signal) => signal.engine === 'opening_range_expansion_v1'
    && signal.direction === direction);
  const high = positiveNumber(breakout?.factor_values?.opening_high);
  const low = positiveNumber(breakout?.factor_values?.opening_low);
  if (!high || !low || high <= low) return null;
  const projected = direction === 'positive' ? high + (high - low) : low - (high - low);
  if (!(projected > 0) || (direction === 'positive' ? projected <= signalPrice : projected >= signalPrice)) return null;
  return Math.round(projected * 100) / 100;
}

/** Research setups, never orders: require same-direction evidence and live inputs. */
export function buildLiveAlphaSetups(rows, { freshness, runtime, now = new Date(), limit = 6 } = {}) {
  if (freshness?.stale !== false || runtime?.market_session?.open !== true
    || runtime?.feed?.status !== 'connected' || runtime?.evaluation_status !== 'live') return [];
  return rows.flatMap((row) => {
    if (!row.active?.length || row.signal_structure === 'CONFLICTING') return [];
    const direction = row.active[0].direction;
    if (!['positive', 'negative'].includes(direction) || row.active.some((signal) => signal.direction !== direction)) return [];
    const times = row.active.map((signal) => Date.parse(signal.as_of || ''));
    if (times.some((time) => !Number.isFinite(time)) || Math.max(...times) - Math.min(...times) > MAX_COMPONENT_GAP_MS) return [];
    const signalAt = new Date(Math.max(...times)).toISOString();
    if (!recent(signalAt, now, MAX_SIGNAL_AGE_MS)) return [];
    const currentPrice = recent(row.price_as_of, now, MAX_PRICE_AGE_MS) ? positiveNumber(row.live_price) : null;
    const signalPrice = positiveNumber(row.active.find((signal) => signal.price_at_signal)?.price_at_signal);
    if (!signalPrice || !currentPrice || row.active.some((signal) => signal.liquidity_ok !== true || signal.liquidity_verified !== true)) return [];
    return [{
      symbol: row.symbol, sector: row.sector, direction, score: row.composite,
      engines: row.active.map((signal) => signal.engine), signal_at: signalAt,
      price: currentPrice, price_as_of: row.price_as_of,
      target: rangeProjection(row, direction, signalPrice),
      target_basis: 'Opening range measured move; unvalidated scenario level',
      confidence: row.confidence,
    }];
  }).sort((a, b) => b.engines.length - a.engines.length || Math.abs(b.score) - Math.abs(a.score))
    .slice(0, Math.max(0, limit));
}
