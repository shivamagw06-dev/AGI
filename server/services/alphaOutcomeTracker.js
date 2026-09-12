import { VALIDATION_HORIZONS } from './alphaValidation.js';
import { tradingCalendar } from './tradingCalendarService.js';

const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;
const INTRADAY_MINUTES = Object.freeze({ '5m': 5, '15m': 15, '30m': 30, '1h': 60 });

function finite(value, field) {
  const result = Number(value);
  if (!Number.isFinite(result)) throw new Error(`Invalid ${field}.`);
  return result;
}

function round(value, digits = 6) {
  return Number(value.toFixed(digits));
}

function directionMultiplier(direction) {
  const normalized = String(direction || '').toLowerCase();
  if (['positive', 'long', 'bullish', 'positive_research_candidate'].includes(normalized)) return 1;
  if (['negative', 'short', 'bearish', 'negative_research_candidate'].includes(normalized)) return -1;
  throw new Error('Outcome tracking requires a positive or negative signal direction.');
}

function istParts(date) {
  const shifted = new Date(date.getTime() + IST_OFFSET_MS);
  return {
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth(),
    day: shifted.getUTCDate(),
    weekday: shifted.getUTCDay(),
  };
}

function istDate(year, month, day, hour, minute) {
  return new Date(Date.UTC(year, month, day, hour, minute) - IST_OFFSET_MS);
}

export function horizonDueAt(asOf, horizon) {
  if (!VALIDATION_HORIZONS.includes(horizon)) throw new Error(`Unsupported outcome horizon: ${horizon}.`);
  const signalTime = new Date(asOf);
  if (Number.isNaN(signalTime.getTime())) throw new Error('Invalid signal timestamp.');
  if (INTRADAY_MINUTES[horizon]) return new Date(signalTime.getTime() + INTRADAY_MINUTES[horizon] * 60_000).toISOString();
  const parts = istParts(signalTime);
  if (horizon === 'close') return istDate(parts.year, parts.month, parts.day, 15, 30).toISOString();
  if (horizon === 'next_day') return tradingCalendar.addTradingDays(signalTime, 1).toISOString();
  return tradingCalendar.addTradingDays(signalTime, 5).toISOString();
}

export function createOutcomeSchedule(signal) {
  const signalId = String(signal?.id || signal?.signal_id || '').trim();
  if (!signalId) throw new Error('signal id is required.');
  const asOf = signal.as_of || signal.timestamp;
  const priceAtSignal = finite(signal.price_at_signal, 'price_at_signal');
  const niftyAtSignal = finite(signal.nifty_at_signal, 'nifty_at_signal');
  const sectorAtSignal = finite(signal.sector_at_signal, 'sector_at_signal');
  if ([priceAtSignal, niftyAtSignal, sectorAtSignal].some((value) => value <= 0)) throw new Error('Signal anchor prices must be positive.');
  return VALIDATION_HORIZONS.map((horizon) => ({
    signal_id: signalId,
    horizon,
    due_at: horizonDueAt(asOf, horizon),
    status: 'pending',
    price_at_signal: priceAtSignal,
    nifty_at_signal: niftyAtSignal,
    sector_at_signal: sectorAtSignal,
  }));
}

/** Calculate direction-aware forward results. Returns percentages, not decimals. */
export function calculateSignalOutcome({
  direction,
  priceAtSignal,
  futurePrice,
  niftyAtSignal,
  futureNifty,
  sectorAtSignal,
  futureSector,
  beta = 1,
  estimatedCostBps = 0,
}) {
  const multiplier = directionMultiplier(direction);
  const start = finite(priceAtSignal, 'priceAtSignal');
  const future = finite(futurePrice, 'futurePrice');
  const marketStart = finite(niftyAtSignal, 'niftyAtSignal');
  const marketFuture = finite(futureNifty, 'futureNifty');
  const sectorStart = finite(sectorAtSignal, 'sectorAtSignal');
  const sectorFuture = finite(futureSector, 'futureSector');
  const stockBeta = finite(beta, 'beta');
  const costBps = finite(estimatedCostBps, 'estimatedCostBps');
  if ([start, future, marketStart, marketFuture, sectorStart, sectorFuture].some((value) => value <= 0) || costBps < 0) {
    throw new Error('Outcome prices must be positive and cost cannot be negative.');
  }
  const stockReturn = (future / start - 1) * 100;
  const marketReturn = (marketFuture / marketStart - 1) * 100;
  const sectorReturn = (sectorFuture / sectorStart - 1) * 100;
  const directionalReturn = multiplier * stockReturn;
  const marketAlpha = multiplier * (stockReturn - stockBeta * marketReturn);
  const sectorAlpha = multiplier * (stockReturn - sectorReturn);
  return {
    direction_multiplier: multiplier,
    stock_return_pct: round(stockReturn),
    market_return_pct: round(marketReturn),
    sector_return_pct: round(sectorReturn),
    directional_return_pct: round(directionalReturn),
    market_adjusted_alpha_pct: round(marketAlpha),
    sector_adjusted_alpha_pct: round(sectorAlpha),
    estimated_cost_bps: costBps,
    net_alpha_pct: round(sectorAlpha - costBps / 100),
    positive_outcome: sectorAlpha - costBps / 100 > 0,
  };
}

export async function processDueOutcomes({ repository, priceProvider, now = new Date(), limit = 500 }) {
  if (!repository || !priceProvider) throw new Error('Outcome repository and price provider are required.');
  const due = await repository.listDue(now.toISOString(), limit);
  const summary = { due: due.length, completed: 0, deferred: 0, failed: 0 };
  for (const row of due) {
    try {
      const prices = await priceProvider.getOutcomePrices(row);
      if (!prices || [prices.futurePrice, prices.futureNifty, prices.futureSector].some((value) => !Number.isFinite(Number(value)))) {
        summary.deferred += 1;
        continue;
      }
      const result = calculateSignalOutcome({
        direction: row.direction,
        priceAtSignal: row.price_at_signal,
        niftyAtSignal: row.nifty_at_signal,
        sectorAtSignal: row.sector_at_signal,
        beta: row.beta ?? 1,
        estimatedCostBps: row.estimated_cost_bps ?? 0,
        ...prices,
      });
      await repository.complete(row.id, { ...prices, ...result, observed_at: now.toISOString(), status: 'completed' });
      summary.completed += 1;
    } catch (error) {
      summary.failed += 1;
      await repository.recordFailure?.(row.id, error.message);
    }
  }
  return summary;
}
