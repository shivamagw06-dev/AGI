import { getHistoricalCandles as getGrowwHistoricalCandles } from '../providers/groww.js';
import { getHistoricalCandles as getUpstoxHistoricalCandles } from '../providers/upstox.js';

export const UPSTOX_INDEX_KEYS = Object.freeze({
  NIFTY: 'NSE_INDEX|Nifty 50',
  NIFTYBANK: 'NSE_INDEX|Nifty Bank',
  NIFTYIT: 'NSE_INDEX|Nifty IT',
  NIFTYAUTO: 'NSE_INDEX|Nifty Auto',
  NIFTYFMCG: 'NSE_INDEX|Nifty FMCG',
  NIFTYPHARMA: 'NSE_INDEX|Nifty Pharma',
  NIFTYMETAL: 'NSE_INDEX|Nifty Metal',
  NIFTYENERGY: 'NSE_INDEX|Nifty Energy',
  NIFTYREALTY: 'NSE_INDEX|Nifty Realty',
  NIFTYPSUBANK: 'NSE_INDEX|Nifty PSU Bank',
  FINNIFTY: 'NSE_INDEX|Nifty Financial Services',
  NIFTYMEDIA: 'NSE_INDEX|Nifty Media',
});

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

function chronological(candles) {
  return [...(candles || [])].sort((left, right) => Date.parse(left?.[0]) - Date.parse(right?.[0]));
}

export async function getHistoricalCandlesWithFallback({
  exchange = 'NSE', segment = 'CASH', tradingSymbol, days = 120,
  upstoxInstrumentKey, minimumCandles = 1,
} = {}) {
  const failures = [];
  try {
    const candles = await getGrowwHistoricalCandles(exchange, segment, tradingSymbol, days);
    if ((candles || []).length >= minimumCandles) return { candles, source: 'groww', failures };
    failures.push(`groww returned ${(candles || []).length} candles`);
  } catch (error) {
    failures.push(`groww: ${error.message}`);
  }

  const instrumentKey = upstoxInstrumentKey || UPSTOX_INDEX_KEYS[tradingSymbol];
  if (!instrumentKey) throw new Error(`${tradingSymbol} history unavailable (${failures.join('; ')}); Upstox instrument key missing`);

  try {
    const to = new Date();
    const from = new Date(to.getTime() - days * 24 * 60 * 60 * 1000);
    const payload = await getUpstoxHistoricalCandles(instrumentKey, {
      unit: 'days', interval: 1, from: isoDate(from), to: isoDate(to),
    });
    const candles = chronological(payload?.data?.candles || []);
    if (candles.length < minimumCandles) {
      throw new Error(`returned ${candles.length} candles; required ${minimumCandles}`);
    }
    return { candles, source: 'upstox', failures };
  } catch (error) {
    failures.push(`upstox: ${error.message}`);
    throw new Error(`${tradingSymbol} history unavailable: ${failures.join('; ')}`);
  }
}
