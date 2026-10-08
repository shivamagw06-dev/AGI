// Closed-session snapshots remain useful history, but never become live signals.
export function liveAlphaSnapshotDisplay({ freshness, runtime, signals, requestFailed = false, now = Date.now() } = {}) {
  const timestamp = Date.parse(freshness?.latest_successful_at || '');
  const saved = Array.isArray(signals) && signals.length > 0 && Number.isFinite(timestamp) && timestamp <= now;
  const historical = !requestFailed && saved && runtime?.evaluation_status === 'market_closed';
  return { historical, withheld: requestFailed || (!historical && freshness?.stale !== false) };
}
