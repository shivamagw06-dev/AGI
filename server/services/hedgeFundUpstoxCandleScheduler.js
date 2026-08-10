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

let timer = null;
let inFlight = null;
let lastRun = null;
let lastDailyRefresh = null;

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

function isoIstDate(now = new Date()) {
  const p = istParts(now);
  return `${p.year}-${p.month}-${p.day}`;
}

function dateDaysAgo(days, now = new Date()) {
  const date = new Date(now.getTime() - days * 86_400_000);
  return date.toISOString().slice(0, 10);
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
  const staged = await engineFetch('/v1/warehouse/tab/daily_market_history/import', {
    method: 'POST', body: { rows, actor: 'hedge_fund_upstox_candles', source: 'upstox_v3' }, timeoutMs: 90_000,
  });
  if (!staged.import_id) throw new Error(staged.error || 'upstox_candle_stage_failed');
  return engineFetch(`/v1/warehouse/import/${staged.import_id}/commit`, {
    method: 'POST', body: { actor: 'hedge_fund_upstox_candles', recalculate: false }, timeoutMs: 90_000,
  });
}

async function refreshDaily(candidates, today) {
  let rowsWritten = 0;
  let refreshed = 0;
  const failures = [];
  for (const candidate of candidates) {
    try {
      const payload = await getHistoricalCandles(candidate.instrumentKey, { unit: 'days', interval: 1, from: dateDaysAgo(400), to: today });
      const rows = candleRows(candidate.ticker, payload, 'upstox_v3_daily');
      await importRows(rows);
      await engineFetch('/v1/warehouse/recalculate', { method: 'POST', body: { actor: 'hedge_fund_upstox_candles', stages: ['factors'], entity: candidate.ticker }, timeoutMs: 90_000 });
      rowsWritten += rows.length;
      refreshed += 1;
    } catch (error) {
      failures.push({ ticker: candidate.ticker, error: error.message });
    }
  }
  return { refreshed, rowsWritten, failures };
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
    const terminal = await engineFetch('/v1/hedge-fund-lab/terminal?limit=24', { timeoutMs: 45_000 });
    const candidates = candidateRows(terminal);
    if (!candidates.length) return { ok: true, skipped: true, reason: 'no_instrument_keys' };
    const shouldRunDaily = force || (!marketOpen() && lastDailyRefresh !== today);
    const daily = shouldRunDaily ? await refreshDaily(candidates, today) : null;
    if (shouldRunDaily) lastDailyRefresh = today;
    const intraday = marketOpen() ? await refreshIntraday(candidates) : null;
    return { ok: true, provider: 'upstox_v3', candidates: candidates.length, daily, intraday, as_of: new Date().toISOString() };
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
  const tick = () => refreshHedgeFundUpstoxCandles().then((result) => { lastRun = result; }).catch((error) => { lastRun = { ok: false, error: error.message, at: new Date().toISOString() }; });
  setTimeout(tick, Math.max(60_000, Number(process.env.HEDGE_FUND_UPSTOX_INITIAL_DELAY_MS || 180_000)));
  timer = setInterval(tick, intervalMs);
  timer.unref?.();
}

export function getHedgeFundUpstoxCandleStatus() {
  return { enabled: Boolean(timer), provider: 'upstox_v3', intervalMs: Number(process.env.HEDGE_FUND_UPSTOX_CANDLE_INTERVAL_MS || 15 * 60_000), marketOpen: marketOpen(), lastRun };
}
