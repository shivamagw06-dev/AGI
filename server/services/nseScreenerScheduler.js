import { getNseScreenerUniverse } from './nseScreenerService.js';
import { tradingCalendar } from './tradingCalendarService.js';

let timer = null;
let lastAttemptAt = 0;
let lastSuccessDate = null;
let lastRun = null;

function istParts(now = new Date()) {
  const values = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(now).map((part) => [part.type, part.value]));
  return { date: `${values.year}-${values.month}-${values.day}`, hour: Number(values.hour), minute: Number(values.minute) };
}

export function inNseScreenerRefreshWindow(now = new Date(), isTradingDay = (date) => tradingCalendar.isTradingDay(date)) {
  const parts = istParts(now);
  return parts.hour === 16 && parts.minute >= 15 && isTradingDay(parts.date);
}

export function getNseScreenerSchedulerStatus() {
  return { enabled: Boolean(timer), target: '16:15 IST on NSE trading days', lastRun, lastSuccessDate };
}

export async function refreshNseScreenerDaily({ now = new Date(), force = false } = {}) {
  const { date } = istParts(now);
  if (!force && (!inNseScreenerRefreshWindow(now) || lastSuccessDate === date || now.getTime() - lastAttemptAt < 15 * 60 * 1000)) {
    const reason = !inNseScreenerRefreshWindow(now) ? 'outside_refresh_window' : lastSuccessDate === date ? 'already_refreshed_today' : 'retry_cooldown';
    return { skipped: true, reason };
  }
  lastAttemptAt = now.getTime();
  try {
    const result = await getNseScreenerUniverse({ force: true });
    lastRun = {
      date, at: new Date().toISOString(), ok: !result.quoteError && result.quoteCount > 0,
      instruments: result.items.length, quoted: result.quoteCount,
      error: result.quoteError || null,
    };
    if (lastRun.ok) lastSuccessDate = date;
    if (!lastRun.ok) console.warn('[nse-screeners] daily refresh incomplete:', lastRun.error || 'no quotes');
    return lastRun;
  } catch (error) {
    lastRun = { date, at: new Date().toISOString(), ok: false, error: error.message };
    console.warn('[nse-screeners] daily refresh failed:', error.message);
    return lastRun;
  }
}

export function startNseScreenerScheduler() {
  if (timer || String(process.env.NSE_SCREENER_SCHEDULER || 'true').toLowerCase() === 'false') return;
  const tick = () => { refreshNseScreenerDaily().catch((error) => console.warn('[nse-screeners] scheduler error:', error.message)); };
  timer = setInterval(tick, 5 * 60 * 1000);
  timer.unref?.();
  setTimeout(tick, 30_000).unref?.();
  console.info('[nse-screeners] daily refresh scheduled for 16:15 IST on trading days');
}
