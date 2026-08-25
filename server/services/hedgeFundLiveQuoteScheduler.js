/**
 * Rate-limited Groww price refresh for the Hedge Fund research universe.
 *
 * This intentionally follows candidates, not every listed company. EOD
 * fundamentals belong to Upstox/the warehouse; during-market price freshness
 * belongs to Groww. Quotes are committed to the existing append-only daily
 * market history table, retaining the latest version and provenance.
 *
 * Keep this light: never rebuild a large terminal scan here. Page opens and
 * keep-warm share the same engine process — a limit=60 terminal + warehouse
 * import was competing with user traffic and causing 502s.
 */
import { getLTP, getOHLC, isGrowwConfigured } from '../providers/groww.js';
import { readLatestHflTerminalSnapshot } from './hflTerminalSnapshot.js';
import { LiveAlphaPersistence } from './liveAlphaPersistence.js';

let timer = null;
let lastRun = null;
let inFlight = null;

function engineConfig() {
  let baseUrl = String(process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  return { baseUrl, token: String(process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim() };
}

function marketOpen(now = new Date()) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(now).map((part) => [part.type, part.value]));
  if (['Sat', 'Sun'].includes(parts.weekday)) return false;
  const minute = Number(parts.hour) * 60 + Number(parts.minute);
  return minute >= 9 * 60 + 15 && minute <= 15 * 60 + 30;
}

