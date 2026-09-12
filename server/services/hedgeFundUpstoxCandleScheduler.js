/**
 * Upstox-backed price maintenance for the Hedge Fund research queue.
 *
 * This deliberately refreshes a small, evidence-ranked queue rather than the
 * full listed universe every few minutes. The full-universe technical model is
 * calculated after close from the warehouse; intraday candles are an overlay
 * used to keep active research candidates current without exhausting provider
 * limits or making a page visit perform vendor work.
 */
import { getHistoricalCandles, getIntradayCandles, isUpstoxConfigured } from '../providers/upstox.js';
import { readLatestHflTerminalSnapshot } from './hflTerminalSnapshot.js';
import { loadLiveAlphaUniverse } from './liveAlphaRuntime.js';
import { tradingCalendar } from './tradingCalendarService.js';

let timer = null;
let retryTimer = null;
let inFlight = null;
let lastRun = null;
let lastDailyRefresh = null;
let dailyProgress = { date: null, covered: new Set() };

function engineConfig() {
  let baseUrl = String(process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  return { baseUrl, token: String(process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim() };
}

async function engineFetch(path, { method = 'GET', body, timeoutMs = 60_000 } = {}) {
  const { baseUrl, token } = engineConfig();
  if (!baseUrl || !token) throw new Error('intelligence_engine_not_configured');
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, 'X-AGI-Intelligence-Token': token },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.error || data?.detail || `engine_http_${response.status}`);
  return data;
}

function istParts(now = new Date()) {
  return Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata', weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(now).map((part) => [part.type, part.value]));
}

function marketOpen(now = new Date()) {
  const p = istParts(now);
  if (['Sat', 'Sun'].includes(p.weekday)) return false;
  const minute = Number(p.hour) * 60 + Number(p.minute);
  return minute >= 9 * 60 + 15 && minute <= 15 * 60 + 30;
}

export function afterMarketClose(now = new Date()) {
  const p = istParts(now);
  if (['Sat', 'Sun'].includes(p.weekday)) return false;
  return Number(p.hour) * 60 + Number(p.minute) >= 15 * 60 + 45;
}

export function dailyCoveragePassed(daily, universeSize) {
  const minimumCoverage = Math.ceil(Number(universeSize || 0) * 0.80);
  return minimumCoverage > 0 && Number(daily?.latest_session_coverage || 0) >= minimumCoverage;
}

function isoIstDate(now = new Date()) {
  const p = istParts(now);
  return `${p.year}-${p.month}-${p.day}`;
}

export function latestCompletedTradingSession(now = new Date()) {
  const today = isoIstDate(now);
  if (tradingCalendar.isTradingDay(today, 'NSE') && afterMarketClose(now)) return today;
  return isoIstDate(tradingCalendar.previousTradingDay(now, 'NSE'));
}

