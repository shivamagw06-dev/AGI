import { gunzipSync } from 'node:zlib';
export const FUND_URL = 'https://assets.upstox.com/market-quote/instruments/exchange/mf-instruments.json.gz';
const numeric = value => value === '' || value == null || typeof value === 'boolean' ? null : Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : null;
export function parseUpstoxFunds(data) {
  if (!Array.isArray(data)) throw new Error('Invalid fund directory');
  const seen = new Set();
  return data.flatMap(item => {
    if (!item || !/^INF[A-Z0-9]{9}$/.test(item.instrument_key) || typeof item.name !== 'string' || !item.name.trim() || seen.has(item.instrument_key)) return [];
    seen.add(item.instrument_key);
    const date = item.last_price_date;
    const asOf = typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date)) && new Date(date).toISOString().slice(0,10) === date ? date : null;
    return [{ id:`upstox-mf:${item.instrument_key}`, instrumentKey:item.instrument_key, isin:item.instrument_key,
      name:item.name, fundHouse:typeof item.amc === 'string' ? item.amc : null,
      category:typeof item.scheme_type === 'string' ? item.scheme_type : null,
      plan:typeof item.plan === 'string' ? item.plan : null,
      price:numeric(item.last_price) > 0 ? numeric(item.last_price) : null, asOf,
      minimumInvestment:numeric(item.minimum_purchase_amount),
      purchaseAllowed:typeof item.purchase_allowed === 'boolean' ? item.purchase_allowed : null,
      source:'Upstox', sourceUrl:'https://upstox.com/developer/api-documentation/instruments/', currency:'INR', assetClass:'mutual_fund' }];
  });
}
export function createUpstoxFundProvider({ fetchImpl = globalThis.fetch, now = Date.now } = {}) {
  let cached, expires = 0, pending;
  return async function getFunds() {
    if (cached && now() < expires) return cached;
    if (pending) return pending;
    pending = (async () => {
      try {
        const response = await fetchImpl(FUND_URL, { signal:AbortSignal.timeout(12000) });
        if (!response.ok) throw new Error('Request failed');
        const reader = response.body.getReader();
        const chunks = []; let size = 0;
        try { while (true) { const {value,done} = await reader.read(); if(done) break; size += value.length; if(size > 15_000_000) throw new Error('Directory too large'); chunks.push(Buffer.from(value)); } }
        finally { await reader.cancel(); }
        let bytes = Buffer.concat(chunks);
        if (bytes[0] === 0x1f && bytes[1] === 0x8b) bytes = gunzipSync(bytes, { maxOutputLength:30_000_000 });
        const rows = parseUpstoxFunds(JSON.parse(bytes.toString('utf8')));
        if (!rows.length) throw new Error('Empty directory');
        cached = { rows, status:'available', fetchedAt:new Date(now()).toISOString(), error:null };
        expires = now() + 3600000;
      } catch {
        cached = { rows:cached?.rows || [], status:cached?.rows?.length ? 'stale' : 'unavailable', fetchedAt:cached?.fetchedAt || null, error:'Upstox fund directory refresh unavailable.' };
        expires = now() + 60000;
      }
      return cached;
    })();
    try { return await pending; } finally { pending = null; }
  };
}
export const getUpstoxFunds = createUpstoxFundProvider();
