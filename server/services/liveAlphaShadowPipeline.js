import { evaluateCrossSectionalMomentum, evaluateDerivativesPositioning, evaluateIntradayMeanReversion, evaluateOpeningRangeExpansion, evaluateVolumeLiquidityAnomaly } from './liveAlphaEngine.js';
import { minuteOfSession } from './minuteVolumeBaseline.js';

function change(current, previous) {
  return previous?.ltp > 0 ? ((current.ltp / previous.ltp) - 1) * 100 : null;
}

/** Upstox full-mode 1-minute candle interval labels observed in V3 feeds. */
function isOneMinuteInterval(interval) {
  return /^(1m|I1|1)$/i.test(String(interval || '').trim());
}

function sessionDateIst(ms) {
  return new Date(ms + 5.5 * 60 * 60_000).toISOString().slice(0, 10);
}

function compactFeaturePoint(point, at) {
  const finiteOrNull = (value) => {
    if (value == null || value === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  };
  return {
    instrument_key: String(point.instrument_key || ''),
    received_at: new Date(at).toISOString(),
    ltp: Number(point.ltp),
    cumulative_volume: finiteOrNull(point.cumulative_volume),
    open_interest: finiteOrNull(point.open_interest),
    spread_bps: finiteOrNull(point.spread_bps),
    implied_volatility: finiteOrNull(point.implied_volatility),
    source: point.source || 'live_feed',
  };
}

export class IntradayFeatureStore {
  constructor({ retentionMs = 2 * 60 * 60_000 } = {}) {
    this.retentionMs = retentionMs;
    this.series = new Map();
    this.openingRanges = new Map();
  }

  #touchOpeningRange(instrumentKey, session, high, low) {
    if (!(high > 0) || !(low > 0)) return;
    const rangeKey = `${session}|${instrumentKey}`;
    const range = this.openingRanges.get(rangeKey) || { high, low, observations: 0 };
    range.high = Math.max(range.high, high);
    range.low = Math.min(range.low, low);
    range.observations += 1;
    this.openingRanges.set(rangeKey, range);
  }

  /**
   * Upstox full mode ships marketOHLC (1m / 30m / 1d). Use 1m bars to:
   * - restore opening-range high/low after mid-session reconnects
   * - seed sparse price history so 15m/60m returns warm up faster than tick-only
   */
  #ingestOhlc(instrumentKey, ohlcRows, receivedAtMs) {
    if (!Array.isArray(ohlcRows) || !ohlcRows.length) return;
    const cutoff = receivedAtMs - this.retentionMs;
    for (const bar of ohlcRows) {
      if (!isOneMinuteInterval(bar.interval)) continue;
      const barMs = Number(bar.timestamp);
      if (!Number.isFinite(barMs) || barMs < cutoff || !(bar.close > 0)) continue;
      const minute = minuteOfSession(new Date(barMs).toISOString());
      if (minute >= 0 && minute < 15) {
        this.#touchOpeningRange(
          instrumentKey,
          sessionDateIst(barMs),
          bar.high ?? bar.close,
          bar.low ?? bar.close,
        );
      }
      this.#upsertPoint(instrumentKey, {
        instrument_key: instrumentKey,
        received_at: new Date(barMs).toISOString(),
        ltp: bar.close,
        cumulative_volume: null,
        open_interest: null,
        spread_bps: null,
        implied_volatility: null,
        source: 'upstox_ohlc_1m',
      }, barMs);
    }
  }

  #upsertPoint(instrumentKey, point, at) {
    const values = this.series.get(instrumentKey) || [];
    const minuteBucket = Math.floor(at / 60_000);
    let index = values.length - 1;
    while (index >= 0 && Math.floor(Date.parse(values[index].received_at) / 60_000) > minuteBucket) index -= 1;
    if (index >= 0 && Math.floor(Date.parse(values[index].received_at) / 60_000) === minuteBucket) {
      const existing = values[index];
      // Live ticks replace synthetic OHLC; never overwrite a live tick with OHLC.
      if (point.source === 'upstox_ohlc_1m' && existing.source !== 'upstox_ohlc_1m') {
        /* keep live */
      } else if (Date.parse(existing.received_at) > at) {
        /* keep the newest observation in this minute */
      } else {
        values[index] = compactFeaturePoint(point, at);
      }
    } else {
      values.splice(index + 1, 0, compactFeaturePoint(point, at));
    }
    const cutoff = at - this.retentionMs;
    while (values.length && Date.parse(values[0].received_at) < cutoff) values.shift();
    this.series.set(instrumentKey, values);
  }

  #seedLookback(instrumentKey, row, at) {
    const previous = Number(row.previous_close);
    if (!(previous > 0)) return;
    const existing = this.series.get(instrumentKey) || [];
    if (existing.length) return;
    const seed = {
      instrument_key: instrumentKey,
      ltp: previous,
      cumulative_volume: null,
      source: 'previous_close_seed',
    };
    this.#upsertPoint(instrumentKey, seed, at - 60 * 60_000);
    this.#upsertPoint(instrumentKey, seed, at - 15 * 60_000);
  }

  ingest(batch) {
    for (const row of batch?.snapshots || []) {
      const at = Date.parse(row.received_at);
      if (!Number.isFinite(at) || !(row.ltp > 0)) continue;
      this.#ingestOhlc(row.instrument_key, row.ohlc, at);
      this.#seedLookback(row.instrument_key, row, at);
      this.#upsertPoint(row.instrument_key, row, at);
      const minute = minuteOfSession(row.received_at);
      if (minute >= 0 && minute < 15) {
        this.#touchOpeningRange(row.instrument_key, sessionDateIst(at), row.ltp, row.ltp);
      }
    }
  }
  latest(key) { return this.series.get(key)?.at(-1) || null; }
  latestWithFinite(key, field) {
    const rows = this.series.get(key) || [];
    for (let index = rows.length - 1; index >= 0; index -= 1) {
      const value = rows[index]?.[field];
      if (value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))) return rows[index];
    }
    return null;
  }
  atOrBefore(key, timestamp) {
    const rows = this.series.get(key) || [];
    for (let index = rows.length - 1; index >= 0; index -= 1) if (Date.parse(rows[index].received_at) <= timestamp) return rows[index];
    return null;
  }
  returns(key, nowMs) {
    const current = this.latest(key);
    return current ? { current, return15m: change(current, this.atOrBefore(key, nowMs - 15 * 60_000)), return60m: change(current, this.atOrBefore(key, nowMs - 60 * 60_000)) } : null;
  }
  openingRange(key, now = new Date()) {
    const session = new Date(now.getTime() + 5.5 * 60 * 60_000).toISOString().slice(0, 10);
    return this.openingRanges.get(`${session}|${key}`) || null;
  }
  derivatives(key, nowMs) {
    const current = this.latest(key);
    const previous = this.atOrBefore(key, nowMs - 15 * 60_000);
    if (!(current?.ltp > 0) || !(previous?.ltp > 0) || !(current?.open_interest > 0) || !(previous?.open_interest > 0)) return null;
    return { current, priceReturn15m: ((current.ltp / previous.ltp) - 1) * 100, oiChange15m: ((current.open_interest / previous.open_interest) - 1) * 100 };
  }
}