function dateDaysAgo(days, now = new Date()) {
  const date = new Date(now.getTime() - days * 86_400_000);
  return date.toISOString().slice(0, 10);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function candidateRows(pack) {
  const seen = new Set();
  const output = [];
  const visit = (row) => {
    const ticker = String(row?.ticker || '').toUpperCase();
    const instrumentKey = String(row?.instrument_key || '').trim();
    if (!ticker || !instrumentKey.includes('|') || seen.has(ticker)) return;
    seen.add(ticker);
    output.push({ ticker, instrumentKey });
  };
  for (const row of pack?.research_queue || []) visit(row);
  for (const row of pack?.overlap || []) visit(row);
  for (const hit of pack?.hero?.highlights || []) visit(hit?.row);
  return output.slice(0, Math.max(1, Number(process.env.HEDGE_FUND_UPSTOX_CANDLE_LIMIT || 25)));
}

function candleRows(ticker, payload, source) {
  const candles = payload?.data?.candles || [];
  return candles.map((candle) => {
    const [timestamp, open, high, low, close, volume] = candle || [];
    const date = String(timestamp || '').slice(0, 10);
    if (!date || !Number.isFinite(Number(close)) || Number(close) <= 0) return null;
    return { symbol: ticker, date, open: Number(open) || null, high: Number(high) || null, low: Number(low) || null, close: Number(close), volume: Number(volume) || null, source, import_time: new Date().toISOString() };
  }).filter(Boolean);
}

async function importRows(rows) {
  if (!rows.length) return { ok: true, written: 0 };
  let written = 0;
  const chunks = [];
  const chunkSize = Math.max(100, Number(process.env.HEDGE_FUND_UPSTOX_IMPORT_CHUNK_SIZE || 750));
  for (let index = 0; index < rows.length; index += chunkSize) {
    const chunk = rows.slice(index, index + chunkSize);
    const staged = await engineFetch('/v1/warehouse/tab/daily_market_history/import', {
      method: 'POST', body: { rows: chunk, actor: 'hedge_fund_upstox_candles', source: 'upstox_v3' }, timeoutMs: 90_000,
    });
    if (!staged.import_id) throw new Error(staged.error || 'upstox_candle_stage_failed');
    const committed = await engineFetch(`/v1/warehouse/import/${staged.import_id}/commit`, {
      method: 'POST', body: { actor: 'hedge_fund_upstox_candles', recalculate: false }, timeoutMs: 90_000,
    });
    written += Number(committed?.inserted ?? committed?.written ?? chunk.length);
    chunks.push({ rows: chunk.length, import_id: staged.import_id, ok: committed?.ok !== false });
  }
  return { ok: true, written, chunks };
}

async function refreshDaily(candidates, targetSession, today) {
  const collected = [];
  const failures = [];
  const overlayFailures = [];
  const concurrency = Math.max(1, Math.min(2, Number(process.env.HEDGE_FUND_UPSTOX_EOD_CONCURRENCY || 1)));
  const requestPauseMs = Math.max(100, Number(process.env.HEDGE_FUND_UPSTOX_EOD_REQUEST_PAUSE_MS || 350));
  let rateLimited = false;
  let cursor = 0;
  const worker = async () => {
    while (cursor < candidates.length && !rateLimited) {
      const candidate = candidates[cursor++];
      try {
        // Upstox historical candles generally stop at the previous completed
        // day. The documented V3 intraday endpoint with days/1 supplies the
        // current trading day's consolidated OHLCV candle. Try it first so the
        // normal daily path needs only one provider call per instrument.
        const byDate = new Map();
        try {
          if (targetSession === today) {
            const currentPayload = await getIntradayCandles(candidate.instrumentKey, { unit: 'days', interval: 1 });
            const currentRows = candleRows(candidate.ticker, currentPayload, 'upstox_v3_current_day').filter((row) => row.date === targetSession);
            if (!currentRows.length) throw new Error('current_day_candle_missing');
            for (const row of currentRows) byDate.set(row.date, row);
          }
        } catch (error) {
          overlayFailures.push({ ticker: candidate.ticker, error: error.message });
          if (error?.status === 429) throw error;
        }
        if (!byDate.has(targetSession)) {
          // Repair missed sessions from a short historical overlap. Existing
          // 10-year warehouse history remains untouched.
          const payload = await getHistoricalCandles(candidate.instrumentKey, { unit: 'days', interval: 1, from: dateDaysAgo(10), to: today });
          const historicalRows = candleRows(candidate.ticker, payload, 'upstox_v3_daily').filter((row) => row.date <= targetSession);
          if (!historicalRows.length) throw new Error('no_daily_candles_returned');
          for (const row of historicalRows) byDate.set(row.date, row);
        }
        collected.push(...byDate.values());
      } catch (error) {
        failures.push({ ticker: candidate.ticker, error: error.message });
        if (error?.status === 429) rateLimited = true;
      }
      if (!rateLimited) await sleep(requestPauseMs);
    }
  };
  await Promise.all(Array.from({ length: concurrency }, worker));
  const imported = await importRows(collected);
  const refreshedSymbols = new Set(collected.map((row) => row.symbol));
  const latestCoverage = new Set(collected.filter((row) => row.date === targetSession).map((row) => row.symbol));
  return {
    requested: candidates.length,
    refreshed: refreshedSymbols.size,
    latest_session_coverage: latestCoverage.size,
    rowsWritten: collected.length,
    imported,
    failures,
    overlayFailures,
    rate_limited: rateLimited,
    successful_today: [...latestCoverage],
  };
}

async function refreshIntraday(candidates) {
  const failures = [];
  let rowsWritten = 0;
  for (const candidate of candidates) {
    try {
      const payload = await getIntradayCandles(candidate.instrumentKey, { unit: 'minutes', interval: 15 });
      const rows = candleRows(candidate.ticker, payload, 'upstox_v3_intraday');
      await importRows(rows);
      rowsWritten += rows.length;
    } catch (error) {
      failures.push({ ticker: candidate.ticker, error: error.message });
    }
  }
  return { rowsWritten, failures };
}

export async function refreshHedgeFundUpstoxCandles({ force = false } = {}) {
  if (!isUpstoxConfigured()) return { ok: false, skipped: true, reason: 'upstox_not_configured' };
  if (inFlight) return { ok: true, skipped: true, reason: 'refresh_in_flight' };
  inFlight = (async () => {
    const today = isoIstDate();
    const targetSession = latestCompletedTradingSession();
    // Prefer Supabase snapshot so candle refresh does not rebuild scanners.
    let terminal = null;
    try {
      terminal = await readLatestHflTerminalSnapshot();
    } catch {
      terminal = null;
    }
    if (!terminal?.ok) {
      try {
        const latest = await engineFetch('/v1/hedge-fund-lab/terminal/snapshot/latest', { timeoutMs: 20_000 });
        terminal = latest?.payload || null;
      } catch {
        terminal = null;
      }
    }
    // The full-universe EOD repair is independent from the terminal snapshot.
    // Only intraday candidate overlays require a current Hedge Fund queue.
    const candidates = terminal?.ok ? candidateRows(terminal) : [];
    const fullUniverse = await loadLiveAlphaUniverse();
    const dailyCandidates = fullUniverse.members.map((member) => ({ ticker: member.symbol, instrumentKey: member.instrumentKey }));
    if (dailyProgress.date !== targetSession) dailyProgress = { date: targetSession, covered: new Set() };
    // Catch up the latest completed NSE session even on weekends or before the
    // next open. Rate limits and deploys must not strand a partial EOD universe.
    const shouldRunDaily = force || lastDailyRefresh !== targetSession;
    const pendingDailyCandidates = dailyCandidates.filter((candidate) => !dailyProgress.covered.has(candidate.ticker));
    const daily = shouldRunDaily && pendingDailyCandidates.length ? await refreshDaily(pendingDailyCandidates, targetSession, today) : null;
    for (const ticker of daily?.successful_today || []) dailyProgress.covered.add(ticker);
    const minimumCoverage = Math.ceil(dailyCandidates.length * 0.80);
    // A partial provider run must retry; it must never mark the EOD session done.
    const cumulativeCoverage = dailyProgress.covered.size;
    const eodRetryRequired = shouldRunDaily && cumulativeCoverage < minimumCoverage;
    if (shouldRunDaily && !eodRetryRequired) lastDailyRefresh = targetSession;
    const intraday = marketOpen() && candidates.length ? await refreshIntraday(candidates) : null;
    return { ok: true, provider: 'upstox_v3', candidates: candidates.length, target_session: targetSession, eod_universe: dailyCandidates.length, eod_minimum_coverage: minimumCoverage, eod_cumulative_coverage: cumulativeCoverage, eod_pending: dailyCandidates.length - cumulativeCoverage, eod_retry_required: eodRetryRequired, daily, intraday, as_of: new Date().toISOString() };
  })();
  try { return await inFlight; } finally { inFlight = null; }
}

export function startHedgeFundUpstoxCandleScheduler() {
  // Technical research is paused while Hedge Fund runs fundamentals-first.
  // Retain this scheduler and the raw candles for a future opt-in, but do not
  // run it merely because the old candle setting is still present.
  if (
    timer ||
    String(process.env.HEDGE_FUND_TECHNICAL_RESEARCH_ENABLED || 'true').toLowerCase() !== 'true' ||
    String(process.env.HEDGE_FUND_UPSTOX_CANDLES || 'true').toLowerCase() !== 'true'
  ) return;
  const intervalMs = Math.max(15 * 60_000, Number(process.env.HEDGE_FUND_UPSTOX_CANDLE_INTERVAL_MS || 15 * 60_000));
  const tick = () => refreshHedgeFundUpstoxCandles().then((result) => {
    lastRun = result;
    if (result?.eod_retry_required && !retryTimer) {
      retryTimer = setTimeout(() => { retryTimer = null; tick(); }, Math.max(5 * 60_000, Number(process.env.HEDGE_FUND_UPSTOX_EOD_RETRY_MS || 15 * 60_000)));
      retryTimer.unref?.();
    }
  }).catch((error) => { lastRun = { ok: false, error: error.message, at: new Date().toISOString() }; });
  // Stagger after HFL snapshot scheduler (default 2m) so Python is not woken twice.
  setTimeout(tick, Math.max(60_000, Number(process.env.HEDGE_FUND_UPSTOX_INITIAL_DELAY_MS || 120_000)));
  timer = setInterval(tick, intervalMs);
  timer.unref?.();
}

export function getHedgeFundUpstoxCandleStatus() {
  return { enabled: Boolean(timer), provider: 'upstox_v3', intervalMs: Number(process.env.HEDGE_FUND_UPSTOX_CANDLE_INTERVAL_MS || 15 * 60_000), marketOpen: marketOpen(), afterMarketClose: afterMarketClose(), retryScheduled: Boolean(retryTimer), lastDailyRefresh, lastRun };
}
