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

async function writeChunks(table, rows, options = {}, chunkSize = 250) {
  const output = [];
  for (let index = 0; index < rows.length; index += chunkSize) {
    const saved = await rest(table, { ...options, body: rows.slice(index, index + chunkSize) });
    if (Array.isArray(saved)) output.push(...saved);
  }
  return output;
}

export async function pagedGet(table, baseParams, { limit = 5000, pageSize = 1000 } = {}) {
  const rows = [];
  while (rows.length < limit) {
    const size = Math.min(pageSize, limit - rows.length);
    const params = new URLSearchParams(baseParams);
    params.set('limit', String(size));
    params.set('offset', String(rows.length));
    const page = await rest(table, { method: 'GET', query: params.toString(), body: undefined, prefer: undefined }) || [];
    rows.push(...page);
    if (page.length < size) break;
  }
  return rows;
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
        ltp: item.ltp, previous_close: item.previous_close ?? null, last_traded_quantity: item.last_traded_quantity ?? null,
        average_traded_price: item.average_traded_price ?? null, cumulative_volume: item.cumulative_volume ?? null,
        open_interest: item.open_interest ?? null, implied_volatility: item.implied_volatility ?? null,
        best_bid: item.best_bid ?? null, best_ask: item.best_ask ?? null, spread_bps: item.spread_bps ?? null,
        feed_latency_ms: item.feed_latency_ms ?? null,
        raw_factors: { ohlc: item.ohlc, total_buy_quantity: item.total_buy_quantity, total_sell_quantity: item.total_sell_quantity, request_mode: item.request_mode },
      });
    }
    // The database intentionally keeps one observation per instrument/minute.
    // Feed reconnects and overlapping batches can legitimately replay that
    // minute, so make the write idempotent at the database boundary as well as
    // in this process. This also protects against two live workers briefly
    // overlapping during a rolling deploy.
    if (rows.length) await writeChunks('live_market_snapshots', rows, {
      query: 'on_conflict=instrument_key,minute_bucket',
      prefer: 'resolution=merge-duplicates,return=minimal',
    });
    return rows.length;
  }
  async saveHealth(status, staleInstruments = 0) {
    await rest('live_market_feed_health', { body: { status: status.status, subscribed_instruments: status.subscribed_instruments, messages: status.messages, decode_errors: status.decode_errors, reconnects: status.reconnects, last_message_at: status.last_message_at, stale_instruments: staleInstruments, diagnostics: { last_error: status.last_error, mode: status.mode } } });
  }
  async loadVolumeBaselines({ limit = 20_000 } = {}) {
    return pagedGet('live_volume_baselines', {
      select: 'instrument_key,minute_of_session,expected_cumulative_volume,sample_sessions',
      order: 'instrument_key.asc,minute_of_session.asc',
    }, { limit });
  }
  async saveVolumeBaselines(rows = []) {
    if (!rows.length) return 0;
    await writeChunks('live_volume_baselines', rows, {
      query: 'on_conflict=instrument_key,minute_of_session',
      prefer: 'resolution=merge-duplicates,return=minimal',
    });
    return rows.length;
  }
  async loadRecentSnapshots({ minutes = 90, limit = 5000 } = {}) {
    const since = new Date(Date.now() - Math.max(1, minutes) * 60_000).toISOString();
    const params = {
      select: 'instrument_key,observed_at,exchange_timestamp,ltp,previous_close,last_traded_quantity,average_traded_price,cumulative_volume,open_interest,implied_volatility,best_bid,best_ask,spread_bps,feed_latency_ms,raw_factors',
      observed_at: `gte.${since}`,
      order: 'observed_at.asc',
    };
    const rows = await pagedGet('live_market_snapshots', params, { limit: Math.max(1, limit) });
    return (rows || []).map((row) => ({
      ...row,
      received_at: row.observed_at,
      ohlc: row.raw_factors?.ohlc || null,
      total_buy_quantity: row.raw_factors?.total_buy_quantity ?? null,
      total_sell_quantity: row.raw_factors?.total_sell_quantity ?? null,
      request_mode: row.raw_factors?.request_mode || null,
    }));
  }
  async loadSessionOpeningSnapshots({ now = new Date(), limit = 1000 } = {}) {
    const shifted = new Date(now.getTime() + 5.5 * 60 * 60_000);
    const session = shifted.toISOString().slice(0, 10);
    const start = new Date(`${session}T03:45:00.000Z`).toISOString();
    const end = new Date(`${session}T04:00:00.000Z`).toISOString();
    const query = new URLSearchParams({
      select: 'instrument_key,observed_at,exchange_timestamp,ltp,previous_close,last_traded_quantity,average_traded_price,cumulative_volume,open_interest,implied_volatility,best_bid,best_ask,spread_bps,feed_latency_ms,raw_factors',
      observed_at: `gte.${start}`,
      and: `(observed_at.lt.${end})`,
      order: 'observed_at.asc',
      limit: String(Math.max(1, limit)),
    }).toString();
    const rows = await rest('live_market_snapshots', { method: 'GET', query, body: undefined, prefer: undefined });
    return (rows || []).map((row) => ({
      ...row,
      received_at: row.observed_at,
      ohlc: row.raw_factors?.ohlc || null,
      total_buy_quantity: row.raw_factors?.total_buy_quantity ?? null,
      total_sell_quantity: row.raw_factors?.total_sell_quantity ?? null,
      request_mode: row.raw_factors?.request_mode || null,
    }));
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
    try {
      const saved = await writeChunks('live_alpha_signals', rows, { prefer: 'return=representation' });
      const outcomes = [];
      let outcomeSkipped = 0;
      for (const signal of saved || []) {
        if (!signal.direction) continue;
        const anchors = [signal.price_at_signal, signal.nifty_at_signal, signal.sector_at_signal].map(Number);
        // A research signal remains useful even when an outcome anchor is not
        // available. Persist it, but do not create an invalid validation row or
        // allow it to stop the other independent alpha engines.
        if (anchors.some((value) => !Number.isFinite(value) || value <= 0)) {
          outcomeSkipped += 1;
          continue;
        }
        outcomes.push(...createOutcomeSchedule({ id: signal.id, as_of: result.as_of, price_at_signal: signal.price_at_signal, nifty_at_signal: signal.nifty_at_signal, sector_at_signal: signal.sector_at_signal }));
      }
      if (outcomes.length) await writeChunks('live_alpha_signal_outcomes', outcomes);
      return { run_id: runId, signals: rows.length, outcomes: outcomes.length, outcome_skipped: outcomeSkipped };
    } catch (error) {
      // REST inserts cannot atomically create a run and its signal rows. Remove
      // the parent on any downstream failure so dashboards never treat an
      // orphan run as a successful engine evaluation. FK cascades clean up any
      // partially inserted signal/outcome rows.
      try {
        await rest('live_alpha_runs', {
          method: 'DELETE', query: `id=eq.${encodeURIComponent(runId)}`,
          body: undefined, prefer: 'return=minimal',
        });
      } catch (cleanupError) {
        error.cleanup_error = cleanupError.message;
      }
      throw error;
    }
  }
  async saveMomentumRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveVolumeAnomalyRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveOpeningRangeRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveMeanReversionRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
  async saveDerivativesRun(result, diagnostics = {}) { return this.saveAlphaRun(result, diagnostics); }
}
