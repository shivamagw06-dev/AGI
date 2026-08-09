const SYMBOL_RE = /^[A-Z0-9][A-Z0-9&.-]{0,31}$/;
const INSTRUMENT_KEY_RE = /^[A-Z0-9_]+\|[A-Z0-9][A-Z0-9_-]*$/;

export function canonicalSymbol(value) {
  const symbol = String(value || '').trim().toUpperCase();
  return SYMBOL_RE.test(symbol) ? symbol : null;
}

export function validInstrumentKey(value) {
  return INSTRUMENT_KEY_RE.test(String(value || '').trim().toUpperCase());
}

export function validateConfluenceCandidate(item, member, universe, { now = new Date(), maxAnchorAgeHours = 24 } = {}) {
  const reasons = [];
  const symbol = canonicalSymbol(item?.symbol);
  const memberSymbol = canonicalSymbol(member?.symbol);
  if (!symbol || !memberSymbol || symbol !== memberSymbol) reasons.push('identity_symbol_mismatch');
  if (!validInstrumentKey(member?.instrumentKey)) reasons.push('invalid_instrument_key');
  if (!validInstrumentKey(member?.sectorInstrumentKey)) reasons.push('invalid_sector_instrument_key');
  if (!validInstrumentKey(universe?.benchmarkKey)) reasons.push('invalid_benchmark_instrument_key');
  if (!String(item?.sector || member?.sector || '').trim()) reasons.push('missing_sector');

  const capturedMs = Date.parse(item?.anchors?.captured_at || '');
  if (!Number.isFinite(capturedMs)) reasons.push('missing_price_anchor');
  else {
    const ageHours = (now.getTime() - capturedMs) / 3_600_000;
    if (ageHours < -5 / 60) reasons.push('future_price_anchor');
    if (ageHours > maxAnchorAgeHours) reasons.push('stale_price_anchor');
  }

  for (const [name, value] of Object.entries({
    price_at_signal: item?.anchors?.price_at_signal,
    benchmark_at_signal: item?.anchors?.benchmark_at_signal,
    sector_index_at_signal: item?.anchors?.sector_index_at_signal,
  })) {
    if (!Number.isFinite(Number(value)) || Number(value) <= 0) reasons.push(`invalid_${name}`);
  }
  return { valid: reasons.length === 0, symbol, reasons };
}

export function settlementWindow(dueAt, horizon) {
  const start = new Date(dueAt);
  if (Number.isNaN(start.getTime())) throw new Error('Invalid outcome due timestamp.');
  const minutes = ['5m', '15m', '30m', '60m'].includes(horizon) ? 30 : horizon === 'close' ? 60 : 8 * 60;
  return { start: start.toISOString(), end: new Date(start.getTime() + minutes * 60_000).toISOString() };
}

export function validateSettlementSnapshots(rows, { maximumSkewMs = 5 * 60_000 } = {}) {
  if (!Array.isArray(rows) || rows.length !== 3 || rows.some((row) => !row)) return { valid: false, reason: 'missing_settlement_snapshot' };
  const times = rows.map((row) => Date.parse(row.observed_at || ''));
  if (times.some((value) => !Number.isFinite(value))) return { valid: false, reason: 'invalid_settlement_timestamp' };
  const skewMs = Math.max(...times) - Math.min(...times);
  if (skewMs > maximumSkewMs) return { valid: false, reason: 'settlement_snapshot_skew', skew_ms: skewMs };
  if (rows.some((row) => !Number.isFinite(Number(row.ltp)) || Number(row.ltp) <= 0)) return { valid: false, reason: 'invalid_settlement_price' };
  return { valid: true, reason: null, skew_ms: skewMs };
}

export function diagnosePipelineBottlenecks({ scheduler, counts, feeds, marketClosed = false }) {
  const diagnostics = [];
  const rejected = scheduler?.last_capture?.rejected || {};
  const rejectionTotal = Object.values(rejected).reduce((sum, value) => sum + (Number(value) || 0), 0);
  const candidates = Number(scheduler?.last_capture?.candidates || 0);
  if (candidates && rejectionTotal / candidates >= 0.2) {
    const [reason, count] = Object.entries(rejected).sort((a, b) => Number(b[1]) - Number(a[1]))[0] || [];
    diagnostics.push({ stage: 'IDENTITY_AND_ANCHORS', severity: 'BLOCKING', reason: reason || 'candidate_rejections', affected: Number(count || rejectionTotal) });
  }
  if (!marketClosed && feeds?.market_feed && !['READY', 'CONNECTED'].includes(feeds.market_feed)) diagnostics.push({ stage: 'COLLECTION', severity: 'BLOCKING', reason: 'market_feed_unavailable' });
  if ((counts?.events || 0) > (counts?.memory || 0)) diagnostics.push({ stage: 'RESEARCH_MEMORY', severity: 'LAGGING', reason: 'memory_coverage_gap', affected: counts.events - counts.memory });
  if ((counts?.events || 0) > (counts?.feature_snapshots || 0)) diagnostics.push({ stage: 'FORECAST_FEATURES', severity: 'LAGGING', reason: 'feature_snapshot_gap', affected: counts.events - counts.feature_snapshots });
  if ((counts?.feature_snapshots || 0) * 3 > (counts?.forecasts || 0)) diagnostics.push({ stage: 'FORECAST_GENERATION', severity: 'LAGGING', reason: 'forecast_coverage_gap', affected: counts.feature_snapshots * 3 - counts.forecasts });
  if ((counts?.outcomes || 0) > 0 && (counts?.forecast_outcomes || 0) === 0) diagnostics.push({ stage: 'OUTCOME_SETTLEMENT', severity: 'OBSERVE', reason: 'no_matured_forecast_outcomes' });
  return diagnostics;
}
