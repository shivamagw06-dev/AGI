/**
 * UIFI schedules — rotating fundamentals refreshes plus monthly coverage audit.
 * Daily key-ratios remain on valuationRatiosScheduler (Phase 7.4D).
 */

import { refreshUpstoxFundamentals, getUifiCoverage } from './upstoxFundamentalsRefresh.js';

let timer = null;
let lastTick = null;
let lastResult = null;

function enabled() {
  return String(process.env.UIFI_SCHEDULER || 'true').toLowerCase() !== 'false';
}

function istParts(d = new Date()) {
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour12: false,
  });
  const parts = Object.fromEntries(fmt.formatToParts(d).map((p) => [p.type, p.value]));
  return {
    weekday: parts.weekday,
    hour: Number(parts.hour),
    minute: Number(parts.minute),
    day: Number(parts.day),
    month: Number(parts.month),
    year: Number(parts.year),
  };
}

export function rotationOffset(d = new Date(), batchSize = 80, cadenceDays = 7) {
  const period = Math.floor(d.getTime() / (cadenceDays * 86_400_000));
  return period * batchSize;
}

async function runWeekly(now = new Date()) {
  const profile = await refreshUpstoxFundamentals({
    dataset: 'profile', limit: 80, offset: rotationOffset(now, 80), concurrency: 3,
  });
  const competitors = await refreshUpstoxFundamentals({
    dataset: 'competitors', limit: 60, offset: rotationOffset(now, 60), concurrency: 2,
  });
  return { profile, competitors };
}

async function runShareholding(now = new Date()) {
  return refreshUpstoxFundamentals({
    dataset: 'share-holdings', limit: 80, offset: rotationOffset(now, 80), concurrency: 2,
  });
}

async function runCorporateActions(now = new Date()) {
  return refreshUpstoxFundamentals({
    dataset: 'corporate-actions', limit: 100, offset: rotationOffset(now, 100, 1), concurrency: 3,
  });
}

async function runMonthlyAudit() {
  const coverage = await getUifiCoverage();
  return { coverage };
}

export function startUifiScheduler() {
  if (!enabled() || timer) return getUifiSchedulerStatus();
  let lastWeeklyKey = '';
  let lastOwnershipKey = '';
  let lastCorporateActionsKey = '';
  let lastMonthlyKey = '';

  timer = setInterval(async () => {
    const now = new Date();
    const p = istParts(now);
    const dateKey = `${p.year}-${p.month}-${p.day}`;
    // Sunday 08:00 IST — weekly profile + competitors
    const weeklyKey = `${dateKey}-${p.hour}`;
    if (p.weekday === 'Sun' && p.hour === 8 && weeklyKey !== lastWeeklyKey) {
      lastWeeklyKey = weeklyKey;
      lastTick = new Date().toISOString();
      try {
        lastResult = { kind: 'weekly', ...(await runWeekly(now)) };
      } catch (err) {
        lastResult = { kind: 'weekly', ok: false, error: err?.message || String(err) };
      }
    }
    // Sunday 09:00 IST — rotating shareholding coverage.
    const ownershipKey = `${dateKey}-${p.hour}`;
    if (p.weekday === 'Sun' && p.hour === 9 && ownershipKey !== lastOwnershipKey) {
      lastOwnershipKey = ownershipKey;
      lastTick = now.toISOString();
      try {
        lastResult = { kind: 'shareholding', result: await runShareholding(now) };
      } catch (err) {
        lastResult = { kind: 'shareholding', ok: false, error: err?.message || String(err) };
      }
    }
    // Weekdays 18:50 IST — rotating corporate-action coverage.
    const corporateActionsKey = `${dateKey}-${p.hour}`;
    if (p.weekday !== 'Sat' && p.weekday !== 'Sun' && p.hour === 18
        && p.minute >= 50 && corporateActionsKey !== lastCorporateActionsKey) {
      lastCorporateActionsKey = corporateActionsKey;
      lastTick = now.toISOString();
      try {
        lastResult = { kind: 'corporate-actions', result: await runCorporateActions(now) };
      } catch (err) {
        lastResult = { kind: 'corporate-actions', ok: false, error: err?.message || String(err) };
      }
    }
    // 1st of month 11:00 IST — coverage audit
    const monthlyKey = `${p.year}-${p.month}-${p.day}-${p.hour}`;
    if (p.day === 1 && p.hour === 11 && monthlyKey !== lastMonthlyKey) {
      lastMonthlyKey = monthlyKey;
      lastTick = new Date().toISOString();
      try {
        lastResult = { kind: 'monthly', ...(await runMonthlyAudit()) };
      } catch (err) {
        lastResult = { kind: 'monthly', ok: false, error: err?.message || String(err) };
      }
    }
  }, 60_000);

  if (typeof timer.unref === 'function') timer.unref();
  return getUifiSchedulerStatus();
}

export function getUifiSchedulerStatus() {
  return {
    ok: true,
    enabled: enabled(),
    running: Boolean(timer),
    schedules: {
      weekly: 'Sunday 08:00 IST — profile + competitors',
      shareholding: 'Sunday 09:00 IST — rotating shareholding coverage',
      corporate_actions: 'Weekdays 18:50 IST — rotating corporate actions',
      monthly: '1st 11:00 IST — coverage audit',
      daily_key_ratios: '18:15 IST via valuationRatiosScheduler',
    },
    lastTick,
    lastResult,
  };
}
