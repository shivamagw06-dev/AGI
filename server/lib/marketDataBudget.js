import { createHash } from 'node:crypto';

// Conservative per-process allocations leave room for the separate Python
// research service. They are NOT an account-wide distributed quota.
export const MARKET_DATA_BUDGETS = Object.freeze({
  upstox: [[1000, 4], [60_000, 120], [1_800_000, 800]],
  groww: [[1000, 2], [60_000, 100]],
});

export const BACKGROUND_DATA_BUDGETS = Object.freeze({
  upstox: [[1000, 2], [60_000, 80], [1_800_000, 550]],
  groww: [[1000, 1], [60_000, 60]],
});

export class MarketDataBudget {
  constructor({ now = Date.now, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), budgets = MARKET_DATA_BUDGETS, backgroundBudgets = budgets === MARKET_DATA_BUDGETS ? BACKGROUND_DATA_BUDGETS : {} } = {}) {
    this.now = now; this.sleep = sleep; this.budgets = budgets; this.backgroundBudgets = backgroundBudgets;
    this.states = new Map(); this.pending = new Map(); this.cache = new Map();
  }
  state(provider) {
    if (!this.states.has(provider)) this.states.set(provider, { starts: [], backgroundStarts: [], cooldown: 0, requests: 0, rate_limits: 0, shared: 0, cache_hits: 0, deferred: 0 });
    return this.states.get(provider);
  }
  async reserve(provider, signal, background = false) {
    const state = this.state(provider), windows = this.budgets[provider], began = this.now();
    while (true) {
      signal?.throwIfAborted();
      const now = this.now();
      state.starts = state.starts.filter(at => at > now - Math.max(...windows.map(([ms]) => ms)));
      let delay = Math.max(0, state.cooldown - now);
      state.backgroundStarts = state.backgroundStarts.filter(at => at > now - 1_800_000);
      const checks = [...windows.map(([ms, limit]) => [ms, limit, state.starts]),
        ...(background ? (this.backgroundBudgets[provider] || []).map(([ms, limit]) => [ms, limit, state.backgroundStarts]) : [])];
      for (const [ms, limit, starts] of checks) {
        const recent = starts.filter(at => at > now - ms);
        if (recent.length >= limit) delay = Math.max(delay, recent[recent.length - limit] + ms - now);
      }
      if (!delay) { state.starts.push(now); if (background) state.backgroundStarts.push(now); state.requests++; return; }
      // Never hold an API request or live evaluation behind a lengthy backlog.
      if (now - began + delay > 20_000) {
        state.deferred++;
        const error = new Error(`${provider} market-data budget cooling down; retry on the next scheduled cycle`);
        error.status = 429; error.isRateLimit = true; error.retryAfterMs = delay;
        throw error;
      }
      await this.sleep(Math.min(delay, 1000));
    }
  }
  async fetch(provider, url, options = {}, fetchImpl = globalThis.fetch) {
    if (!this.budgets[provider] || String(options.method || 'GET').toUpperCase() !== 'GET') throw new Error('Market-data budget accepts read-only GET requests');
    const state = this.state(provider);
    const auth = new Headers(options.headers).get('authorization') || '';
    const key = createHash('sha256').update(`${provider}|${url}|${auth}`).digest('hex');
    const cached = this.cache.get(key);
    if (cached && cached.until > this.now()) { state.cache_hits++; return cached.response.clone(); }
    if (this.pending.has(key)) { state.shared++; const response = await this.pending.get(key); return response.clone ? response.clone() : response; }
    const background = !/(?:market-quote|live-data)\//.test(String(url));
    if (this.pending.size >= (background ? 96 : 128)) {
      state.deferred++;
      const error = new Error('Market-data queue is full; retry next cycle');
      error.status = 429; error.isRateLimit = true; throw error;
    }
    const task = (async () => {
      await this.reserve(provider, options.signal, background);
      const response = await fetchImpl(url, { ...options, signal: options.signal || AbortSignal.timeout(30_000) });
      if (response.status === 429) {
        state.rate_limits++;
        const raw = response.headers?.get('retry-after');
        const retry = raw && Number.isFinite(Number(raw)) ? Number(raw) * 1000 : Date.parse(raw) - this.now();
        state.cooldown = this.now() + Math.max(60_000, Number.isFinite(retry) ? retry : 0);
      }
      if ([401, 403].includes(response.status)) state.cooldown = this.now() + 60_000;
      // Only share short-lived quote responses. Historical bodies can be huge;
      // coalesce concurrent downloads, but do not accumulate them in memory.
      if (response.ok && /(?:market-quote|live-data)\//.test(String(url)) && response.clone) {
        for (const [id, entry] of this.cache) if (entry.until <= this.now()) this.cache.delete(id);
        if (this.cache.size >= 128) this.cache.delete(this.cache.keys().next().value);
        this.cache.set(key, { until: this.now() + 2000, response: response.clone() });
      }
      return response;
    })();
    this.pending.set(key, task);
    try { const response = await task; return response.clone ? response.clone() : response; }
    finally { this.pending.delete(key); }
  }
  status() {
    return { scope: 'node_process', account_wide: false, budgets: this.budgets, background_budgets: this.backgroundBudgets,
      providers: Object.fromEntries([...this.states].map(([name, state]) => [name, {
        requests: state.requests, rate_limits: state.rate_limits, shared_requests: state.shared,
        cache_hits: state.cache_hits, deferred: state.deferred,
        windows: this.budgets[name].map(([window_ms, limit]) => ({ window_ms, limit, used: state.starts.filter(at => at > this.now() - window_ms).length })),
        cooldown_until: state.cooldown > this.now() ? new Date(state.cooldown).toISOString() : null,
      }])) };
  }
}
export const marketDataBudget = new MarketDataBudget();
export const budgetedMarketFetch = (provider, url, options, fetchImpl) => marketDataBudget.fetch(provider, url, options, fetchImpl);
