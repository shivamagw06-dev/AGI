/**
 * Scheduled Groww sector rotation research on Render.
 */

import { isGrowwConfigured } from '../providers/groww.js';
import { runGrowwSectorRotationResearch, STRATEGY } from './growwSectorRotationRun.js';

let timer = null;
let lastRun = null;
let lastIstDay = null;

async function hasSectorRotationRunToday(fetchImpl = globalThis.fetch) {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key) return false;
  const parts = istParts();
  const dayStart = `${parts.year}-${parts.month}-${parts.day}T00:00:00+05:30`;
  const response = await fetchImpl(
    `${url}/rest/v1/research_strategy_runs?strategy=eq.${STRATEGY}&as_of=gte.${encodeURIComponent(dayStart)}&select=id&limit=1`,
    { headers: { apikey: key, Authorization: `Bearer ${key}` } },
  );
  if (!response.ok) return false;
  const rows = await response.json();
  return Array.isArray(rows) && rows.length > 0;
}

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
  const raw = String(process.env.GROWW_SECTOR_ROTATION_SCHEDULE_IST || '16:35');
  const [hourText, minuteText] = raw.split(':');
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return 16 * 60 + 35;
  return hour * 60 + minute;
}

export function shouldRunSectorRotationNow(now = new Date()) {
  const parts = istParts(now);
  if (['Sat', 'Sun'].includes(parts.weekday)) return false;
  const currentMinute = Number(parts.hour) * 60 + Number(parts.minute);
  const targetMinute = parseScheduleMinutes();
  const windowMinutes = Math.max(5, Number(process.env.GROWW_SECTOR_ROTATION_WINDOW_MIN || 45) || 45);
  if (currentMinute < targetMinute || currentMinute >= targetMinute + windowMinutes) return false;
  const dayKey = `${parts.year}-${parts.month}-${parts.day}`;
  return lastIstDay !== dayKey;
}

export async function triggerGrowwSectorRotationRun({ force = false } = {}) {
  if (!force && !shouldRunSectorRotationNow()) {
    return { ok: true, skipped: true, reason: 'outside_schedule_window' };
  }
  const parts = istParts();
  lastIstDay = `${parts.year}-${parts.month}-${parts.day}`;
  const result = await runGrowwSectorRotationResearch({ force });
  lastRun = { at: new Date().toISOString(), ...result };
  console.info('[groww-sector-rotation] run complete:', result.runId, 'accepted=', result.accepted);
  return lastRun;
}

export function startGrowwSectorRotationScheduler() {
  if (timer) return;
  if (String(process.env.GROWW_SECTOR_ROTATION_SCHEDULER || 'false').toLowerCase() !== 'true') return;
  if (!isGrowwConfigured()) {
    console.warn('[groww-sector-rotation] scheduler disabled: Groww auth not configured');
    return;
  }

  const pollMs = Math.max(60_000, Number(process.env.GROWW_SECTOR_ROTATION_POLL_MS || 15 * 60_000));
  const initialDelayMs = Math.max(60_000, Number(process.env.GROWW_SECTOR_ROTATION_INITIAL_DELAY_MS || 480_000));

  const tick = () => {
    triggerGrowwSectorRotationRun().catch((error) => {
      console.warn('[groww-sector-rotation] scheduled run failed:', error?.message || error);
      lastRun = { at: new Date().toISOString(), ok: false, error: error?.message || String(error) };
    });
  };

  setTimeout(tick, initialDelayMs);
  timer = setInterval(tick, pollMs);
  timer.unref?.();

  const backfillDelayMs = Math.max(90_000, Number(process.env.GROWW_SECTOR_ROTATION_BACKFILL_DELAY_MS || 120_000));
  setTimeout(() => {
    hasSectorRotationRunToday()
      .then((hasRun) => {
        if (hasRun) return null;
        console.info('[groww-sector-rotation] no run today — startup backfill');
        return triggerGrowwSectorRotationRun({ force: true });
      })
      .catch((error) => {
        console.warn('[groww-sector-rotation] startup backfill failed:', error?.message || error);
      });
  }, backfillDelayMs);
  console.info(
    `[groww-sector-rotation] scheduler active (IST ${process.env.GROWW_SECTOR_ROTATION_SCHEDULE_IST || '16:35'}, poll ${Math.round(pollMs / 60000)}m)`
  );
}

export function getGrowwSectorRotationSchedulerStatus() {
  return {
    enabled: Boolean(timer),
    scheduleIst: process.env.GROWW_SECTOR_ROTATION_SCHEDULE_IST || '16:35',
    pollMs: Number(process.env.GROWW_SECTOR_ROTATION_POLL_MS || 15 * 60_000),
    lastRun,
    lastIstDay,
  };
}