export class MomentumShadowPipeline {
  constructor({ universe, benchmarkKey, featureStore = new IntradayFeatureStore(), baselineIndex, repository, intervalMs = 5 * 60_000 } = {}) {
    this.universe = universe || [];
    this.benchmarkKey = benchmarkKey;
    this.featureStore = featureStore;
    this.baselineIndex = baselineIndex;
    this.repository = repository;
    this.intervalMs = intervalMs;
    this.lastRunBucket = null;
  }
  ingest(batch) { this.featureStore.ingest(batch); }
  async persistEngines(entries, diagnostics) {
    const persistence = [];
    for (const entry of entries) {
      if (!entry.result || typeof this.repository?.[entry.method] !== 'function') {
        persistence.push({ engine: entry.engine, status: 'unavailable', reason: entry.reason || 'insufficient_input_coverage' });
        continue;
      }
      try {
        const stored = await this.repository[entry.method](entry.result, diagnostics);
        persistence.push({ engine: entry.engine, status: 'stored', ...stored });
      } catch (error) {
        // Engines are independent research observations. A storage failure in
        // one must not prevent the remaining engines from being evaluated and
        // persisted in the same five-minute bucket.
        persistence.push({ engine: entry.engine, status: 'failed', error: error.message });
      }
    }
    return persistence;
  }
  async evaluate(now = new Date()) {
    const bucket = Math.floor(now.getTime() / this.intervalMs);
    if (bucket === this.lastRunBucket) return { skipped: true, reason: 'already_evaluated_bucket' };
    const benchmark = this.featureStore.returns(this.benchmarkKey, now.getTime());
    if (!benchmark || benchmark.return15m === null || benchmark.return60m === null) return { skipped: true, reason: 'benchmark_history_incomplete' };
    const minute = minuteOfSession(now.toISOString());
    const snapshots = [];
    const coverageDiagnostics = { stock_history: 0, sector_history: 0, sector_proxy: 0, volume_tick: 0, volume_baseline: 0, complete: 0 };
    for (const member of this.universe) {
      const stock = this.featureStore.returns(member.instrumentKey, now.getTime());
      const sector = this.featureStore.returns(member.sectorInstrumentKey, now.getTime());
      const sectorReady = sector && Number.isFinite(Number(sector.return15m)) && Number.isFinite(Number(sector.return60m));
      const effectiveSector = sectorReady ? sector : benchmark;
      const expected = this.baselineIndex?.get(member.instrumentKey, minute);
      const volumePoint = this.featureStore.latestWithFinite(member.instrumentKey, 'cumulative_volume');
      if (stock && Number.isFinite(Number(stock.return15m)) && Number.isFinite(Number(stock.return60m))) coverageDiagnostics.stock_history += 1;
      if (sectorReady) coverageDiagnostics.sector_history += 1;
      else coverageDiagnostics.sector_proxy += 1;
      if (volumePoint) coverageDiagnostics.volume_tick += 1;
      if (Number.isFinite(Number(expected)) && expected > 0) coverageDiagnostics.volume_baseline += 1;
      if (!stock || [stock.return15m, stock.return60m, effectiveSector.return15m, effectiveSector.return60m, expected, volumePoint?.cumulative_volume].every((value) => Number.isFinite(Number(value))) === false || expected <= 0) continue;
      coverageDiagnostics.complete += 1;
      snapshots.push({
        symbol: member.symbol, sector: member.sector, instrumentKey: member.instrumentKey,
        return15m: stock.return15m, return60m: stock.return60m,
        benchmarkReturn15m: benchmark.return15m, benchmarkReturn60m: benchmark.return60m,
        sectorReturn15m: effectiveSector.return15m, sectorReturn60m: effectiveSector.return60m,
        sectorProxyUsed: !sectorReady,
        cumulativeVolume: volumePoint.cumulative_volume, expectedCumulativeVolume: expected,
        spreadBps: stock.current.spread_bps ?? volumePoint.spread_bps, minimumLiquidity: member.minimumLiquidity !== false,
      });
    }
    const minimumCoverage = Math.max(10, Math.ceil(this.universe.length * 0.8));
    if (snapshots.length < minimumCoverage) return { skipped: true, reason: 'insufficient_complete_universe', coverage: snapshots.length, required_coverage: minimumCoverage, coverage_diagnostics: coverageDiagnostics };
    const result = evaluateCrossSectionalMomentum(snapshots, { asOf: now.toISOString() });
    const volumeResult = evaluateVolumeLiquidityAnomaly(snapshots, { asOf: now.toISOString() });
    const meanReversionResult = evaluateIntradayMeanReversion(snapshots, { asOf: now.toISOString() });
    const derivativeSnapshots = this.universe.map((member) => {
      if (!member.derivativeInstrumentKey) return null;
      const derivative = this.featureStore.derivatives(member.derivativeInstrumentKey, now.getTime());
      return derivative ? { symbol: member.symbol, sector: member.sector, instrumentKey: member.derivativeInstrumentKey, priceReturn15m: derivative.priceReturn15m, oiChange15m: derivative.oiChange15m, openInterest: derivative.current.open_interest, impliedVolatility: derivative.current.implied_volatility, spreadBps: derivative.current.spread_bps, minimumLiquidity: member.minimumLiquidity !== false } : null;
    }).filter(Boolean);
    const derivativesResult = derivativeSnapshots.length >= 10 ? evaluateDerivativesPositioning(derivativeSnapshots, { asOf: now.toISOString() }) : null;
    const openingSnapshots = snapshots.map((snapshot) => {
      const range = this.featureStore.openingRange(snapshot.instrumentKey, now);
      const current = this.featureStore.latest(snapshot.instrumentKey);
      return range ? { ...snapshot, currentPrice: current?.ltp, openingHigh: range.high, openingLow: range.low } : null;
    }).filter(Boolean);
    const openingResult = openingSnapshots.length >= 10 ? evaluateOpeningRangeExpansion(openingSnapshots, { asOf: now.toISOString() }) : null;
    const openingRangeReason = openingSnapshots.length
      ? `insufficient_opening_range_coverage:${openingSnapshots.length}/10`
      : 'genuine_session_opening_observations_unavailable';
    const anchors = new Map(this.universe.map((member) => {
      const stock = this.featureStore.latest(member.instrumentKey);
      const sector = this.featureStore.latest(member.sectorInstrumentKey);
      return [member.symbol, { stock, sector }];
    }));
    result.signals = result.signals.map((signal) => {
      const anchor = anchors.get(signal.symbol);
      return {
        ...signal,
        direction: signal.classification === 'positive_research_candidate' ? 'positive' : signal.classification === 'negative_research_candidate' ? 'negative' : null,
        price_at_signal: anchor?.stock?.ltp ?? null,
        nifty_at_signal: benchmark.current.ltp,
        sector_at_signal: anchor?.sector?.ltp ?? null,
      };
    });
    volumeResult.signals = volumeResult.signals.map((signal) => {
      const anchor = anchors.get(signal.symbol);
      const candidate = signal.classification === 'abnormal_accumulation_candidate' || signal.classification === 'abnormal_distribution_candidate';
      return {
        ...signal,
        direction: !candidate ? null : signal.classification === 'abnormal_accumulation_candidate' ? 'positive' : 'negative',
        price_at_signal: anchor?.stock?.ltp ?? null,
        nifty_at_signal: benchmark.current.ltp,
        sector_at_signal: anchor?.sector?.ltp ?? null,
      };
    });
    if (openingResult) openingResult.signals = openingResult.signals.map((signal) => {
      const anchor = anchors.get(signal.symbol);
      const positive = signal.classification === 'upside_opening_breakout_candidate';
      const negative = signal.classification === 'downside_opening_breakout_candidate';
      return { ...signal, direction: positive ? 'positive' : negative ? 'negative' : null, price_at_signal: anchor?.stock?.ltp ?? null, nifty_at_signal: benchmark.current.ltp, sector_at_signal: anchor?.sector?.ltp ?? null };
    });
    meanReversionResult.signals = meanReversionResult.signals.map((signal) => {
      const anchor = anchors.get(signal.symbol);
      const positive = signal.classification === 'negative_shock_rebound_candidate';
      const negative = signal.classification === 'positive_shock_pullback_candidate';
      return { ...signal, direction: positive ? 'positive' : negative ? 'negative' : null, price_at_signal: anchor?.stock?.ltp ?? null, nifty_at_signal: benchmark.current.ltp, sector_at_signal: anchor?.sector?.ltp ?? null };
    });
    if (derivativesResult) derivativesResult.signals = derivativesResult.signals.map((signal) => {
      const positive = signal.classification === 'long_buildup_candidate' || signal.classification === 'short_covering_candidate';
      const negative = signal.classification === 'short_buildup_candidate' || signal.classification === 'long_unwinding_candidate';
      const member = this.universe.find((row) => row.symbol === signal.symbol);
      const stock = this.featureStore.latest(member?.instrumentKey);
      const sector = this.featureStore.latest(member?.sectorInstrumentKey);
      return { ...signal, direction: positive ? 'positive' : negative ? 'negative' : null, price_at_signal: stock?.ltp ?? null, nifty_at_signal: benchmark.current.ltp, sector_at_signal: sector?.ltp ?? null };
    });
    this.lastRunBucket = bucket;
    const diagnostics = { benchmark_key: this.benchmarkKey, minute_of_session: minute };
    const persistence = await this.persistEngines([
      { engine: result.engine, method: 'saveMomentumRun', result },
      { engine: volumeResult.engine, method: 'saveVolumeAnomalyRun', result: volumeResult },
      { engine: 'opening_range_expansion_v1', method: 'saveOpeningRangeRun', result: openingResult, reason: openingRangeReason },
      { engine: meanReversionResult.engine, method: 'saveMeanReversionRun', result: meanReversionResult },
      { engine: 'derivatives_positioning_v1', method: 'saveDerivativesRun', result: derivativesResult, reason: derivativeSnapshots.length ? 'insufficient_derivative_coverage' : 'derivative_instruments_not_configured' },
    ], diagnostics);
    return {
      ...result,
      companion_engines: [volumeResult, ...(openingResult ? [openingResult] : []), meanReversionResult, ...(derivativesResult ? [derivativesResult] : [])],
      persistence,
      coverage_diagnostics: coverageDiagnostics,
      opening_range_status: openingResult ? 'running' : openingRangeReason,
      derivatives_status: derivativesResult ? 'running' : derivativeSnapshots.length ? 'insufficient_derivative_coverage' : 'derivative_instruments_not_configured',
    };
  }
}
