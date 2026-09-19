import { readFileSync } from 'node:fs';
import { tradingCalendar } from './tradingCalendarService.js';

/**
 * When Live Alpha may evaluate, and when a signal was issued in a real session.
 *
 * The runtime used to evaluate on any feed batch. On a weekend or holiday the
 * feed still delivers the last traded snapshot after a restart, so the engines
 * ranked Friday's prices and stored them as Saturday's shortlist (5, 6, 12, 13,
 * 14 and 19 Sep 2026). Those lists could not be acted on and their outcomes
 * measured nothing.
 *
 * The Upstox calendar supplies holidays once it has refreshed; the committed
 * NSE list covers the time before that, or a refresh that failed.
 */

const IST_OFFSET_MS = 5.5 * 60 * 60_000;

const COMMITTED_HOLIDAYS = (() => {
  try {
    const file = JSON.parse(readFileSync(new URL('../config/nse-holidays.json', import.meta.url), 'utf8'));
    return new Set((file.holidays || []).map((row) => row.date));
  } catch {
    return new Set();
  }
})();

export function istDateKey(value) {
  return new Date(new Date(value).getTime() + IST_OFFSET_MS).toISOString().slice(0, 10);
}

/** Session bounds for the IST date of `value`, or null on a non-trading day. */
export function nseSession(value, { calendar = tradingCalendar, holidays = COMMITTED_HOLIDAYS } = {}) {
  const key = istDateKey(value);
  if (holidays.has(key)) return null;
  const session = calendar.sessionFor(key);
  if (!session) return null;
  const start = Number(session.start_time);
  const end = Number(session.end_time);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null;
  return { date: key, start, end };
}

/**
 * Whether the market is open at `now`, with a reason when it is not.
 * `leadMs` and `lagMs` widen the window, e.g. to connect a feed before 09:15.
 */
export function sessionState(now = new Date(), { leadMs = 0, lagMs = 0, ...options } = {}) {
  const at = new Date(now).getTime();
  const session = nseSession(at, options);
  if (!session) return { open: false, reason: 'market_closed_non_trading_day', session: null };
  if (at < session.start - leadMs) return { open: false, reason: 'market_closed_before_open', session };
  if (at >= session.end + lagMs) return { open: false, reason: 'market_closed_after_close', session };
  return { open: true, reason: null, session };
}

/**
 * The most recent `count` sessions that had started by `now`, newest first.
 * Looks back at most three weeks.
 */
export function recentSessions(now = new Date(), count = 10, options = {}) {
  const at = new Date(now).getTime();
  const sessions = [];
  for (let day = 0; day < 21 && sessions.length < count; day += 1) {
    const session = nseSession(at - day * 86_400_000, options);
    if (session && session.start <= at) sessions.push(session);
  }
  return sessions;
}

/** A PostgREST `or` filter matching timestamps inside the given sessions. */
export function sessionWindowsFilter(column, sessions) {
  const windows = sessions.map((session) =>
    `and(${column}.gte.${new Date(session.start).toISOString()},${column}.lte.${new Date(session.end).toISOString()})`);
  return windows.length ? `(${windows.join(',')})` : null;
}
