import { tradingCalendar } from './tradingCalendarService.js';

const IST_OFFSET_MS = 5.5 * 60 * 60_000;
export const CONFLUENCE_HORIZONS = Object.freeze(['5m', '15m', '30m', '60m', 'close', '1d', '5d', '20d']);
const MINUTES = Object.freeze({ '5m': 5, '15m': 15, '30m': 30, '60m': 60 });

const finite = (value, name) => { const parsed = Number(value); if (!Number.isFinite(parsed)) throw new Error(`Invalid ${name}.`); return parsed; };
const round = (value) => Number(value.toFixed(6));
const median = (values) => { const clean = [...values].sort((a, b) => a - b); const mid = Math.floor(clean.length / 2); return clean.length % 2 ? clean[mid] : (clean[mid - 1] + clean[mid]) / 2; };
const istDate = (date, hour = 15, minute = 30) => { const shifted = new Date(date.getTime() + IST_OFFSET_MS); return new Date(Date.UTC(shifted.getUTCFullYear(), shifted.getUTCMonth(), shifted.getUTCDate(), hour, minute) - IST_OFFSET_MS); };

export function confluenceHorizonDueAt(capturedAt, horizon) {
  if (!CONFLUENCE_HORIZONS.includes(horizon)) throw new Error(`Unsupported confluence horizon: ${horizon}.`);
  const at = new Date(capturedAt); if (Number.isNaN(at.getTime())) throw new Error('Invalid confluence timestamp.');
  if (MINUTES[horizon]) return new Date(at.getTime() + MINUTES[horizon] * 60_000).toISOString();
  if (horizon === 'close') return istDate(at).toISOString();
  return tradingCalendar.addTradingDays(at, horizon === '1d' ? 1 : horizon === '5d' ? 5 : 20).toISOString();
}

export function createConfluenceOutcomeSchedule(eventId, capturedAt) {
  if (!eventId) throw new Error('Confluence event id is required.');
  return CONFLUENCE_HORIZONS.map((horizon) => ({ event_id: eventId, horizon, due_at: confluenceHorizonDueAt(capturedAt, horizon), status: 'pending' }));
}

export function calculateConfluenceOutcome({ priceAtSignal, futurePrice, benchmarkAtSignal, futureBenchmark, sectorAtSignal, futureSector }) {
  const start = finite(priceAtSignal, 'priceAtSignal'), future = finite(futurePrice, 'futurePrice');
  const benchmarkStart = finite(benchmarkAtSignal, 'benchmarkAtSignal'), benchmarkFuture = finite(futureBenchmark, 'futureBenchmark');
  const sectorStart = finite(sectorAtSignal, 'sectorAtSignal'), sectorFutureValue = finite(futureSector, 'futureSector');
  if ([start, future, benchmarkStart, benchmarkFuture, sectorStart, sectorFutureValue].some((value) => value <= 0)) throw new Error('Confluence outcome prices must be positive.');
  const stock = (future / start - 1) * 100, benchmark = (benchmarkFuture / benchmarkStart - 1) * 100, sector = (sectorFutureValue / sectorStart - 1) * 100;
  return { stock_return_pct: round(stock), benchmark_return_pct: round(benchmark), sector_return_pct: round(sector), excess_return_pct: round(stock - benchmark), sector_adjusted_alpha_pct: round(stock - sector), positive_excess: stock - benchmark > 0 };
}

export function summarizeConfluenceOutcomes(rows) {
  const groups = new Map();
  for (const row of rows || []) {
    if (row.status !== 'completed' || !Number.isFinite(Number(row.excess_return_pct))) continue;
    const key = `${row.classification}|${row.horizon}|${row.market_regime || 'UNCLASSIFIED'}`;
    const group = groups.get(key) || { classification: row.classification, horizon: row.horizon, market_regime: row.market_regime || null, values: [], sector_values: [] };
    group.values.push(Number(row.excess_return_pct)); if (Number.isFinite(Number(row.sector_adjusted_alpha_pct))) group.sector_values.push(Number(row.sector_adjusted_alpha_pct)); groups.set(key, group);
  }
  return [...groups.values()].map((group) => {
    const observations = group.values.length, hitRate = group.values.filter((value) => value > 0).length / observations * 100;
    const reliability = Math.round(Math.min(100, hitRate * Math.min(1, Math.sqrt(observations / 100))));
    return { classification: group.classification, horizon: group.horizon, market_regime: group.market_regime, observations, positive_alpha_rate: Number(hitRate.toFixed(2)), average_excess_return_pct: round(group.values.reduce((sum, value) => sum + value, 0) / observations), median_excess_return_pct: round(median(group.values)), average_sector_adjusted_alpha_pct: group.sector_values.length ? round(group.sector_values.reduce((sum, value) => sum + value, 0) / group.sector_values.length) : null, historical_reliability: reliability, calibrated: observations >= 100 };
  }).sort((a, b) => a.classification.localeCompare(b.classification) || CONFLUENCE_HORIZONS.indexOf(a.horizon) - CONFLUENCE_HORIZONS.indexOf(b.horizon));
}
