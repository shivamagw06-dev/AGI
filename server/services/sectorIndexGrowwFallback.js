/**
 * Groww LTP fallback for NSE sector indices when Upstox live feed auth fails.
 * Keeps sector_at_signal anchors populated for confluence validation.
 */

import { getLTP, isGrowwConfigured } from '../providers/groww.js';

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
  const ltp = await getLTP(exchangeSymbols, 'CASH');
  const receivedAt = new Date().toISOString();
  const snapshots = [];
  for (const [instrumentKey, symbol] of growwByKey.entries()) {
    const quote = readGrowwLtpRow(ltp, symbol);
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
