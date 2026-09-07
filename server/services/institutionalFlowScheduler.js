/**
 * Daily EOD FII/DII ingest — 18:05 IST after market close.
 * Users never call Upstox; warehouse is the only read path for the terminal.
 */

import { refreshUpstoxInstitutionalFlows } from './upstoxFlowRefresh.js';
import { tradingCalendar } from './tradingCalendarService.js';

let scheduler = null;
let lastRun = null;
let lastSuccessDate = null;

function enabled() {
  return String(process.env.INSTITUTIONAL_FLOW_SCHEDULER || 'true').toLowerCase() !== 'false';
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

function isWeekdayIST(weekday) {
  return !['Sat', 'Sun'].includes(String(weekday || ''));
}

/** Target window: 18:05–18:59 IST on weekdays (one success per calendar day). */
function inEodWindow(parts) {
  if (!isWeekdayIST(parts.weekday) || !tradingCalendar.isTradingDay(parts.date)) return false;
  if (parts.hour !== 18) return false;
  return parts.minute >= 5;
}

export function getInstitutionalFlowSchedulerStatus() {
  return {
    enabled: Boolean(scheduler),
    lastRun,
    lastSuccessDate,
    target: '18:05 IST weekdays',
    intervalMs: Number(process.env.INSTITUTIONAL_FLOW_INTERVAL_MS || 60 * 1000),
  };
}

export async function triggerInstitutionalFlowRefresh({ force = false } = {}) {
  const parts = istParts();
  if (!force && lastSuccessDate === parts.date) {
    return { ok: true, skipped: true, reason: 'already_ran_today', date: parts.date };
  }
  if (!force && !inEodWindow(parts)) {
    return { ok: true, skipped: true, reason: 'outside_eod_window', now: parts };
  }

  try {
    const result = await refreshUpstoxInstitutionalFlows();
    lastRun = {
      at: new Date().toISOString(),
      ok: Boolean(result.ok),
      status: result.status,
      date: parts.date,
      error: result.error || null,
      warehouse: result.warehouse
        ? {
            wrote: result.warehouse.wrote ?? result.warehouse.ok ?? null,
            history: result.warehouse.history ?? null,
          }
        : null,
    };
    if (result.ok) lastSuccessDate = parts.date;
    if (result.ok) {
      console.info('[institutional-flow] EOD ingest ok', parts.date);
    } else {
      console.warn('[institutional-flow] EOD ingest failed', result.error || result.status);
    }
    return { ...result, date: parts.date, forced: force };
  } catch (error) {
    lastRun = {
      at: new Date().toISOString(),
      ok: false,
      date: parts.date,
      error: error.message,
    };
    console.warn('[institutional-flow] EOD ingest error:', error.message);
    return { ok: false, error: error.message, date: parts.date };
  }
}

export function startInstitutionalFlowScheduler() {
  if (scheduler) return;
  if (!enabled()) {
    console.info('[institutional-flow] scheduler disabled (INSTITUTIONAL_FLOW_SCHEDULER=false)');
    return;
  }

  const intervalMs = Number(process.env.INSTITUTIONAL_FLOW_INTERVAL_MS || 60 * 1000);
  const tick = () => {
    triggerInstitutionalFlowRefresh().catch((error) => {
      console.warn('[institutional-flow] tick failed:', error.message);
    });
  };

  // First check after boot; then every minute around the EOD window.
  setTimeout(tick, 20_000);
  scheduler = setInterval(tick, intervalMs);
  scheduler.unref?.();
  console.info('[institutional-flow] scheduler active — target 18:05 IST weekdays');
}
