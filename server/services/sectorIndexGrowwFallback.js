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

export async function pollGrowwIndexSnapshots(instrumentKeys = []) {
  if (!isGrowwConfigured()) return [];
  const keys = [...new Set((instrumentKeys || []).map(String).filter(Boolean))];
  const growwByKey = new Map();
  for (const key of keys) {
    const symbol = growwSymbolForIndex(key);
    if (symbol) growwByKey.set(key, symbol);
  }
  if (!growwByKey.size) return [];

  const ltp = await getLTP([...new Set(growwByKey.values())], 'CASH');
  const receivedAt = new Date().toISOString();
  const snapshots = [];
  for (const [instrumentKey, symbol] of growwByKey.entries()) {
    const row = ltp?.[symbol] ?? ltp?.[`NSE_${symbol}`] ?? ltp?.[`NSE:${symbol}`];
    const price = Number(row?.ltp ?? row?.last_price ?? row?.close);
    if (!Number.isFinite(price) || price <= 0) continue;
    snapshots.push({
      instrument_key: instrumentKey,
      received_at: receivedAt,
      ltp: price,
      source: 'groww_fallback',
    });
  }
  return snapshots;
}
