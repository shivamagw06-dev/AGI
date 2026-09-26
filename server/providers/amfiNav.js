const URL = 'https://portal.amfiindia.com/spages/NAVAll.txt';
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const CACHE_MS = 60 * 60 * 1000;

function navDate(raw) {
  const parts = String(raw).trim().split('-');
  const month = MONTHS.indexOf(parts[1]);
  if (parts.length !== 3 || month < 0 || !/^\d{4}$/.test(parts[2])) return null;
  const date = new Date(Date.UTC(Number(parts[2]), month, Number(parts[0])));
  if (date.getUTCMonth() !== month || date.getUTCDate() !== Number(parts[0])) return null;
  return date.toISOString().slice(0, 10);
}

export function parseAmfiNav(text) {
  const rows = [], seen = new Set();
  let category = '', fundHouse = '';
  for (const raw of String(text).split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (!line.includes(';')) {
      if (/^(Open Ended|Close Ended|Interval)/i.test(line)) category = line;
      else fundHouse = line;
      continue;
    }
    const fields = line.split(';');
    const [code, isinGrowth, isinReinvestment, baseName] = fields;
    // AMFI publishes both the legacy six-column and new eight-column layouts.
    const extended = fields.length === 8;
    if (fields.length !== 6 && !extended) continue;
    const name = extended ? [baseName, fields[4], fields[5]].filter(Boolean).join(' · ') : baseName;
    const price = fields[extended ? 6 : 4], date = fields[extended ? 7 : 5];
    const nav = Number(price), asOf = navDate(date);
    if (fields.length < 6 || !/^\d+$/.test(code) || seen.has(code) || !name || !(nav > 0) || !Number.isFinite(nav) || !asOf) continue;
    seen.add(code);
    rows.push({ id: `amfi:${code}`, schemeCode: code, name, category, fundHouse, price: nav, asOf,
      isin: /^INF[A-Z0-9]{9}$/.test(isinGrowth) ? isinGrowth : /^INF[A-Z0-9]{9}$/.test(isinReinvestment) ? isinReinvestment : null,
      source: 'AMFI', sourceUrl: URL, currency: 'INR', assetClass: 'mutual_fund' });
  }
  return rows;
}

/** One process cache and in-flight request shared across all users. No history or return estimates fabricated. */
export function createAmfiNavProvider({ fetchImpl = globalThis.fetch, now = Date.now } = {}) {
  let cached = null, expiresAt = 0, pending = null;
  return async function getNav() {
    if (cached && now() < expiresAt) return cached;
    if (pending) return pending;
    pending = (async () => {
      try {
        const response = await fetchImpl(URL, { signal: AbortSignal.timeout(12_000), headers: { Accept: 'text/plain' } });
        if (!response.ok) throw new Error('AMFI request failed');
        const text = await response.text();
        if (text.length > 15_000_000) throw new Error('AMFI response too large');
        const rows = parseAmfiNav(text);
        if (!rows.length) throw new Error('AMFI returned no usable NAVs');
        cached = { rows, status: 'available', fetchedAt: new Date(now()).toISOString(), error: null };
        expiresAt = now() + CACHE_MS;
      } catch {
        cached = { rows: cached?.rows || [], fetchedAt: cached?.fetchedAt || null,
          status: cached?.rows?.length ? 'stale' : 'unavailable', error: 'AMFI NAV refresh unavailable.' };
        expiresAt = now() + 60_000;
      }
      return cached;
    })();
    try { return await pending; } finally { pending = null; }
  };
}

export const getAmfiNav = createAmfiNavProvider();
