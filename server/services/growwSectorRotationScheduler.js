/**
 * Scheduled Groww sector rotation research on Render.
 */

import { isGrowwConfigured } from '../providers/groww.js';
import { runGrowwSectorRotationResearch, STRATEGY } from './growwSectorRotationRun.js';
import { activeHourlySlot, hasStoredStrategyRunInSlot } from './growwHourlySchedule.js';

let timer = null;
let lastRun = null;
let lastSlotKey = null;
let activeSlotKey = null;
const DEFAULT_SLOTS = '10:05,11:05,12:05,13:05,14:05,15:05,16:35';

export function shouldRunSectorRotationNow(now = new Date()) {
  const slot = activeHourlySlot({ now, rawSlots: process.env.GROWW_SECTOR_ROTATION_SLOTS_IST, fallbackSlots: DEFAULT_SLOTS, windowMinutes: Math.max(5, Number(process.env.GROWW_SECTOR_ROTATION_WINDOW_MIN || 20) || 20) });
  return Boolean(slot && slot.key !== lastSlotKey);
}

export async function triggerGrowwSectorRotationRun({ force = false } = {}) {
  const now = new Date();
  const slot = activeHourlySlot({ now, rawSlots: process.env.GROWW_SECTOR_ROTATION_SLOTS_IST, fallbackSlots: DEFAULT_SLOTS, windowMinutes: Math.max(5, Number(process.env.GROWW_SECTOR_ROTATION_WINDOW_MIN || 20) || 20) });
  if (!force && (!slot || slot.key === lastSlotKey || slot.key === activeSlotKey)) {
    return { ok: true, skipped: true, reason: 'outside_schedule_window' };
  }
  if (!force && await hasStoredStrategyRunInSlot(STRATEGY, slot)) {
    lastSlotKey = slot.key;
    return { ok: true, skipped: true, reason: 'slot_already_stored', slot: slot.key };
  }
  if (slot) activeSlotKey = slot.key;
  try {
    const result = await runGrowwSectorRotationResearch({ force });
    if (slot) lastSlotKey = slot.key;
    lastRun = { at: new Date().toISOString(), slot: slot?.key || 'manual', ...result };
    console.info('[groww-sector-rotation] run complete:', result.runId, 'accepted=', result.accepted);
    return lastRun;
  } finally {
    if (slot?.key === activeSlotKey) activeSlotKey = null;
  }
}

export function startGrowwSectorRotationScheduler() {
  if (timer) return;
  if (String(process.env.GROWW_SECTOR_ROTATION_SCHEDULER || 'false').toLowerCase() !== 'true') return;
  if (!isGrowwConfigured()) {
    console.warn('[groww-sector-rotation] scheduler disabled: Groww auth not configured');
    return;
  }

  const pollMs = Math.max(60_000, Number(process.env.GROWW_SECTOR_ROTATION_POLL_MS || 5 * 60_000));
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

  console.info(
    `[groww-sector-rotation] hourly scheduler active (IST ${process.env.GROWW_SECTOR_ROTATION_SLOTS_IST || DEFAULT_SLOTS}, poll ${Math.round(pollMs / 60000)}m)`
  );
}

export function getGrowwSectorRotationSchedulerStatus() {
  return {
    enabled: Boolean(timer),
    scheduleIst: process.env.GROWW_SECTOR_ROTATION_SLOTS_IST || DEFAULT_SLOTS,
    pollMs: Number(process.env.GROWW_SECTOR_ROTATION_POLL_MS || 5 * 60_000),
    lastRun,
    lastSlotKey,
    activeSlotKey,
  };
}
