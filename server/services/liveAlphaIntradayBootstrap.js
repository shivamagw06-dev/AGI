import { liveAlphaHistoryRouter } from './liveAlphaHistoryRouter.js';

export function normalizeIntradayCandles(payload) {
  return (payload?.data?.candles || []).flatMap(row => {
    const timestamp = Date.parse(row[0]);
    const [open, high, low, close] = row.slice(1, 5).map(Number);
    if (!Number.isFinite(timestamp) || ![open, high, low, close].every(value => value > 0) || high < Math.max(open, close, low) || low > Math.min(open, close)) return [];
    return [{ interval: 'I1', timestamp, open, high, low, close, open_interest: Number(row[6]) > 0 ? Number(row[6]) : null }];
  }).sort((a, b) => a.timestamp - b.timestamp);
}

// Bounded, read-only recovery. Keep candle timestamps and do not fabricate volume
// or publish retrospective signals. Live ticks still supply the current quote.
export async function bootstrapLiveAlphaIntraday({ instrumentKeys, featureStore, fetchCandles = liveAlphaHistoryRouter.intraday, now = () => new Date(), active = () => true, delayMs = 250, onProgress = () => {}, recoveredKeys = new Set() }) {
  const keys = [...new Set(instrumentKeys.filter(Boolean))];
  const pending = keys.filter(key => !recoveredKeys.has(key));
  const alreadyRestored = keys.length - pending.length;
  const status = { status: 'running', requested: keys.length, completed: alreadyRestored, restored: alreadyRestored, failed: 0, opening_ranges: keys.filter(key => recoveredKeys.has(key) && featureStore.openingRange(key, now())).length, failures: [] };
  let cursor = 0;
  const worker = async () => {
    while (active() && cursor < pending.length) {
      const key = pending[cursor++];
      try {
        const payload = await fetchCandles(key, { unit: 'minutes', interval: 1, timeoutMs: 15_000 });
        if (!active()) break;
        const at = now();
        const session = ms => new Date(ms + 5.5 * 60 * 60_000).toISOString().slice(0, 10);
        const bars = normalizeIntradayCandles(payload).filter(bar => bar.timestamp + 60_000 <= at.getTime() && session(bar.timestamp) === session(at.getTime()));
        featureStore.ingestCandles(key, bars, at);
        if (bars.length) { status.restored += 1; recoveredKeys.add(key); }
        else throw new Error('No usable intraday candles');
        if (featureStore.openingRange(key, at)) status.opening_ranges += 1;
      } catch (error) {
        status.failed += 1;
        if (status.failures.length < 10) status.failures.push({ instrument_key: key, status: error.status || null, reason: error.localBudget ? 'local_budget_deferred' : error.status ? `provider_http_${error.status}` : 'intraday_history_unavailable' });
        // Provider circuits in the router prevent repeated calls. One unavailable
        // index/provider must not block unrelated equities on healthy providers.
      }
      status.completed += 1;
      onProgress({ ...status });
      if (delayMs) await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  };
  await Promise.all([worker(), worker()]);
  status.status = !active() ? 'cancelled' : status.failed ? 'partial' : 'ready';
  onProgress({ ...status });
  return status;
}