async function engineFetch(path, { method = 'GET', body, timeoutMs = 45_000 } = {}) {
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

function addCandidate(out, seen, ticker, instrumentKey) {
  const symbol = String(ticker || '').trim().toUpperCase();
  if (!symbol || seen.has(symbol)) return;
  seen.add(symbol);
  out.push({ symbol, instrument_key: String(instrumentKey || '').trim() || null });
}

function symbolsFromTerminal(pack) {
  const out = [];
  const seen = new Set();
  const addRow = (row) => {
    if (!row || typeof row !== 'object') return;
    addCandidate(out, seen, row.ticker || row.symbol, row.instrument_key);
    addCandidate(out, seen, row.long_leg?.ticker, row.long_leg?.instrument_key);
    addCandidate(out, seen, row.short_leg?.ticker, row.short_leg?.instrument_key);
  };
  for (const card of pack?.cards || []) {
    for (const row of card?.results || []) addRow(row);
  }
  for (const row of [...(pack?.research_queue || []), ...(pack?.overlap || [])]) addRow(row);
  for (const hit of pack?.hero?.highlights || []) addRow(hit?.row);
  return out.slice(0, Number(process.env.HEDGE_FUND_LIVE_QUOTE_LIMIT || 50));
}

function quoteValue(map, key) {
  const value = map?.[key];
  return value && typeof value === 'object' ? value.ltp ?? value.last_price ?? value.lastPrice ?? value.close : value;
}

function ohlcValue(map, key) {
  const value = map?.[key];
  if (!value) return {};
  if (typeof value === 'object') return value;
  try { return JSON.parse(value); } catch { return {}; }
}

function candlePrevious(map, key) {
  const candle = ohlcValue(map, key);
  const previous = Number(candle.previous_close ?? candle.prev_close ?? candle.close);
  return Number.isFinite(previous) && previous > 0 ? previous : null;
}

async function commitQuotes(rows) {
  if (!rows.length) return { ok: true, written: 0 };
  const staged = await engineFetch('/v1/warehouse/tab/daily_market_history/import', {
    method: 'POST',
    body: { rows, actor: 'hedge_fund_groww_quotes', source: 'groww' },
    timeoutMs: 60_000,
  });
  if (!staged.import_id) throw new Error(staged.error || 'quote_stage_failed');
  return engineFetch(`/v1/warehouse/import/${staged.import_id}/commit`, {
    method: 'POST',
    body: { actor: 'hedge_fund_groww_quotes' },
    timeoutMs: 60_000,
  });
}

export async function refreshHedgeFundLiveQuotes({ force = false } = {}) {
  if (!isGrowwConfigured()) return { ok: false, skipped: true, reason: 'groww_not_configured' };
  if (!force && !marketOpen()) return { ok: true, skipped: true, reason: 'market_closed' };
  if (inFlight) return { ok: true, skipped: true, reason: 'refresh_in_flight' };

  inFlight = (async () => {
    // Prefer the Supabase terminal snapshot — never rebuild scanners for quotes.
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
    if (!terminal?.ok) return { ok: true, skipped: true, reason: 'no_terminal_snapshot' };
    const candidates = symbolsFromTerminal(terminal);
    if (!candidates.length) return { ok: true, skipped: true, reason: 'no_research_candidates' };
    const keys = candidates.map((row) => `NSE_${row.symbol}`);
    const [ltp, ohlc] = await Promise.all([getLTP(keys), getOHLC(keys)]);
    const date = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
    const receivedAt = new Date().toISOString();
    const rows = candidates.map((candidate) => {
      const key = `NSE_${candidate.symbol}`;
      const candle = ohlcValue(ohlc, key);
      const close = Number(quoteValue(ltp, key) ?? candle.close);
      if (!Number.isFinite(close) || close <= 0) return null;
      return {
        symbol: candidate.symbol,
        instrument_key: candidate.instrument_key,
        date,
        open: Number(candle.open) || null,
        high: Number(candle.high) || null,
        low: Number(candle.low) || null,
        close,
        volume: Number(candle.volume) || null,
        source: 'groww',
        import_time: receivedAt,
      };
    }).filter(Boolean);
    const snapshots = rows.map((row) => ({
        instrument_key: row.instrument_key || row.symbol,
        received_at: receivedAt,
        ltp: row.close,
        previous_close: candlePrevious(ohlc, `NSE_${row.symbol}`),
        cumulative_volume: row.volume,
        source: 'groww_hfl',
      }));
    let snapshotWrites = 0;
    if (snapshots.length) {
      snapshotWrites = await new LiveAlphaPersistence().persistBatch({ snapshots });
    }
    let committed = { skipped: true, reason: 'warehouse_optional' };
    try {
      committed = await commitQuotes(rows);
    } catch (error) {
      committed = { ok: false, error: error.message };
    }
    return {
      ok: true,
      candidates: candidates.length,
      quotes: rows.length,
      snapshots: snapshotWrites,
      committed,
    };
  })();

  try {
    return await inFlight;
  } finally {
    inFlight = null;
  }
}

export function startHedgeFundLiveQuoteScheduler() {
  // Quotes persist to live_market_snapshots first; warehouse import is
  // best-effort. Cap candidates so this never competes with the Live Alpha 500.
  if (
    timer ||
    String(process.env.HEDGE_FUND_LIVE_REFRESH_ENABLED || 'true').toLowerCase() !== 'true' ||
    String(process.env.HEDGE_FUND_LIVE_QUOTES || 'true').toLowerCase() !== 'true'
  ) return;
  // Default 10 minutes — do not compete with page opens every minute.
  const intervalMs = Math.max(120_000, Number(process.env.HEDGE_FUND_LIVE_QUOTE_INTERVAL_MS || 600_000));
  const tick = () => refreshHedgeFundLiveQuotes().then((result) => { lastRun = { at: new Date().toISOString(), ...result }; })
    .catch((error) => { lastRun = { at: new Date().toISOString(), ok: false, error: error.message }; });
  // Wait 12 minutes after boot — after HFL snapshot (2m) and candles (8m).
  const initialDelayMs = Math.max(60_000, Number(process.env.HEDGE_FUND_LIVE_QUOTE_INITIAL_DELAY_MS || 720_000));
  setTimeout(tick, initialDelayMs); timer = setInterval(tick, intervalMs); timer.unref?.();
}

export function getHedgeFundLiveQuoteStatus() {
  return {
    enabled: Boolean(timer),
    intervalMs: Number(process.env.HEDGE_FUND_LIVE_QUOTE_INTERVAL_MS || 600_000),
    marketOpen: marketOpen(),
    lastRun,
  };
}
