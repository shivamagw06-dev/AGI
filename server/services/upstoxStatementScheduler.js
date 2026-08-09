/**
 * Daily post-close Upstox statement refresh.
 *
 * Statements change only on results, so this deliberately runs once after
 * market close and rotates a small, rate-safe batch through the ISIN universe.
 * It never runs on page requests and never shares the web engine process.
 */

import { refreshUpstoxFundamentals } from './upstoxFundamentalsRefresh.js';
import { tradingCalendar } from './tradingCalendarService.js';

let timer = null;
let inFlight = false;
let lastRun = null;
let lastSuccessDate = null;
let catchupRun = 0;
let lastCatchupSlot = null;

function enabled() {
  return String(process.env.UPSTOX_STATEMENT_SCHEDULER || 'true').toLowerCase() !== 'false';
}

function istParts(d = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false, weekday: 'short',
  }).formatToParts(d);
  const get = (type) => parts.find((part) => part.type === type)?.value;
  return { date: `${get('year')}-${get('month')}-${get('day')}`, hour: Number(get('hour')), minute: Number(get('minute')), weekday: get('weekday') };
}

function due(parts) {
  return tradingCalendar.isTradingDay(parts.date) && parts.hour === 18 && parts.minute >= 35;
}

function catchupConfig() {
  const intervalMinutes = Math.max(0, Number(process.env.UPSTOX_STATEMENT_CATCHUP_INTERVAL_MINUTES || 0));
  return {
    enabled: intervalMinutes > 0,
    date: String(process.env.UPSTOX_STATEMENT_CATCHUP_DATE || ''),
    intervalMinutes,
    batchSize: Math.max(1, Number(process.env.UPSTOX_STATEMENT_CATCHUP_BATCH || 4)),
  };
}

function catchupSlot(parts, config) {
  if (!config.enabled || config.date !== parts.date || ['Sat', 'Sun'].includes(String(parts.weekday || ''))) return null;
  return `${parts.date}:${Math.floor(((parts.hour * 60) + parts.minute) / config.intervalMinutes)}`;
}

function dayNumber(date) {
  return Math.floor(Date.parse(`${date}T00:00:00Z`) / 86_400_000);
}

export function getUpstoxStatementSchedulerStatus() {
  const catchup = catchupConfig();
  return {
    enabled: enabled(),
    running: Boolean(timer),
    inFlight,
    lastRun,
    lastSuccessDate,
    target: '18:35 IST weekdays',
    batchSize: Number(process.env.UPSTOX_STATEMENT_INCREMENTAL_BATCH || 12),
    catchup: {
      ...catchup,
      runningToday: Boolean(catchupSlot(istParts(), catchup)),
      completedBatches: catchupRun,
      lastSlot: lastCatchupSlot,
    },
    note: 'One small rotating batch per weekday; full statements are normalized into the warehouse.',
  };
}

export async function triggerUpstoxStatementRefresh({ force = false } = {}) {
  const now = istParts();
  const catchup = catchupConfig();
  const slot = catchupSlot(now, catchup);
  if (inFlight) return { ok: true, skipped: true, reason: 'already_running' };
  if (!force && slot && lastCatchupSlot === slot) return { ok: true, skipped: true, reason: 'already_ran_this_catchup_slot', slot };
  if (!force && !slot && lastSuccessDate === now.date) return { ok: true, skipped: true, reason: 'already_ran_today', date: now.date };
  if (!force && !slot && !due(now)) return { ok: true, skipped: true, reason: 'outside_post_close_window', now };
  inFlight = true;
  try {
    const batchSize = slot ? catchup.batchSize : Math.max(1, Number(process.env.UPSTOX_STATEMENT_INCREMENTAL_BATCH || 12));
    const result = await refreshUpstoxFundamentals({
      dataset: 'statements', limit: batchSize,
      concurrency: Math.max(1, Number(process.env.UPSTOX_STATEMENT_CONCURRENCY || 1)),
      offset: (dayNumber(now.date) * batchSize) + (slot ? catchupRun * batchSize : 0),
    });
    lastRun = { at: new Date().toISOString(), date: now.date, ok: Boolean(result.ok), fetched: result.fetched || 0, errors: (result.errors || []).length, selection: result.selection || null, error: result.error || null, catchup: Boolean(slot) };
    if (result.ok && slot) {
      lastCatchupSlot = slot;
      catchupRun += 1;
    }
    if (result.ok && !slot) lastSuccessDate = now.date;
    return { ...result, date: now.date, forced: force, catchup: Boolean(slot) };
  } catch (error) {
    lastRun = { at: new Date().toISOString(), date: now.date, ok: false, error: error.message };
    return { ok: false, error: error.message, date: now.date };
  } finally {
    inFlight = false;
  }
}

export function startUpstoxStatementScheduler() {
  if (timer || !enabled()) return getUpstoxStatementSchedulerStatus();
  const tick = () => triggerUpstoxStatementRefresh().catch(() => {});
  setTimeout(tick, 60_000);
  timer = setInterval(tick, 60_000);
  timer.unref?.();
  console.info('[upstox-statements] scheduler active — daily post-close plus optional bounded catch-up batches');
  return getUpstoxStatementSchedulerStatus();
}
