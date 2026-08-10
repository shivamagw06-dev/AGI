/**
 * Scheduled Groww equity-opportunity research on Render.
 *
 * Groww Cloud cannot deliver results externally; this scheduler computes the
 * same agi_equity_opportunity_v1 payload on the Node API and stores it directly.
 */

import { isGrowwConfigured } from '../providers/groww.js';
import { runGrowwEquityOpportunityResearch } from './growwEquityOpportunityRun.js';

let timer = null;
let lastRun = null;
let lastIstDay = null;

function istParts(now = new Date()) {
  return Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Kolkata',
      weekday: 'short',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
      .formatToParts(now)
      .map((part) => [part.type, part.value])
  );
}

function parseScheduleMinutes() {
  const raw = String(process.env.GROWW_EQUITY_OPPORTUNITY_SCHEDULE_IST || '16:30');
  const [hourText, minuteText] = raw.split(':');
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return 16 * 60 + 30;
  return hour * 60 + minute;
}

export function shouldRunEquityOpportunityNow(now = new Date()) {
  const parts = istParts(now);
  if (['Sat', 'Sun'].includes(parts.weekday)) return false;
  const currentMinute = Number(parts.hour) * 60 + Number(parts.minute);
  const targetMinute = parseScheduleMinutes();
  const windowMinutes = Math.max(5, Number(process.env.GROWW_EQUITY_OPPORTUNITY_WINDOW_MIN || 45) || 45);
  if (currentMinute < targetMinute || currentMinute >= targetMinute + windowMinutes) return false;
  const dayKey = `${parts.year}-${parts.month}-${parts.day}`;
  return lastIstDay !== dayKey;
}

export async function triggerGrowwEquityOpportunityRun({ force = false } = {}) {
  if (!force && !shouldRunEquityOpportunityNow()) {
    return { ok: true, skipped: true, reason: 'outside_schedule_window' };
  }
  const parts = istParts();
  lastIstDay = `${parts.year}-${parts.month}-${parts.day}`;
  const result = await runGrowwEquityOpportunityResearch({ force });
  lastRun = { at: new Date().toISOString(), ...result };
  console.info('[groww-equity-opportunity] run complete:', result.runId, 'accepted=', result.accepted);
  return lastRun;
}

export function startGrowwEquityOpportunityScheduler() {
  if (timer) return;
  if (String(process.env.GROWW_EQUITY_OPPORTUNITY_SCHEDULER || 'false').toLowerCase() !== 'true') return;
  if (!isGrowwConfigured()) {
    console.warn('[groww-equity-opportunity] scheduler disabled: Groww auth not configured');
    return;
  }

  const pollMs = Math.max(60_000, Number(process.env.GROWW_EQUITY_OPPORTUNITY_POLL_MS || 15 * 60_000));
  const initialDelayMs = Math.max(60_000, Number(process.env.GROWW_EQUITY_OPPORTUNITY_INITIAL_DELAY_MS || 420_000));

  const tick = () => {
    triggerGrowwEquityOpportunityRun().catch((error) => {
      console.warn('[groww-equity-opportunity] scheduled run failed:', error?.message || error);
      lastRun = { at: new Date().toISOString(), ok: false, error: error?.message || String(error) };
    });
  };

  setTimeout(tick, initialDelayMs);
  timer = setInterval(tick, pollMs);
  timer.unref?.();
  console.info(
    `[groww-equity-opportunity] scheduler active (IST ${process.env.GROWW_EQUITY_OPPORTUNITY_SCHEDULE_IST || '16:30'}, poll ${Math.round(pollMs / 60000)}m)`
  );
}

export function getGrowwEquityOpportunitySchedulerStatus() {
  return {
    enabled: Boolean(timer),
    scheduleIst: process.env.GROWW_EQUITY_OPPORTUNITY_SCHEDULE_IST || '16:30',
    pollMs: Number(process.env.GROWW_EQUITY_OPPORTUNITY_POLL_MS || 15 * 60_000),
    lastRun,
    lastIstDay,
  };
}
