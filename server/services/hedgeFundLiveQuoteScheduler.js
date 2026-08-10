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

function symbolsFromTerminal(pack) {
  const symbols = new Set();
  for (const row of [...(pack?.research_queue || []), ...(pack?.overlap || [])]) {
    if (row?.ticker) symbols.add(String(row.ticker).toUpperCase());
  }
  for (const hit of pack?.hero?.highlights || []) {
    const row = hit?.row || {};
    if (row.ticker) symbols.add(String(row.ticker).toUpperCase());
    if (row.long_leg?.ticker) symbols.add(String(row.long_leg.ticker).toUpperCase());
    if (row.short_leg?.ticker) symbols.add(String(row.short_leg.ticker).toUpperCase());
  }
  // Prefer a small candidate set — Groww rate limits and engine load both matter.
  return [...symbols].filter(Boolean).slice(0, Number(process.env.HEDGE_FUND_LIVE_QUOTE_LIMIT || 25));
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
    const symbols = symbolsFromTerminal(terminal);
    if (!symbols.length) return { ok: true, skipped: true, reason: 'no_research_candidates' };
    const keys = symbols.map((symbol) => `NSE_${symbol}`);
    const [ltp, ohlc] = await Promise.all([getLTP(keys), getOHLC(keys)]);
    const date = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
    const rows = symbols.map((symbol) => {
      const key = `NSE_${symbol}`;
      const candle = ohlcValue(ohlc, key);
      const close = Number(quoteValue(ltp, key) ?? candle.close);
      if (!Number.isFinite(close) || close <= 0) return null;
      return {
        symbol,
        date,
        open: Number(candle.open) || null,
        high: Number(candle.high) || null,
        low: Number(candle.low) || null,
        close,
        volume: Number(candle.volume) || null,
        source: 'groww',
        import_time: new Date().toISOString(),
      };
    }).filter(Boolean);
    const committed = await commitQuotes(rows);
    return { ok: true, candidates: symbols.length, quotes: rows.length, committed };
  })();

  try {
    return await inFlight;
  } finally {
    inFlight = null;
  }
}

export function startHedgeFundLiveQuoteScheduler() {
  // Quote refresh currently depends on a terminal rebuild plus warehouse
  // import. Keep it off until it is moved to an isolated data worker.
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
