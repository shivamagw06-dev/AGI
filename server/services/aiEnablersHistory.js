/**
 * The basket against its benchmark since admission, one point per session.
 *
 * Daily equal weight, the same construction as the live basket: each session
 * the basket's return is the plain average of its members' close-to-close
 * returns, so weights reset every day rather than drifting.
 *
 * Membership is point-in-time. A member decided on day D enters at D's close
 * and contributes from the next session; nothing is backdated to evidence
 * that existed earlier. The series therefore starts at the first decision
 * date and is short on purpose. A line that ran back to January would be
 * pricing a basket on decisions nobody had made.
 *
 * A member is left out of a session in which it goes ex a bonus, split or
 * rights issue, because an unadjusted close-to-close return that day is the
 * share count changing, not the market. A session where a member has no
 * close is reported, and the basket that day is the average of the members
 * that do, with the count stated.
 */

import { parseActionDate } from './aiEnablersStatements.js';

const DILUTIVE = /^(bonus|split|sub-?division|rights)/i;

/** Daily closes from Upstox candle rows, oldest first, keyed by IST date. */
export function closesFrom(payload) {
  const rows = payload?.data?.candles || [];
  const out = new Map();
  for (const row of rows) {
    if (!Array.isArray(row)) continue;
    const date = String(row[0]).slice(0, 10);
    const close = Number(row[4]);
    if (/^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(close) && close > 0) out.set(date, close);
  }
  return new Map([...out.entries()].sort(([a], [b]) => (a < b ? -1 : 1)));
}

/** Ex-dates of dilutive corporate actions, as a set of YYYY-MM-DD. */
export function dilutiveExDates(payload) {
  const out = new Set();
  for (const one of payload?.data || []) {
    if (!DILUTIVE.test(String(one?.name || ''))) continue;
    // Upstox's corporate-actions rows carry the ex-date as expiry_date,
    // "18 Sep 2026", read by the same parser the live guard uses.
    const t = parseActionDate(one?.expiry_date);
    if (t !== null) out.add(new Date(t).toISOString().slice(0, 10));
  }
  return out;
}

/**
 * The daily series.
 *
 * `members`: [{ symbol, membershipStart }]
 * `closes`: { [symbol]: Map(date -> close) }
 * `benchmark`: Map(date -> close)
 * `exDates`: { [symbol]: Set(date) }
 */
export function dailyIndex({ members = [], closes = {}, benchmark = new Map(), exDates = {} } = {}) {
  const starts = members.map((one) => one.membershipStart).filter(Boolean).sort();
  if (!starts.length) return { base: null, points: [], reason: 'NO_MEMBERSHIP_DATES' };
  const base = starts[0];
  // Sessions are the benchmark's trading days: exchange holidays are not
  // missing data, and a member without a close on a trading day is.
  const sessions = [...benchmark.keys()].filter((date) => date >= base);
  if (!sessions.length || sessions[0] !== base) {
    return { base, points: [], reason: 'NO_BENCHMARK_CLOSE_ON_BASE_DATE' };
  }

  let basketLevel = 100;
  let benchLevel = 100;
  const points = [{ date: base, basket: 100, benchmark: 100, members: 0, missing: [], excluded: [] }];
  for (let i = 1; i < sessions.length; i += 1) {
    const prev = sessions[i - 1];
    const day = sessions[i];
    const returns = [];
    const missing = [];
    const excluded = [];
    for (const member of members) {
      // Entered at the close of its decision day, so it contributes only
      // to sessions after that day.
      if (!member.membershipStart || member.membershipStart > prev) continue;
      if (exDates[member.symbol]?.has(day)) { excluded.push(member.symbol); continue; }
      const c0 = closes[member.symbol]?.get(prev);
      const c1 = closes[member.symbol]?.get(day);
      if (!c0 || !c1) { missing.push(member.symbol); continue; }
      returns.push(c1 / c0 - 1);
    }
    const b0 = benchmark.get(prev);
    const b1 = benchmark.get(day);
    const basketReturn = returns.length ? returns.reduce((a, b) => a + b, 0) / returns.length : 0;
    basketLevel *= 1 + basketReturn;
    benchLevel *= 1 + (b1 / b0 - 1);
    points.push({
      date: day,
      basket: Number(basketLevel.toFixed(4)),
      benchmark: Number(benchLevel.toFixed(4)),
      members: returns.length,
      missing,
      excluded,
    });
  }
  return { base, points, reason: null };
}
