// Read-only INDstocks market data. Never exposes a token or broker order API.
import { parse } from 'csv-parse/sync';
export const isIndstocksConfigured = () => Boolean(process.env.IND_API?.trim());
const errorWithStatus = (message, status) => Object.assign(new Error(message), { status });
export function cashInstrumentMap(csv) {
  const map = new Map();
  for (const row of parse(csv, { columns: true, skip_empty_lines: true, bom: true })) {
    if (row.EXCH !== 'NSE' || row.SEGMENT !== 'E' || row.SERIES !== 'EQ' || !/^IN[A-Z0-9]{10}$/.test(row.ISIN || '') || !/^\d+$/.test(row.SECURITY_ID || '')) continue;
    const key = `NSE_EQ|${row.ISIN}`, code = `NSE_${row.SECURITY_ID}`;
    if (!map.has(key)) map.set(key, code);
    else if (map.get(key) !== code) map.set(key, null);
  }
  return map;
}
export function normalizeIndstocksCandles(json, code, start, end) {
  if (json?.success !== true || !Array.isArray(json.data?.[code]?.candles)) throw new Error('INDstocks candle history unavailable');
  const seen = new Map();
  for (const c of json.data[code].candles) {
    const ms = Number(c.ts) * 1000;
    const prices = [c.o, c.h, c.l, c.c];
    if (!Number.isFinite(ms) || ms < start || ms >= end || prices.some(v => v == null || !Number.isFinite(Number(v)) || Number(v) <= 0) || c.v == null || !Number.isFinite(Number(c.v)) || Number(c.v) < 0 || Number(c.h) < Math.max(...prices.map(Number)) || Number(c.l) > Math.min(...prices.map(Number))) throw new Error('Invalid INDstocks candle');
    const row = [new Date(ms).toISOString(), ...prices.map(Number), Number(c.v)];
    if (seen.has(ms) && JSON.stringify(seen.get(ms)) !== JSON.stringify(row)) throw new Error('Conflicting INDstocks candles');
    seen.set(ms, row);
  }
  return [...seen.values()].sort((a,b) => Date.parse(a[0])-Date.parse(b[0]));
}
export function createIndstocksClient({ token = () => process.env.IND_API?.trim(), fetchImpl = globalThis.fetch, now = Date.now, sleep = ms => new Promise(r => setTimeout(r, ms)) } = {}) {
  let queue = Promise.resolve(), lastStart = -Infinity, blockedUntil = 0, blockedStatus = null, masterPromise, masterUntil = 0, day = '', calls = 0;
  const state = { requests: 0, successes: 0, failures: 0, last_http_status: null, last_success_at: null, mapped_instruments: 0 };
  function request(path, csv = false) {
    const task = queue.then(async () => {
      if (!token()) throw errorWithStatus('INDstocks token missing',401);
      if (now() < blockedUntil) throw errorWithStatus('INDstocks provider cooling down',blockedStatus);
      const today = new Date(now()).toISOString().slice(0,10);
      if (day !== today) { day = today; calls = 0; }
      if (calls >= 50_000) throw errorWithStatus('INDstocks local daily budget exhausted',429);
      await sleep(Math.max(0, 350 - (now()-lastStart)));
      lastStart = now(); calls++; state.requests++;
      try {
        const res = await fetchImpl(`https://api.indstocks.com${path}`, { headers: { Authorization: token() }, signal: AbortSignal.timeout(20_000), redirect: 'error' });
        state.last_http_status = res.status;
        if (!res.ok) {
          if ([401,403,429].includes(res.status)) { blockedStatus = res.status; blockedUntil = now() + (res.status === 429 ? 60_000 : 30*60_000); }
          throw errorWithStatus(`INDstocks market-data HTTP ${res.status}`, res.status);
        }
        const result = csv ? await res.text() : await res.json();
        state.successes++; state.last_success_at = new Date(now()).toISOString();
        return result;
      } catch (e) { state.failures++; throw errorWithStatus(e.status ? e.message : 'INDstocks market-data request failed',e.status); }
    });
    queue = task.catch(() => {});
    return task;
  }
  async function master() {
    if (masterPromise && now() < masterUntil) return masterPromise;
    masterUntil = now()+86_400_000;
    masterPromise = request('/market/instruments?source=equity',true).then(csv => {
      const map = cashInstrumentMap(csv); state.mapped_instruments = [...map.values()].filter(Boolean).length; return map;
    }).catch(e => { masterUntil = now()+60_000; throw e; });
    return masterPromise;
  }
  async function history(key, options = {}, intraday = false) {
    if (!key.startsWith('NSE_EQ|')) throw new Error('INDstocks mapping supports NSE cash only');
    if (options.unit && (options.unit !== 'minutes' || Number(options.interval || 1) !== 1)) throw new Error('INDstocks Live Alpha supports one-minute history only');
    const at = now(), today = new Date(at+19_800_000).toISOString().slice(0,10);
    const start = Date.parse(`${intraday ? today : options.from}T${intraday ? '09:15:00' : '00:00:00'}+05:30`);
    const end = intraday ? at : Math.min(at, Date.parse(`${options.to}T00:00:00+05:30`)+86_400_000);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || end-start > 31*86_400_000) throw new Error('Invalid INDstocks history window');
    const code = (await master()).get(key);
    if (!code) throw new Error('No unambiguous INDstocks ISIN match');
    const candles = [];
    for (let from = start; from < end; from += 7*86_400_000) {
      const to = Math.min(end,from+7*86_400_000);
      const query = new URLSearchParams({'scrip-codes':code,start_time:String(from),end_time:String(to)});
      const json = await request(`/market/historical/1minute?${query}`);
      // Empty windows (e.g. holidays) are valid, but an entirely empty series is rejected by the router.
      if (json?.success === true && !json.data?.[code]) continue;
      candles.push(...normalizeIndstocksCandles(json,code,from,to));
    }
    return {data:{candles},source:'indstocks'};
  }
  return { history, status: () => ({...state, configured: Boolean(token()), cooling_down: now() < blockedUntil, read_only: true}) };
}
export const indstocks = createIndstocksClient();
