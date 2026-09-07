/**
 * Groww LTP fallback for NSE sector indices when Upstox live feed auth fails.
 * Keeps sector_at_signal anchors populated for confluence validation.
 */

import { getLTP, getOHLC, isGrowwConfigured } from '../providers/groww.js';

/** Upstox NSE_INDEX key → Groww NSE CASH symbol */
export const SECTOR_INDEX_GROWW = Object.freeze({
  'NSE_INDEX|Nifty 50': 'NIFTY',
  'NSE_INDEX|Nifty Bank': 'NIFTYBANK',
  'NSE_INDEX|Nifty IT': 'NIFTYIT',
  'NSE_INDEX|Nifty Auto': 'NIFTYAUTO',
  'NSE_INDEX|Nifty FMCG': 'NIFTYFMCG',
  'NSE_INDEX|Nifty Pharma': 'NIFTYPHARMA',
  'NSE_INDEX|Nifty Metal': 'NIFTYMETAL',
  'NSE_INDEX|Nifty Energy': 'NIFTYENERGY',
  'NSE_INDEX|Nifty Realty': 'NIFTYREALTY',
  'NSE_INDEX|Nifty Financial Services': 'FINNIFTY',
  'NSE_INDEX|Nifty Infrastructure': 'NIFTYINFRA',
  'NSE_INDEX|Nifty India Digital': 'NIFTYIT',
});

export function growwSymbolForIndex(instrumentKey) {
  return SECTOR_INDEX_GROWW[String(instrumentKey || '').trim()] || null;
}

/** Groww REST LTP expects NSE_NIFTY, not the bare trading symbol NIFTY. */
export function growwExchangeSymbol(instrumentKey) {
  const symbol = growwSymbolForIndex(instrumentKey);
  return symbol ? `NSE_${symbol}` : null;
}

/** Yesterday's close — never today's running close, which would collapse 15m/60m returns to ~0. */
export function growwQuotePreviousClose(quote) {
  const candle = quote?.ohlc && typeof quote.ohlc === 'object' && !Array.isArray(quote.ohlc)
    ? quote.ohlc
    : Array.isArray(quote?.ohlc) ? quote.ohlc[0] : null;
  const previous = Number(
    quote?.previous_close
    ?? quote?.prev_close
    ?? candle?.previous_close
    ?? candle?.prev_close
    ?? candle?.cp
  );
  return Number.isFinite(previous) && previous > 0 ? previous : null;
}

/** Prefer LTP, then OHLC close. Previous close comes from either payload. */
export function mergeGrowwIndexQuote(ltpPayload, ohlcPayload, symbol) {
  const quote = readGrowwLtpRow(ltpPayload, symbol) || readGrowwLtpRow(ohlcPayload, symbol);
  if (!quote) return null;
  if (quote.previous_close > 0) return quote;
  const fromOhlc = readGrowwLtpRow(ohlcPayload, symbol);
  const previous = fromOhlc?.previous_close;
  return previous > 0 ? { ...quote, previous_close: previous } : quote;
}

export function readGrowwLtpRow(payload, symbol) {
  if (!payload || typeof payload !== 'object' || !symbol) return null;
  const row = payload[symbol]
    ?? payload[`NSE_${symbol}`]
    ?? payload[`NSE:${symbol}`]
    ?? payload[`NSE-${symbol}`];
  if (row == null) return null;
  if (typeof row === 'number') {
    return Number.isFinite(row) && row > 0 ? { ltp: row, previous_close: null } : null;
  }
  const ltp = Number(row.ltp ?? row.last_price ?? row.close);
  if (!Number.isFinite(ltp) || ltp <= 0) return null;
  const previous = Number(row.previous_close ?? row.prev_close ?? row.cp);
  return {
    ltp,
    previous_close: Number.isFinite(previous) && previous > 0 ? previous : null,
  };
}

export async function pollGrowwIndexSnapshots(instrumentKeys = []) {
  if (!isGrowwConfigured()) return [];
  const keys = [...new Set((instrumentKeys || []).map(String).filter(Boolean))];
  const growwByKey = new Map();
  for (const key of keys) {
    const symbol = growwSymbolForIndex(key);
    if (symbol) growwByKey.set(key, symbol);
  }
  if (!growwByKey.size) return [];

  const exchangeSymbols = [...new Set([...growwByKey.values()].map((symbol) => `NSE_${symbol}`))];
  const [ltp, ohlc] = await Promise.all([
    getLTP(exchangeSymbols, 'CASH'),
    getOHLC(exchangeSymbols, 'CASH').catch(() => ({})),
  ]);
  const receivedAt = new Date().toISOString();
  const snapshots = [];
  for (const [instrumentKey, symbol] of growwByKey.entries()) {
    const quote = mergeGrowwIndexQuote(ltp, ohlc, symbol);
    if (!quote) continue;
    snapshots.push({
      instrument_key: instrumentKey,
      received_at: receivedAt,
      ltp: quote.ltp,
      previous_close: quote.previous_close,
      source: 'groww_fallback',
    });
  }
  return snapshots;
}
