import { createOutcomeSchedule } from './alphaOutcomeTracker.js';

function config() {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key) throw new Error('Live alpha persistence requires Supabase service credentials.');
  return { url, key };
}

async function rest(table, { method = 'POST', query = '', body, prefer = 'return=minimal' } = {}) {
  const { url, key } = config();
  const response = await fetch(`${url}/rest/v1/${table}${query ? `?${query}` : ''}`, {
    method, headers: { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', Prefer: prefer },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Live alpha storage failed (${response.status}): ${(await response.text()).slice(0, 300)}`);
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

export class LiveAlphaPersistence {
  constructor() { this.persistedMinute = new Map(); }
  async persistBatch(batch) {
    const rows = [];
    for (const item of batch?.snapshots || []) {
      const minute = String(item.received_at).slice(0, 16);
      if (this.persistedMinute.get(item.instrument_key) === minute) continue;
      this.persistedMinute.set(item.instrument_key, minute);
      rows.push({
        instrument_key: item.instrument_key, observed_at: item.received_at,
        exchange_timestamp: item.exchange_timestamp ? new Date(item.exchange_timestamp).toISOString() : null,
        ltp: item.ltp, previous_close: item.previous_close, last_traded_quantity: item.last_traded_quantity,
        average_traded_price: item.average_traded_price, cumulative_volume: item.cumulative_volume,
        open_interest: item.open_interest, implied_volatility: item.implied_volatility,
        best_bid: item.best_bid, best_ask: item.best_ask, spread_bps: item.spread_bps,
        feed_latency_ms: item.feed_latency_ms,
        raw_factors: { ohlc: item.ohlc, total_buy_quantity: item.total_buy_quantity, total_sell_quantity: item.total_sell_quantity, request_mode: item.request_mode },
      });
    }
    if (rows.length) await rest('live_market_snapshots', { body: rows });
    return rows.length;
  }
  async saveHealth(status, staleInstruments = 0) {
    await rest('live_market_feed_health', { body: { status: status.status, subscribed_instruments: status.subscribed_instruments, messages: status.messages, decode_errors: status.decode_errors, reconnects: status.reconnects, last_message_at: status.last_message_at, stale_instruments: staleInstruments, diagnostics: { last_error: status.last_error, mode: status.mode } } });
  }
  async loadVolumeBaselines() {
    return rest('live_volume_baselines', { method: 'GET', query: 'select=instrument_key,minute_of_session,expected_cumulative_volume,sample_sessions', body: undefined, prefer: undefined });
  }
  async saveAlphaRun(result, diagnostics = {}) {
    const session = new Date(new Date(result.as_of).getTime() + 5.5 * 60 * 60_000).toISOString().slice(0, 10);
    const runs = await rest('live_alpha_runs', {
      body: { engine: result.engine, as_of: result.as_of, market_session: session, universe_size: result.universe_size, research_only: true, execution_enabled: false, config: result.config || { weights: result.weights }, diagnostics },
      prefer: 'return=representation',
    });
    const runId = runs?.[0]?.id;
    if (!runId) throw new Error('Live alpha run insert did not return an id.');
    const rows = result.signals.map((signal) => ({
      run_id: runId, symbol: signal.symbol, instrument_key: signal.instrument_key, sector: signal.sector,
      rank: signal.rank, classification: signal.classification, alpha_z: signal.alpha_z,
      signal_quality_score: signal.signal_quality.score, signal_quality_label: signal.signal_quality.label,
      empirical_confidence_score: signal.empirical_confidence.score, comparable_observations: signal.empirical_confidence.comparable_observations,
      liquidity_ok: signal.liquidity_ok, factor_values: { ...signal.factors, residual_15m: signal.residual_15m, residual_60m: signal.residual_60m, volume_surprise: signal.volume_surprise, sector_strength: signal.sector_strength },
      direction: signal.direction, price_at_signal: signal.price_at_signal, nifty_at_signal: signal.nifty_at_signal,
      sector_at_signal: signal.sector_at_signal, volume_ratio: signal.volume_surprise,
    }));
    const saved = await rest('live_alpha_signals', { body: rows, prefer: 'return=representation' });
    const outcomes = [];
    for (const signal of saved || []) {
      if (!signal.direction) continue;
      outcomes.push(...createOutcomeSchedule({ id: signal.id, as_of: result.as_of, price_at_signal: signal.price_at_signal, nifty_at_signal: signal.nifty_at_signal, sector_at_signal: signal.sector_at_signal }));
    }
    if (outcomes.length) await rest('live_alpha_signal_outcomes', { body: outcomes });
    return { run_id: runId, signals: rows.length, outcomes: outcomes.length };
  }
  async saveMomentumRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveVolumeAnomalyRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveOpeningRangeRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveMeanReversionRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveDerivativesRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
}
