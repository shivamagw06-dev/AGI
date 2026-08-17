/**
 * AGI Equity Opportunity V1 — research shortlist computed on Render.
 *
 * Groww Cloud can fetch market data but cannot reach external HTTPS (Render or
 * Supabase). This module runs the same scoring logic on the Node API and
 * persists via ingestPayload (direct Supabase write, no outbound ingest hop).
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ingestPayload, STRATEGIES } from './researchSignalIngest.js';
import { getHistoricalCandlesWithFallback } from './marketHistoricalCandles.js';

export const STRATEGY = STRATEGIES.EQUITY;
export const SCHEMA_VERSION = '1.0';

export const DEFAULT_UNIVERSE =
  'RELIANCE,HDFCBANK,ICICIBANK,INFY,TCS,BHARTIARTL,ITC,LT,SBIN,AXISBANK,KOTAKBANK,HINDUNILVR,BAJFINANCE,MARUTI,SUNPHARMA,NTPC,TITAN,ULTRACEMCO,ASIANPAINT,POWERGRID,M&M,NESTLEIND,TATASTEEL,ONGC,TECHM,WIPRO,COALINDIA,JSWSTEEL,HCLTECH,ADANIENT,ADANIPORTS,BAJAJFINSV,GRASIM,DRREDDY,CIPLA,EICHERMOT,HEROMOTOCO,APOLLOHOSP,BRITANNIA,DIVISLAB,INDUSINDBK,TATACONSUM,SBILIFE,HDFCLIFE,BPCL,SHRIRAMFIN,TRENT,BEL,JIOFIN,BAJAJ-AUTO';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const serverDir = path.dirname(fileURLToPath(import.meta.url));
const defaultNifty500Path = path.join(serverDir, '../../indices/Nifty500.csv');

function istTimestamp(now = new Date()) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
      .formatToParts(now)
      .map((part) => [part.type, part.value])
  );
  const ms = String(now.getMilliseconds()).padStart(3, '0');
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}.${ms}+05:30`;
}

function istRunId(now = new Date()) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
      .formatToParts(now)
      .map((part) => [part.type, part.value])
  );
  return `${STRATEGY}:${parts.year}${parts.month}${parts.day}T${parts.hour}${parts.minute}${parts.second}+0530`;
}

export function returnPct(values, n) {
  if (values.length <= n || !values[values.length - n - 1]) return null;
  return ((values[values.length - 1] / values[values.length - n - 1]) - 1) * 100;
}

export function stdev(values) {
  if (values.length < 2) return 0;
  const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance);
}

function candleSeries(candles) {
  const rows = (candles || []).filter((row) => Array.isArray(row) && row.length >= 6);
  return {
    closes: rows.map((row) => Number(row[4])).filter(Number.isFinite),
    volumes: rows.map((row) => Number(row[5])).filter(Number.isFinite),
  };
}

async function loadNiftyBenchmark(lookbackDays, providerUsage) {
  const windows = [...new Set([lookbackDays, 120])];
  const failures = [];
  for (const days of windows) {
    try {
      const result = await getHistoricalCandlesWithFallback({ tradingSymbol: 'NIFTY', days, minimumCandles: 65 });
      const candles = result.candles;
      providerUsage[result.source] += 1;
      const closes = candleSeries(candles).closes;
      if (closes.length >= 65) return closes;
      failures.push(`${days}d returned ${closes.length} candles`);
    } catch (error) {
      failures.push(`${days}d: ${error.message}`);
    }
  }
  throw new Error(`NIFTY benchmark history unavailable: ${failures.join('; ')}`);
}

export function analyseEquity(symbol, candles, benchmark) {
  const { closes, volumes } = candleSeries(candles);
  if (closes.length < 65 || volumes.length < 65) return null;

  const r20 = returnPct(closes, 20);
  const r60 = returnPct(closes, 60);
  const daily = [];
  for (let i = 1; i < closes.length; i += 1) {
    daily.push(((closes[i] / closes[i - 1]) - 1) * 100);
  }
  const vol = stdev(daily.slice(-20)) * Math.sqrt(252);
  const volumeAvg = volumes.slice(-20).reduce((sum, value) => sum + value, 0) / 20;
  const volumeRatio = volumeAvg ? volumes[volumes.length - 1] / volumeAvg : 0;
  const ma20 = closes.slice(-20).reduce((sum, value) => sum + value, 0) / 20;
  const ma50 = closes.slice(-50).reduce((sum, value) => sum + value, 0) / 50;
  const relative20 = (r20 || 0) - (benchmark.return_20d || 0);
  const relative60 = (r60 || 0) - (benchmark.return_60d || 0);

  const score = Math.round(
    Math.max(
      0,
      Math.min(
        100,
        50
          + Math.max(-15, Math.min(15, r20 || 0))
          + Math.max(-15, Math.min(15, relative60))
          + (closes[closes.length - 1] > ma20 && ma20 > ma50 ? 8 : -8)
          + (volumeRatio > 1.2 ? 5 : 0)
          - Math.max(0, Math.min(10, (vol - 20) / 2))
      )
    ) * 10
  ) / 10;

  const reasons = [];
  if (closes[closes.length - 1] > ma20 && ma20 > ma50) {
    reasons.push('Price above rising 20/50-day structure');
  }
  if (relative20 > 3) reasons.push('Twenty-day outperformance versus Nifty');
  if (relative60 > 5) reasons.push('Persistent sixty-day relative strength');
  if (volumeRatio > 1.2) reasons.push('Latest volume above twenty-day average');
  if (vol > 30) reasons.push('Elevated volatility requires risk review');

  const lastClose = closes[closes.length - 1];
  let trend = 'mixed';
  if (lastClose > ma20 && ma20 > ma50) trend = 'positive';
  else if (lastClose < ma20 && ma20 < ma50) trend = 'negative';

  return {
    symbol,
    score,
    close: lastClose,
    return_20d: r20 == null ? null : Math.round(r20 * 100) / 100,
    return_60d: r60 == null ? null : Math.round(r60 * 100) / 100,
    relative_20d: Math.round(relative20 * 100) / 100,
    relative_60d: Math.round(relative60 * 100) / 100,
    volatility_20d: Math.round(vol * 100) / 100,
    volume_ratio: Math.round(volumeRatio * 100) / 100,
    trend,
    volume_confirmation: volumeRatio > 1.2,
    risk: vol > 30 ? 'high' : vol > 20 ? 'moderate' : 'low',
    reasons: reasons.length ? reasons : ['No strong factor confirmation'],
  };
}

export async function loadEquityUniverse() {
  const limit = Math.max(5, Math.min(500, Number(process.env.AGI_MAX_SYMBOLS || 500) || 500));
  const configured = String(process.env.AGI_UNIVERSE || '').trim();
  if (configured) {
    return configured.split(',').map((symbol) => symbol.trim().toUpperCase()).filter(Boolean).slice(0, limit);
  }
  try {
    const csvPath = process.env.AGI_NIFTY500_PATH || process.env.AGI_NIFTY200_PATH || defaultNifty500Path;
    const rows = (await fs.readFile(csvPath, 'utf8')).split(/\r?\n/).slice(1).filter(Boolean);
    const symbols = rows.map((line) => line.split(',')[2]?.trim().toUpperCase()).filter(Boolean);
    if (symbols.length !== 500 || new Set(symbols).size !== 500) {
      throw new Error(`expected 500 unique symbols, received ${symbols.length}`);
    }
    return symbols.slice(0, limit);
  } catch (error) {
    console.warn('[groww-equity-opportunity] Nifty 200 universe unavailable, using core fallback:', error.message);
    return DEFAULT_UNIVERSE.split(',').map((symbol) => symbol.trim()).slice(0, limit);
  }
}

export async function runGrowwEquityOpportunityResearch({ force = false } = {}) {
  const delayMs = Math.max(100, Number(process.env.AGI_CALL_DELAY_SEC || 0.22) * 1000);
  const symbols = await loadEquityUniverse();
  const lookbackDays = Math.max(120, Number(process.env.AGI_LOOKBACK_DAYS || 175) || 175);
  const providerUsage = { groww: 0, upstox: 0 };

  const csvPath = process.env.AGI_NIFTY500_PATH || process.env.AGI_NIFTY200_PATH || defaultNifty500Path;
  const isinBySymbol = new Map();
  try {
    const lines = (await fs.readFile(csvPath, 'utf8')).split(/\r?\n/).slice(1).filter(Boolean);
    for (const line of lines) {
      const columns = line.split(',');
      const symbol = columns[2]?.trim().toUpperCase();
      const isin = columns[4]?.trim().toUpperCase();
      if (symbol && isin) isinBySymbol.set(symbol, isin);
    }
  } catch (error) {
    console.warn('[groww-equity-opportunity] Upstox ISIN map unavailable:', error.message);
  }

  const niftyCloses = await loadNiftyBenchmark(lookbackDays, providerUsage);

  const benchmark = {
    return_20d: returnPct(niftyCloses, 20),
    return_60d: returnPct(niftyCloses, 60),
  };

  await sleep(delayMs);

  const rows = [];
  const errors = [];
  for (const symbol of symbols) {
    try {
      const result = await getHistoricalCandlesWithFallback({
        tradingSymbol: symbol, days: lookbackDays, minimumCandles: 65,
        upstoxInstrumentKey: isinBySymbol.get(symbol) ? `NSE_EQ|${isinBySymbol.get(symbol)}` : null,
      });
      providerUsage[result.source] += 1;
      const candles = result.candles;
      const result = analyseEquity(symbol, candles, benchmark);
      if (result) rows.push(result);
    } catch (error) {
      errors.push({ symbol, error: String(error?.message || error).slice(0, 160) });
    }
    await sleep(delayMs);
  }

  rows.sort((left, right) => right.score - left.score);
  // Persist the complete cross-section. Downstream conviction ranking needs
  // every constituent, not only the ten names already selected by momentum.
  const candidates = rows.map((row, index) => ({
    ...row,
    rank: index + 1,
    signal: 'research_candidate',
  }));
  const deteriorating = [...rows]
    .sort((left, right) => left.score - right.score)
    .slice(0, 10)
    .map((row) => ({ ...row, signal: 'risk_review' }));

  const now = new Date();
  const payload = {
    strategy: STRATEGY,
    schema_version: SCHEMA_VERSION,
    run_id: istRunId(now),
    as_of: istTimestamp(now),
    research_only: true,
    universe_size: symbols.length,
    processed: rows.length,
    benchmark,
    provider_usage: providerUsage,
    universe: 'nifty500',
    shortlist_size: Math.min(20, rows.length),
    candidates,
    deteriorating,
    errors: errors.slice(0, 20),
  };

  const rawBody = Buffer.from(JSON.stringify(payload));
  const result = await ingestPayload(payload, rawBody);
  return {
    ok: true,
    forced: Boolean(force),
    runId: result.runId,
    duplicate: Boolean(result.duplicate),
    accepted: result.accepted ?? 0,
    processed: rows.length,
    universe_size: symbols.length,
    errors: errors.length,
    provider_usage: providerUsage,
  };
}
