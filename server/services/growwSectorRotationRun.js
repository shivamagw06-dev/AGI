/**
 * AGI Sector Rotation V1 — Nifty sector index ranking on Render.
 *
 * Groww Cloud cannot deliver externally. Computes agi_sector_rotation_v1 and
 * persists via ingestPayload directly to Supabase.
 */

import { getHistoricalCandles, isGrowwConfigured } from '../providers/groww.js';
import { ingestPayload, STRATEGIES } from './researchSignalIngest.js';

export const STRATEGY = STRATEGIES.SECTOR;
export const SCHEMA_VERSION = '1.0';

export const DEFAULT_SECTOR_UNIVERSE = [
  'NIFTYBANK',
  'NIFTYIT',
  'NIFTYAUTO',
  'NIFTYFMCG',
  'NIFTYPHARMA',
  'NIFTYMETAL',
  'NIFTYREALTY',
  'NIFTYPSUBANK',
  'FINNIFTY',
  'NIFTYENERGY',
  'NIFTYMEDIA',
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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

export function returnPct(values, periods) {
  if (values.length <= periods || !values[values.length - periods - 1]) return null;
  return ((values[values.length - 1] / values[values.length - periods - 1]) - 1) * 100;
}

export function stdev(values) {
  if (values.length < 2) return 0;
  const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (values.length - 1);
  return Math.sqrt(variance);
}

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

export function classifyRotation(rel20, rel60) {
  if (rel20 >= 0 && rel60 >= 0) return 'leading';
  if (rel20 >= 0 && rel60 < 0) return 'improving';
  if (rel20 < 0 && rel60 >= 0) return 'weakening';
  return 'lagging';
}

function candleCloses(candles) {
  return (candles || [])
    .filter((row) => Array.isArray(row) && row.length >= 6)
    .map((row) => Number(row[4]))
    .filter(Number.isFinite);
}

export function analyseSector(sector, candles, benchmark) {
  const closes = candleCloses(candles);
  if (closes.length < 125) return null;

  const r5 = returnPct(closes, 5);
  const r20 = returnPct(closes, 20);
  const r60 = returnPct(closes, 60);
  const rel20 = (r20 || 0) - (benchmark.return_20d || 0);
  const rel60 = (r60 || 0) - (benchmark.return_60d || 0);
  const ma20 = closes.slice(-20).reduce((sum, value) => sum + value, 0) / 20;
  const ma50 = closes.slice(-50).reduce((sum, value) => sum + value, 0) / 50;
  const ma100 = closes.slice(-100).reduce((sum, value) => sum + value, 0) / 100;
  const dailyReturns = [];
  for (let i = 1; i < closes.length; i += 1) {
    dailyReturns.push(((closes[i] / closes[i - 1]) - 1) * 100);
  }
  const volatility = stdev(dailyReturns.slice(-20)) * Math.sqrt(252);
  const high60 = Math.max(...closes.slice(-60));
  const drawdown60 = ((closes[closes.length - 1] / high60) - 1) * 100;
  const peakWindow = closes.slice(-120);
  let maxDrawdown = 0;
  for (let i = 0; i < peakWindow.length; i += 1) {
    const peak = Math.max(...peakWindow.slice(0, i + 1));
    maxDrawdown = Math.min(maxDrawdown, ((peakWindow[i] / peak) - 1) * 100);
  }

  const trendPoints = closes[closes.length - 1] > ma20 && ma20 > ma50 && ma50 > ma100
    ? 12
    : closes[closes.length - 1] > ma50
      ? 6
      : -10;

  const score = Math.round(
    clamp(
      50
        + clamp(rel20, -10, 10) * 1.1
        + clamp(rel60, -15, 15) * 0.8
        + trendPoints
        - clamp(Math.max(0, volatility - 18) * 0.45, 0, 10)
        + clamp(drawdown60 + 10, -5, 5),
      0,
      100
    ) * 10
  ) / 10;

  return {
    sector,
    score,
    close: Math.round(closes[closes.length - 1] * 100) / 100,
    return_5d: r5 == null ? null : Math.round(r5 * 100) / 100,
    return_20d: r20 == null ? null : Math.round(r20 * 100) / 100,
    return_60d: r60 == null ? null : Math.round(r60 * 100) / 100,
    relative_20d: Math.round(rel20 * 100) / 100,
    relative_60d: Math.round(rel60 * 100) / 100,
    volatility_20d: Math.round(volatility * 100) / 100,
    max_drawdown: Math.round(maxDrawdown * 100) / 100,
    rotation: classifyRotation(rel20, rel60),
    risk: volatility > 28 ? 'high' : volatility > 18 ? 'moderate' : 'low',
    factors: {
      drawdown_60d: Math.round(drawdown60 * 100) / 100,
      trend: closes[closes.length - 1] > ma20 && ma20 > ma50 && ma50 > ma100
        ? 'positive'
        : closes[closes.length - 1] < ma20 && ma20 < ma50
          ? 'negative'
          : 'mixed',
    },
  };
}

function parseSectors() {
  const raw = String(process.env.AGI_SECTOR_UNIVERSE || DEFAULT_SECTOR_UNIVERSE.join(','));
  return raw
    .split(',')
    .map((entry) => {
      const trimmed = entry.trim().toUpperCase();
      if (!trimmed) return null;
      if (trimmed.includes(':')) return trimmed.split(':').pop().trim();
      return trimmed;
    })
    .filter(Boolean);
}

export async function runGrowwSectorRotationResearch({ force = false } = {}) {
  if (!isGrowwConfigured()) {
    throw new Error('Groww auth missing: set GROWW_ACCESS_TOKEN or GROWW_API_KEY + GROWW_API_SECRET');
  }

  const delayMs = Math.max(100, Number(process.env.AGI_CALL_DELAY_SEC || 0.25) * 1000);
  const sectors = parseSectors();
  const benchmarkSymbol = String(process.env.AGI_BENCHMARK_SYMBOL || 'NIFTY').trim().toUpperCase();
  const lookbackDays = Math.max(180, Number(process.env.AGI_SECTOR_LOOKBACK_DAYS || 400) || 400);

  const benchmarkCandles = await getHistoricalCandles('NSE', 'CASH', benchmarkSymbol, lookbackDays);
  const benchmarkCloses = candleCloses(benchmarkCandles);
  if (benchmarkCloses.length < 65) {
    throw new Error(`${benchmarkSymbol} benchmark history too short for sector rotation run`);
  }

  const benchmark = {
    symbol: benchmarkSymbol,
    return_20d: returnPct(benchmarkCloses, 20),
    return_60d: returnPct(benchmarkCloses, 60),
  };
  if (benchmark.return_20d == null || benchmark.return_60d == null) {
    throw new Error('Insufficient benchmark history for sector rotation run');
  }

  await sleep(delayMs);

  const rows = [];
  const errors = [];
  for (const sector of sectors) {
    try {
      const candles = await getHistoricalCandles('NSE', 'CASH', sector, lookbackDays);
      const result = analyseSector(sector, candles, benchmark);
      if (result) rows.push(result);
      else errors.push({ sector, error: 'Insufficient history' });
    } catch (error) {
      errors.push({ sector, error: String(error?.message || error).slice(0, 180) });
    }
    await sleep(delayMs);
  }

  rows.sort((left, right) => right.score - left.score);
  const ranked = rows.map((row, index) => ({ ...row, rank: index + 1 }));

  const now = new Date();
  const payload = {
    strategy: STRATEGY,
    schema_version: SCHEMA_VERSION,
    run_id: istRunId(now),
    as_of: istTimestamp(now),
    research_only: true,
    universe_size: sectors.length,
    processed: rows.length,
    benchmark,
    sectors: ranked,
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
    universe_size: sectors.length,
    errors: errors.length,
  };
}
