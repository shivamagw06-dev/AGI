import { evaluateCrossSectionalMomentum, evaluateOpeningRangeExpansion, evaluateVolumeLiquidityAnomaly } from './liveAlphaEngine.js';
import { minuteOfSession } from './minuteVolumeBaseline.js';

function change(current, previous) {
  return previous?.ltp > 0 ? ((current.ltp / previous.ltp) - 1) * 100 : null;
}

export class IntradayFeatureStore {
  constructor({ retentionMs = 2 * 60 * 60_000 } = {}) {
    this.retentionMs = retentionMs;
    this.series = new Map();
    this.openingRanges = new Map();
  }
  ingest(batch) {
    for (const row of batch?.snapshots || []) {
      const at = Date.parse(row.received_at);
      if (!Number.isFinite(at) || !(row.ltp > 0)) continue;
      const values = this.series.get(row.instrument_key) || [];
      const last = values.at(-1);
      if (!last || Date.parse(last.received_at) < at) values.push(row);
      const cutoff = at - this.retentionMs;
      while (values.length && Date.parse(values[0].received_at) < cutoff) values.shift();
      this.series.set(row.instrument_key, values);
      const minute = minuteOfSession(row.received_at);
      const session = new Date(at + 5.5 * 60 * 60_000).toISOString().slice(0, 10);
      if (minute >= 0 && minute < 15) {
        const rangeKey = `${session}|${row.instrument_key}`;
        const range = this.openingRanges.get(rangeKey) || { high: row.ltp, low: row.ltp, observations: 0 };
        range.high = Math.max(range.high, row.ltp); range.low = Math.min(range.low, row.ltp); range.observations += 1;
        this.openingRanges.set(rangeKey, range);
      }
    }
  }
  latest(key) { return this.series.get(key)?.at(-1) || null; }
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
  async evaluate(now = new Date()) {
    const bucket = Math.floor(now.getTime() / this.intervalMs);
    if (bucket === this.lastRunBucket) return { skipped: true, reason: 'already_evaluated_bucket' };
    const benchmark = this.featureStore.returns(this.benchmarkKey, now.getTime());
    if (!benchmark || benchmark.return15m === null || benchmark.return60m === null) return { skipped: true, reason: 'benchmark_history_incomplete' };
    const minute = minuteOfSession(now.toISOString());
    const snapshots = [];
    for (const member of this.universe) {
      const stock = this.featureStore.returns(member.instrumentKey, now.getTime());
      const sector = this.featureStore.returns(member.sectorInstrumentKey, now.getTime());
      const expected = this.baselineIndex?.get(member.instrumentKey, minute);
      if (!stock || !sector || [stock.return15m, stock.return60m, sector.return15m, sector.return60m, expected, stock.current.cumulative_volume].every((value) => Number.isFinite(Number(value))) === false || expected <= 0) continue;
      snapshots.push({
        symbol: member.symbol, sector: member.sector, instrumentKey: member.instrumentKey,
        return15m: stock.return15m, return60m: stock.return60m,
        benchmarkReturn15m: benchmark.return15m, benchmarkReturn60m: benchmark.return60m,
        sectorReturn15m: sector.return15m, sectorReturn60m: sector.return60m,
        cumulativeVolume: stock.current.cumulative_volume, expectedCumulativeVolume: expected,
        spreadBps: stock.current.spread_bps, minimumLiquidity: member.minimumLiquidity !== false,
      });
    }
    if (snapshots.length < 10) return { skipped: true, reason: 'insufficient_complete_universe', coverage: snapshots.length };
    const result = evaluateCrossSectionalMomentum(snapshots, { asOf: now.toISOString() });
    const volumeResult = evaluateVolumeLiquidityAnomaly(snapshots, { asOf: now.toISOString() });
    const openingSnapshots = snapshots.map((snapshot) => {
      const range = this.featureStore.openingRange(snapshot.instrumentKey, now);
      const current = this.featureStore.latest(snapshot.instrumentKey);
      return range ? { ...snapshot, currentPrice: current?.ltp, openingHigh: range.high, openingLow: range.low } : null;
    }).filter(Boolean);
    const openingResult = openingSnapshots.length >= 10 ? evaluateOpeningRangeExpansion(openingSnapshots, { asOf: now.toISOString() }) : null;
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
    this.lastRunBucket = bucket;
    await this.repository?.saveMomentumRun?.(result, { benchmark_key: this.benchmarkKey, minute_of_session: minute });
    await this.repository?.saveVolumeAnomalyRun?.(volumeResult, { benchmark_key: this.benchmarkKey, minute_of_session: minute });
    if (openingResult) await this.repository?.saveOpeningRangeRun?.(openingResult, { benchmark_key: this.benchmarkKey, minute_of_session: minute });
    return { ...result, companion_engines: [volumeResult, ...(openingResult ? [openingResult] : [])] };
  }
}
