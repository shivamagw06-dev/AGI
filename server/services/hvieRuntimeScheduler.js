/**
 * HVIE Continuous Runtime — daily append tick at 18:30 IST weekdays.
 * Heavy bootstrap/append work runs on the intelligence gather worker;
 * this Node tick wakes the engine's daily/weekly/monthly slices after close.
 */

let scheduler = null;
let lastRun = null;
let lastSuccessDate = null;
let lastWeeklyDate = null;
let lastMonthlyKey = null;

function engineConfig() {
  let baseUrl = (process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) {
    baseUrl = `https://${baseUrl}`;
  }
  const token = (process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim();
  return { baseUrl, token };
}

function enabled() {
  return String(process.env.HVIE_RUNTIME_SCHEDULER || 'true').toLowerCase() !== 'false';
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

function inDailyWindow(parts) {
  if (['Sat', 'Sun'].includes(String(parts.weekday || ''))) return false;
  if (parts.hour !== 18) return false;
  return parts.minute >= 30;
}

function inWeeklyWindow(parts) {
  return parts.weekday === 'Sun' && parts.hour === 9 && parts.minute < 30;
}

function inMonthlyWindow(parts) {
  return String(parts.date || '').endsWith('-01') && parts.hour === 10 && parts.minute < 30;
}

async function enginePost(path, body = {}) {
  const { baseUrl, token } = engineConfig();
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(180_000),
  });
  const data = await response.json().catch(() => ({}));
  return { ok: response.ok, status: response.status, data };
}

export function getHvieRuntimeSchedulerStatus() {
  return {
    enabled: Boolean(scheduler),
    lastRun,
    lastSuccessDate,
    lastWeeklyDate,
    lastMonthlyKey,
    target: '18:30 IST weekdays (daily); Sun 09:00 (weekly); 1st 10:00 (monthly)',
    intervalMs: Number(process.env.HVIE_RUNTIME_INTERVAL_MS || 60 * 1000),
  };
}

export async function triggerHvieRuntime({ force = false, mode } = {}) {
  const parts = istParts();
  let chosen = mode;
  if (!chosen) {
    if (inMonthlyWindow(parts) && lastMonthlyKey !== parts.date) chosen = 'monthly';
    else if (inWeeklyWindow(parts) && lastWeeklyDate !== parts.date) chosen = 'weekly';
    else if (inDailyWindow(parts)) chosen = 'daily';
    else if (force) chosen = 'daily';
    else return { ok: true, skipped: true, reason: 'outside_hvie_windows', now: parts };
  }

  if (!force && chosen === 'daily' && lastSuccessDate === parts.date) {
    return { ok: true, skipped: true, reason: 'already_ran_today', date: parts.date };
  }

  try {
    const batch = Number(
      chosen === 'daily'
        ? process.env.HVIE_DAILY_BATCH || 120
        : process.env.HVIE_WEEKLY_BATCH || 60,
    );
    const r = await enginePost('/v1/historical-valuation/runtime/run', { mode: chosen, batch });
    const data = r.data || {};
    const ok = Boolean(r.ok && (data.ok !== false));
    lastRun = {
      at: new Date().toISOString(),
      ok,
      mode: chosen,
      date: parts.date,
      result: data,
    };
    if (ok && chosen === 'daily') lastSuccessDate = parts.date;
    if (ok && chosen === 'weekly') lastWeeklyDate = parts.date;
    if (ok && chosen === 'monthly') lastMonthlyKey = parts.date;
    if (ok) console.info('[hvie-runtime] tick ok', chosen, parts.date);
    else console.warn('[hvie-runtime] tick failed', chosen, data.error || r.status);
    return { ...data, ok, mode: chosen, date: parts.date, forced: force };
  } catch (error) {
    lastRun = {
      at: new Date().toISOString(),
      ok: false,
      mode: chosen,
      date: parts.date,
      error: error.message,
    };
    console.warn('[hvie-runtime] tick error:', error.message);
    return { ok: false, error: error.message, mode: chosen, date: parts.date };
  }
}

export function startHvieRuntimeScheduler() {
  if (scheduler) return;
  if (!enabled()) {
    console.info('[hvie-runtime] scheduler disabled (HVIE_RUNTIME_SCHEDULER=false)');
    return;
  }
  const intervalMs = Number(process.env.HVIE_RUNTIME_INTERVAL_MS || 60 * 1000);
  const tick = () => {
    triggerHvieRuntime().catch((error) => {
      console.warn('[hvie-runtime] tick failed:', error.message);
    });
  };
  setTimeout(tick, 60_000);
  scheduler = setInterval(tick, intervalMs);
  scheduler.unref?.();
  console.info('[hvie-runtime] scheduler active — 18:30 IST daily / weekly / monthly');
}
