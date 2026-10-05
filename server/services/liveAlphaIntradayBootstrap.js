import { getIntradayCandles } from '../providers/upstox.js';

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
export async function bootstrapLiveAlphaIntraday({ instrumentKeys, featureStore, fetchCandles = getIntradayCandles, now = () => new Date(), active = () => true, delayMs = 250, onProgress = () => {} }) {
  const keys = [...new Set(instrumentKeys.filter(Boolean))];
  const status = { status: 'running', requested: keys.length, completed: 0, restored: 0, failed: 0, opening_ranges: 0, failures: [] };
  let cursor = 0;
  let blocked = false;
  const worker = async () => {
    while (active() && !blocked && cursor < keys.length) {
      const key = keys[cursor++];
      try {
        const payload = await fetchCandles(key, { unit: 'minutes', interval: 1, timeoutMs: 15_000 });
        if (!active()) break;
        const bars = normalizeIntradayCandles(payload);
        const at = now();
        featureStore.ingestCandles(key, bars, at);
        if (bars.length) status.restored += 1;
        else throw new Error('No usable intraday candles');
        if (featureStore.openingRange(key, at)) status.opening_ranges += 1;
      } catch (error) {
        status.failed += 1;
        if (status.failures.length < 10) status.failures.push({ instrument_key: key, status: error.status || null, reason: error.status ? `provider_http_${error.status}` : 'intraday_history_unavailable' });
        if ([401, 403, 429].includes(error.status)) blocked = true;
      }
      status.completed += 1;
      onProgress({ ...status });
      if (delayMs) await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  };
  await Promise.all([worker(), worker()]);
  status.status = !active() ? 'cancelled' : blocked ? 'blocked' : status.failed ? 'partial' : 'ready';
  onProgress({ ...status });
  return status;
}
