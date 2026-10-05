// Reuse provider timestamps, never the cache read time. This store contains
// market data only; no account holdings or credentials.
export class SharedLiveQuotes {
  constructor() { this.rows = new Map(); this.hits = 0; }
  ingest(snapshots = [], now = Date.now()) {
    for (const row of snapshots) {
      const at = Number(row.exchange_timestamp);
      const price = Number(row.ltp), key = row.instrument_key;
      if (!key || !(price > 0) || !Number.isFinite(at) || at <= 0 || at > now || now - at > 120_000) continue;
      if ((this.rows.get(key)?.at || 0) >= at) continue;
      this.rows.set(key, { at, price, time: new Date(at).toISOString(), instrumentKey: key, source: row.source || 'live_stream' });
    }
    if (this.rows.size > 5000) for (const [key, row] of this.rows) if (now - row.at > 120_000) this.rows.delete(key);
  }
  get(key, now = Date.now(), maxAgeMs = 30_000) {
    const row = this.rows.get(key);
    if (!row || now < row.at || now - row.at > maxAgeMs) return null;
    this.hits++;
    return { ...row };
  }
  status() { return { cached_instruments: this.rows.size, cache_hits: this.hits, max_quote_age_ms: 30_000 }; }
}
export const sharedLiveQuotes = new SharedLiveQuotes();
