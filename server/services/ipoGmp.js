import fs from 'node:fs/promises';
import path from 'node:path';

const endpoint = 'https://xflot.com/api/public/market/ipos?status=OPEN&board=MAINBOARD&limit=200';
const file = path.join(process.env.DATA_DIR || path.resolve('data'), 'ipo-gmp-xflot.json');
const dayKey = () => new Date(Date.now() + 19800000).toISOString().slice(0, 10);
let state = { day: null, records: [], history: [] };
let loaded = false, pending = null, retryAt = 0;
const numeric = v => v !== null && v !== undefined && String(v).trim() !== '' && Number.isFinite(Number(v)) ? Number(v) : null;
const nameKey = v => String(v || '').toLowerCase().replace(/\b(ipo|limited|ltd)\b/g, '').replace(/[^a-z0-9]/g, '');

export function matchXflot(ipo, records) {
  if (ipo.isSme) return null;
  const matches = records.filter(r => r.board === 'MAINBOARD' && r.status === 'OPEN' && (
    (ipo.symbol && r.symbol && ipo.symbol.toUpperCase() === r.symbol.toUpperCase()) || nameKey(ipo.name) === nameKey(r.name)
  ));
  return matches.length === 1 ? matches[0] : null;
}

export function quoteFromXflot(ipo, snapshot) {
  const row = matchXflot(ipo, snapshot.records || []);
  const value = numeric(row?.lastGmp);
  if (!row || value === null) return null;
  const issuePrice = numeric(ipo.cutOffPrice) ?? numeric(ipo.maxPrice);
  const sourcePrice = numeric(row.priceMax);
  const mismatch = issuePrice !== null && sourcePrice !== null && issuePrice !== sourcePrice;
  return {
    value, percentage: !mismatch && issuePrice > 0 ? value / issuePrice * 100 : null,
    indicativeListingPrice: !mismatch && issuePrice > 0 ? issuePrice + value : null,
    source: 'Xflot', sourceUrl: 'https://www.xflot.com/api-docs',
    updatedAt: null, recordUpdatedAt: row.updatedAt || null, fetchedAt: snapshot.fetchedAt,
    stale: Boolean(snapshot.unavailable || !snapshot.fetchedAt || Date.now() - Date.parse(snapshot.fetchedAt) > 26 * 3600000),
    disputed: Boolean(row.gmpDisputed || mismatch), unofficial: true,
    disclaimer: snapshot.disclaimer,
  };
}

export async function loadDailyXflot() {
  if (pending) return pending;
  pending = (async () => {
    if (!loaded) {
      try { const saved = JSON.parse(await fs.readFile(file, 'utf8')); if (Array.isArray(saved.records)) state = saved; } catch {}
      loaded = true;
    }
    if (state.day === dayKey() || Date.now() < retryAt) return state;
    try {
      const response = await fetch(endpoint, { signal: AbortSignal.timeout(15000), headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (payload.ok !== true || !Array.isArray(payload.ipos) || payload.count !== payload.ipos.length || payload.count >= 200) throw new Error('Invalid or truncated GMP feed');
      const fetchedAt = new Date().toISOString();
      state = { day: dayKey(), fetchedAt, records: payload.ipos, disclaimer: payload.disclaimer, unavailable: false,
        history: [...(state.history || []), { fetchedAt, records: payload.ipos }].slice(-365) };
      try {
        await fs.mkdir(path.dirname(file), { recursive: true });
        await fs.writeFile(`${file}.tmp`, JSON.stringify(state));
        await fs.rename(`${file}.tmp`, file);
      } catch (e) { console.warn('[ipo][gmp] snapshot persistence failed:', e.message); }
    } catch (e) {
      console.warn('[ipo][gmp] Xflot:', e.message);
      state = { ...state, unavailable: true };
      retryAt = Date.now() + 15 * 60000;
    }
    return state;
  })().finally(() => { pending = null; });
  return pending;
}

let timer;
export function startDailyGmp() {
  if (timer) return;
  // Startup catches missed runs; hourly checks fetch at most once per IST day.
  void loadDailyXflot();
  timer = setInterval(() => { void loadDailyXflot(); }, 3600000);
  timer.unref?.();
}
