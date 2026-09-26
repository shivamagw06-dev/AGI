/**
 * Daily EOD Upstox valuation ratios refresh — 18:15 IST weekdays
 * (after FII/DII at 18:05, before warehouse refresh ~18:45).
 */

import { refreshUpstoxValuationRatios } from './upstoxValuationRatiosRefresh.js';
import { tradingCalendar } from './tradingCalendarService.js';

let scheduler = null;
let lastRun = null;
let lastSuccessDate = null;

function enabled() {
  return String(process.env.VALUATION_RATIOS_SCHEDULER || 'true').toLowerCase() !== 'false';
}

function istParts(d = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    weekday: 'short',
  }).formatToParts(d);
  const get = (type) => parts.find((p) => p.type === type)?.value;
  return {
    date: `${get('year')}-${get('month')}-${get('day')}`,
    hour: Number(get('hour')),
    minute: Number(get('minute')),
    weekday: get('weekday'),
  };
}

function inEodWindow(parts) {
  if (['Sat', 'Sun'].includes(String(parts.weekday || '')) || !tradingCalendar.isTradingDay(parts.date)) return false;
  // 18:15–18:59 IST
  if (parts.hour !== 18) return false;
  return parts.minute >= 15;
}

export function getValuationRatiosSchedulerStatus() {
  return {
    enabled: Boolean(scheduler),
    lastRun,
    lastSuccessDate,
    target: '18:15 IST weekdays',
    intervalMs: Number(process.env.VALUATION_RATIOS_INTERVAL_MS || 60 * 1000),
  };
}

export async function triggerValuationRatiosRefresh({ force = false } = {}) {
  const parts = istParts();
  if (!force && lastSuccessDate === parts.date) {
    return { ok: true, skipped: true, reason: 'already_ran_today', date: parts.date };
  }
  if (!force && !inEodWindow(parts)) {
    return { ok: true, skipped: true, reason: 'outside_eod_window', now: parts };
  }

  try {
    // Never compete with the one-shot full-universe bootstrap (Phase 7.4d).
    const { isUpstoxBootstrapRunning } = await import('./upstoxBootstrapEngine.js');
    if (!force && isUpstoxBootstrapRunning()) {
      return { ok: true, skipped: true, reason: 'bootstrap_running', date: parts.date };
    }

    // Nightly = incremental maintenance only (small batch), not universe bootstrap.
    const incrementalLimit = Number(process.env.UPSTOX_VALUATION_INCREMENTAL_BATCH || 80);
    const result = await refreshUpstoxValuationRatios({
      limit: incrementalLimit,
      concurrency: Number(process.env.UPSTOX_VALUATION_CONCURRENCY || 3),
    });
    lastRun = {
      at: new Date().toISOString(),
      ok: Boolean(result.ok),
      status: result.status,
      date: parts.date,
      fetched: result.fetched ?? 0,
      failed: result.failed ?? 0,
      selection: result.selection
        ? {
            universeSize: result.selection.universeSize,
            offset: result.selection.offset,
            batchSize: result.selection.batchSize,
          }
        : null,
      error: result.error || null,
    };
    if (result.ok) lastSuccessDate = parts.date;
    if (result.ok) {
      console.info('[valuation-ratios] EOD ingest ok', parts.date, `fetched=${result.fetched}`);
    } else {
      console.warn('[valuation-ratios] EOD ingest failed', result.error || result.status);
    }
    return { ...result, date: parts.date, forced: force };
  } catch (error) {
    lastRun = {
      at: new Date().toISOString(),
      ok: false,
      date: parts.date,
      error: error.message,
    };
    console.warn('[valuation-ratios] EOD ingest error:', error.message);
    return { ok: false, error: error.message, date: parts.date };
  }
}

export function startValuationRatiosScheduler() {
  if (scheduler) return;
  if (!enabled()) {
    console.info('[valuation-ratios] scheduler disabled (VALUATION_RATIOS_SCHEDULER=false)');
    return;
  }
  const intervalMs = Number(process.env.VALUATION_RATIOS_INTERVAL_MS || 60 * 1000);
  const tick = () => {
    triggerValuationRatiosRefresh().catch((error) => {
      console.warn('[valuation-ratios] tick failed:', error.message);
    });
  };
  setTimeout(tick, 45_000);
  scheduler = setInterval(tick, intervalMs);
  scheduler.unref?.();
  console.info('[valuation-ratios] scheduler active — target 18:15 IST weekdays');
}
