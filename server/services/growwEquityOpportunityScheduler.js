/**
 * Scheduled Groww equity-opportunity research on Render.
 *
 * Groww Cloud cannot deliver results externally; this scheduler computes the
 * same agi_equity_opportunity_v1 payload on the Node API and stores it directly.
 */

import { isGrowwConfigured } from '../providers/groww.js';
import { runGrowwEquityOpportunityResearch, STRATEGY } from './growwEquityOpportunityRun.js';
import { activeHourlySlot, hasStoredStrategyRunInSlot } from './growwHourlySchedule.js';

let timer = null;
let lastRun = null;
let lastSlotKey = null;
let activeSlotKey = null;
const DEFAULT_SLOTS = '10:00,11:00,12:00,13:00,14:00,15:00,16:30';

export function shouldRunEquityOpportunityNow(now = new Date()) {
  const slot = activeHourlySlot({ now, rawSlots: process.env.GROWW_EQUITY_OPPORTUNITY_SLOTS_IST, fallbackSlots: DEFAULT_SLOTS, windowMinutes: Math.max(5, Number(process.env.GROWW_EQUITY_OPPORTUNITY_WINDOW_MIN || 20) || 20) });
  return Boolean(slot && slot.key !== lastSlotKey);
}

export async function triggerGrowwEquityOpportunityRun({ force = false } = {}) {
  const now = new Date();
  const slot = activeHourlySlot({ now, rawSlots: process.env.GROWW_EQUITY_OPPORTUNITY_SLOTS_IST, fallbackSlots: DEFAULT_SLOTS, windowMinutes: Math.max(5, Number(process.env.GROWW_EQUITY_OPPORTUNITY_WINDOW_MIN || 20) || 20) });
  if (!force && (!slot || slot.key === lastSlotKey || slot.key === activeSlotKey)) {
    return { ok: true, skipped: true, reason: 'outside_schedule_window' };
  }
  if (!force && await hasStoredStrategyRunInSlot(STRATEGY, slot)) {
    lastSlotKey = slot.key;
    return { ok: true, skipped: true, reason: 'slot_already_stored', slot: slot.key };
  }
  if (slot) activeSlotKey = slot.key;
  try {
    const result = await runGrowwEquityOpportunityResearch({ force });
    if (slot) lastSlotKey = slot.key;
    lastRun = { at: new Date().toISOString(), slot: slot?.key || 'manual', ...result };
    console.info('[groww-equity-opportunity] run complete:', result.runId, 'accepted=', result.accepted);
    return lastRun;
  } finally {
    if (slot?.key === activeSlotKey) activeSlotKey = null;
  }
}

export function startGrowwEquityOpportunityScheduler() {
  if (timer) return;
  if (String(process.env.GROWW_EQUITY_OPPORTUNITY_SCHEDULER || 'false').toLowerCase() !== 'true') return;
  if (!isGrowwConfigured()) {
    console.warn('[groww-equity-opportunity] scheduler disabled: Groww auth not configured');
    return;
  }

  const pollMs = Math.max(60_000, Number(process.env.GROWW_EQUITY_OPPORTUNITY_POLL_MS || 5 * 60_000));
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
    `[groww-equity-opportunity] hourly scheduler active (IST ${process.env.GROWW_EQUITY_OPPORTUNITY_SLOTS_IST || DEFAULT_SLOTS}, poll ${Math.round(pollMs / 60000)}m)`
  );
}

export function getGrowwEquityOpportunitySchedulerStatus() {
  return {
    enabled: Boolean(timer),
    scheduleIst: process.env.GROWW_EQUITY_OPPORTUNITY_SLOTS_IST || DEFAULT_SLOTS,
    pollMs: Number(process.env.GROWW_EQUITY_OPPORTUNITY_POLL_MS || 5 * 60_000),
    lastRun,
    lastSlotKey,
    activeSlotKey,
  };
}
