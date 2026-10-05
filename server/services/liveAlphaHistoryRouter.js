import { parse } from 'csv-parse/sync';
import { getHistoricalCandleRange, isGrowwConfigured } from '../providers/groww.js';
import { getHistoricalCandles, getIntradayCandles } from '../providers/upstox.js';

let masterPromise = null, masterUntil = 0;
async function growwCashMaster() {
  if (masterPromise && Date.now() < masterUntil) return masterPromise;
  masterUntil = Date.now() + 86_400_000;
  masterPromise = (async () => {
    const response = await fetch('https://growwapi-assets.groww.in/instruments/instrument.csv', { signal: AbortSignal.timeout(30_000) });
    if (!response.ok) throw new Error('Groww instrument master unavailable');
    const rows = parse(await response.text(), { columns: true, skip_empty_lines: true, relax_column_count: true });
    const map = new Map();
    for (const row of rows) {
      if (row.exchange !== 'NSE' || row.segment !== 'CASH' || !row.isin || !row.groww_symbol) continue;
      const key = `NSE_EQ|${row.isin}`;
      // Ambiguous share classes/series are not interchangeable.
      if (map.has(key) && map.get(key) !== row.groww_symbol) map.set(key, null);
      else if (!map.has(key)) map.set(key, row.groww_symbol);
    }
    return map;
  })().catch(error => { masterUntil = Date.now() + 60_000; throw error; });
  return masterPromise;
}

export function validHistoryPayload(payload) {
  const rows = payload?.data?.candles;
  return Array.isArray(rows) && rows.length > 0 && rows.every(row => {
    const numbers = row.slice(1, 5).map(Number);
    return row[0] != null && Number.isFinite(Date.parse(row[0])) && numbers.length === 4 && numbers.every(n => n > 0)
      && Number(row[2]) >= Math.max(Number(row[1]), Number(row[3]), Number(row[4]))
      && Number(row[3]) <= Math.min(Number(row[1]), Number(row[2]), Number(row[4]))
      && row[5] != null && Number.isFinite(Number(row[5])) && Number(row[5]) >= 0;
  });
}

// Route complete requests, never splice providers inside a candle series. Groww
// handles alternate cash instruments; indices/futures keep their canonical
// Upstox keys. ISIN equality is mandatory before requesting Groww history.
export function createLiveAlphaHistoryRouter({ growwConfigured = isGrowwConfigured, master = growwCashMaster,
  growwHistory = getHistoricalCandleRange, upstoxHistory = getHistoricalCandles,
  upstoxIntraday = getIntradayCandles, now = () => new Date() } = {}) {
  const counters = { groww: 0, upstox: 0, fallbacks: 0, failures: 0 };
  const preferred = key => key.startsWith('NSE_EQ|') && [...key].reduce((sum, ch) => sum + ch.charCodeAt(0), 0) % 2 === 0 && growwConfigured() ? 'groww' : 'upstox';
  async function load(key, options, intraday) {
    const primary = preferred(key);
    // Only eligible cash instruments have an alternative; never guess an index
    // or futures mapping, and never substitute daily data for intraday history.
    const providers = key.startsWith('NSE_EQ|') && growwConfigured()
      ? [primary, primary === 'groww' ? 'upstox' : 'groww'] : ['upstox'];
    let lastError;
    for (const [index, provider] of providers.entries()) {
      try {
        let payload;
        if (provider === 'upstox') payload = await (intraday ? upstoxIntraday : upstoxHistory)(key, options);
        else {
          const symbol = (await master()).get(key);
          if (!symbol) throw new Error('No unambiguous Groww ISIN match');
          const at = now(), today = new Date(at.getTime() + 19_800_000).toISOString().slice(0, 10);
          const start = intraday ? new Date(`${today}T09:15:00+05:30`) : new Date(`${options.from}T00:00:00+05:30`);
          const end = intraday ? at : new Date(`${options.to}T23:59:59+05:30`);
          const rows = await growwHistory('NSE', 'CASH', symbol, start, end, 1);
          payload = { data: { candles: rows.map(row => [new Date(Number(row[0]) * 1000).toISOString(), ...row.slice(1)]) } };
        }
        if (!validHistoryPayload(payload)) throw new Error('Empty or invalid provider candle history');
        counters[provider]++; if (index) counters.fallbacks++;
        return { ...payload, source: provider };
      } catch (error) { lastError = error; }
    }
    counters.failures++;
    throw lastError;
  }
  return { historical: (key, options) => load(key, options, false), intraday: (key, options) => load(key, options, true),
    status: () => ({ ...counters, policy: 'split_cash_history_by_isin', live_stream: 'upstox', candle_series_spliced: false }) };
}
export const liveAlphaHistoryRouter = createLiveAlphaHistoryRouter();
