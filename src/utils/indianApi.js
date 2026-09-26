// src/utils/indianApi.js
// Lightweight wrapper for IndianAPI endpoints. Uses API_ORIGIN from your config.
const DEFAULT_TIMEOUT = 8000;
const DEFAULT_RETRIES = 1;

// Simple token-bucket style limiter (client-side). Configure to match IndianAPI plan.
class RateLimiter {
  constructor({ tokensPerMinute = 60 } = {}) {
    this.capacity = tokensPerMinute;
    this.tokens = tokensPerMinute;
    this.refillInterval = 60000; // 60s
    setInterval(() => { this.tokens = this.capacity; }, this.refillInterval);
    this.queue = [];
  }

  async removeToken() {
    if (this.tokens > 0) {
      this.tokens -= 1;
      return;
    }
    return new Promise(resolve => {
      const waiter = () => {
        if (this.tokens > 0) {
          this.tokens -= 1;
          resolve();
          return true;
        }
        return false;
      };
      this.queue.push(waiter);
    });
  }
}

// single limiter instance (tune tokensPerMinute to match your IndianAPI plan)
const limiter = new RateLimiter({ tokensPerMinute: 80 });

function buildUrl(base, path, params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.append(k, String(v));
  });
  const qstr = q.toString() ? `?${q.toString()}` : '';
  // base may be e.g. https://finance-news-backend-19i5.onrender.com or '' (use same origin)
  const b = (typeof base === 'string' && base) ? base.replace(/\/$/, '') : '';
  return `${b}/api/${path}${qstr}`;
}

async function timeoutFetch(url, opts = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, { ...opts, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(id);
  }
}

async function safeJson(res) {
  const ct = res.headers.get?.('content-type') || '';
  const text = await res.text().catch(() => '');
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}: ${text.slice(0, 500)}`);
    err.status = res.status;
    err.body = text;
    throw err;
  }
  if (ct.includes('json') || ct.includes('+json')) {
    try { return JSON.parse(text); } catch { return text; }
  }
  try { return JSON.parse(text); } catch { return text; }
}

export default function createIndianApi({ apiOrigin }) {
  if (!apiOrigin) apiOrigin = ''; // same origin

  async function request(path, params = {}, opts = {}) {
    // rate limit token
    await limiter.removeToken();
    const url = buildUrl(apiOrigin, path, params);
    let lastErr;
    const retries = opts.retries ?? DEFAULT_RETRIES;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await timeoutFetch(url, { method: 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } }, opts.timeout ?? DEFAULT_TIMEOUT);
        return await safeJson(res);
      } catch (err) {
        lastErr = err;
        // small backoff
        await new Promise(r => setTimeout(r, 200 * (attempt + 1)));
      }
    }
    throw lastErr;
  }

  return {
    // simple endpoint helpers
    ipo: (params) => request('ipo', params),
    news: (params) => request('news', params),
    stock: (params) => request('stock', params),
    trending: (params) => request('trending', params),
    statement: (params) => request('statement', params),
    commodities: (params) => request('commodities', params),
    mutual_funds: (params) => request('mutual_funds', params),
    price_shockers: (params) => request('price_shockers', params),
    BSE_most_active: (params) => request('BSE_most_active', params),
    NSE_most_active: (params) => request('NSE_most_active', params),
    historical_data: (params) => request('historical_data', params),
    industry_search: (params) => request('industry_search', params),
    stock_forecasts: (params) => request('stock_forecasts', params),
    historical_stats: (params) => request('historical_stats', params),
    corporate_actions: (params) => request('corporate_actions', params),
    mutual_fund_search: (params) => request('mutual_fund_search', params),
    stock_target_price: (params) => request('stock_target_price', params),
    mutual_funds_details: (params) => request('mutual_funds_details', params),
    recent_announcements: (params) => request('recent_announcements', params),
    fetch_52_week_high_low_data: (params) => request('fetch_52_week_high_low_data', params),
    clearLimiter: () => { limiter.tokens = limiter.capacity; limiter.queue = []; }
  };
}
