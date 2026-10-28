import { sessionState, istDateKey } from './liveAlphaSession.js';

export const RADAR_VERSION = 'early-range-v1';
export const RADAR_INTERVAL_MS = 30_000;
const pct = (a, b) => (a / b - 1) * 100;
const valid = n => Number.isFinite(n) && n > 0;

// Completed prior minutes only. The current observation cannot set its own level.
export function setupInputs({ points = [], benchmark = [], quote, now }) {
  const at = now.getTime(), minute = Math.floor(at / 60000) * 60000;
  const prior = points.filter(p => {
    const t = Date.parse(p.received_at);
    return t >= minute - 15 * 60000 && t < minute && istDateKey(t) === istDateKey(at) && valid(p.ltp);
  });
  const buckets = new Set(prior.map(p => Math.floor(Date.parse(p.received_at) / 60000)));
  if (buckets.size < 15) return { blocked: 'Need 15 complete prior minutes' };
  const qt = Date.parse(quote?.effective_timestamp || quote?.exchange_timestamp);
  if (!valid(quote?.ltp) || !Number.isFinite(qt) || at - qt < 0 || at - qt > 30000 || istDateKey(qt) !== istDateKey(at)) return { blocked: 'Quote older than 30 seconds or missing exchange time' };
  const bid = Number(quote.best_bid), ask = Number(quote.best_ask);
  if (!valid(bid) || !valid(ask) || ask < bid || pct(ask, bid) > 0.2) return { blocked: 'Missing, crossed or wide bid/ask' };
  const bm = benchmark.filter(p => Date.parse(p.received_at) <= at && at - Date.parse(p.received_at) <= 30000).at(-1);
  const oldBm = benchmark.filter(p => Date.parse(p.received_at) <= minute - 15 * 60000 && minute - 15 * 60000 - Date.parse(p.received_at) <= 60000).at(-1);
  if (!valid(bm?.ltp) || !valid(oldBm?.ltp) || istDateKey(oldBm.received_at) !== istDateKey(at)) return { blocked: 'Benchmark not ready' };
  const high = Math.max(...prior.map(p => p.ltp)), low = Math.min(...prior.map(p => p.ltp));
  const width = pct(high, low);
  if (width > 1.5 || width < 0.1) return { blocked: 'Prior range outside setup limits' };
  // Use actual cumulative-volume observations; reconstructed OHLC has no volume here.
  const first = prior[0], last = prior.at(-1);
  const elapsed = (Date.parse(last.received_at) - Date.parse(first.received_at)) / 60000;
  const recentMinutes = (qt - Date.parse(last.received_at)) / 60000;
  const volumeDelta = Number(quote.cumulative_volume) - Number(last.cumulative_volume);
  const baselineDelta = Number(last.cumulative_volume) - Number(first.cumulative_volume);
  if (first.cumulative_volume == null || last.cumulative_volume == null || quote.cumulative_volume == null || elapsed < 10 || recentMinutes < 0.25 || recentMinutes > 2 || volumeDelta < 0 || baselineDelta <= 0) return { blocked: 'Live volume history not ready' };
  const participation = (volumeDelta / recentMinutes) / (baselineDelta / elapsed);
  const relative = pct(quote.ltp, first.ltp) - pct(bm.ltp, oldBm.ltp);
  const direction = relative >= 0 ? 'positive' : 'negative';
  const level = direction === 'positive' ? high : low;
  return { direction, level, width, high, low, participation, relative, price: quote.ltp, quote_at: new Date(qt).toISOString(),
    distance: (direction === 'positive' ? 1 : -1) * pct(quote.ltp, level), range_basis: 'prior 15 minute sampled prices' };
}

export class EarlyRadar {
  constructor({ featureStore, quoteStore, universe, benchmarkKey, save = async () => {} }) {
    Object.assign(this, { featureStore, quoteStore, universe, benchmarkKey, save });
    this.episodes = new Map(); this.events = []; this.lastBucket = null; this.lastAt = null;
    this.coverage = {}; this.storageError = null;
  }
  restore(state) {
    if (state?.version !== RADAR_VERSION) return;
    this.events = (state.events || []).slice(-20000);
    this.episodes = new Map((state.episodes || []).map(e => [e.symbol, e]));
  }
  event(row, stage, now, extra = {}) {
    row.stage = stage; row.updated_at = now.toISOString(); Object.assign(row, extra);
    this.events.push({ ...row, event_at: now.toISOString() });
    if (this.events.length > 20000) this.events.shift();
  }
  async evaluate(now = new Date()) {
    if (!sessionState(now).open) return;
    const bucket = Math.floor(now.getTime() / RADAR_INTERVAL_MS);
    if (bucket === this.lastBucket) return;
    this.lastBucket = bucket; this.lastAt = now.toISOString();
    const coverage = { checked: this.universe.length, eligible: 0, blocked: {} };
    for (const member of this.universe) {
      let row = this.episodes.get(member.symbol);
      if (row && row.session !== istDateKey(now)) {
        if (['watch', 'triggered', 'confirmed'].includes(row.stage)) this.event(row, 'expired', now, { reason: 'Prior session ended; no closing execution assumed' });
        this.episodes.delete(member.symbol); row = null;
      }
      const quote = this.quoteStore.get(member.instrumentKey);
      const qtime = Date.parse(quote?.effective_timestamp || quote?.exchange_timestamp);
      const fresh = valid(quote?.ltp) && Number.isFinite(qtime) && now.getTime() - qtime >= 0 && now.getTime() - qtime <= 30000;
      // Follow triggered episodes even if the setup range or volume has changed.
      if (row?.trigger_at && !['failed', 'expired'].includes(row.stage)) {
        if (fresh) {
          row.current_price = quote.ltp; row.quote_at = new Date(qtime).toISOString();
          const sign = row.direction === 'positive' ? 1 : -1;
          row.return_pct = sign * pct(quote.ltp, row.trigger_price);
          row.best_return_pct = Math.max(row.best_return_pct || 0, row.return_pct);
          row.worst_return_pct = Math.min(row.worst_return_pct || 0, row.return_pct);
          if (sign * pct(quote.ltp, row.level) <= -0.15) this.event(row, 'failed', now, { reason: 'Price crossed back through frozen breakout level' });
          else if (now - Date.parse(row.trigger_at) >= 60 * 60000) this.event(row, 'expired', now, { reason: 'One-hour observation window ended' });
          else if (row.stage === 'triggered' && now - Date.parse(row.trigger_at) >= 60000 && row.return_pct >= 0.15) this.event(row, 'confirmed', now, { reason: 'At least one minute and 0.15% follow-through' });
        }
        continue;
      }
      if (row && ['failed', 'expired', 'extended'].includes(row.stage) && now - Date.parse(row.updated_at) < 15 * 60000) continue;
      const inputs = setupInputs({ points: this.featureStore.series.get(member.instrumentKey), benchmark: this.featureStore.series.get(this.benchmarkKey), quote, now });
      if (inputs.blocked) {
        coverage.blocked[inputs.blocked] = (coverage.blocked[inputs.blocked] || 0) + 1;
        if (row?.stage === 'watch' && now - Date.parse(row.started_at) > 10 * 60000) this.event(row, 'expired', now, { reason: inputs.blocked });
        continue;
      }
      coverage.eligible++;
      const { direction, price, participation, relative } = inputs;
      // Freeze levels once a watch is published; moving levels cannot revise history.
      const watching = row?.stage === 'watch' && row.direction === direction;
      const level = watching ? row.level : inputs.level;
      const distance = (direction === 'positive' ? 1 : -1) * pct(price, level);
      if (watching && now - Date.parse(row.started_at) > 10 * 60000) { this.event(row, 'expired', now, { reason: 'Watch expired after ten minutes' }); continue; }
      const near = distance >= -0.2 && distance < 0.08 && participation >= 1.2 && Math.abs(relative) >= 0.1;
      const crossed = distance >= 0.08 && participation >= 1.5 && Math.abs(relative) >= 0.2;
      if (!near && !crossed) continue;
      if (!watching) {
        if (row?.stage === 'watch') this.event(row, 'expired', now, { reason: 'Setup direction changed' });
        row = { symbol: member.symbol, session: istDateKey(now), version: RADAR_VERSION, direction, level,
          started_at: now.toISOString(), initial_price: price, stage: 'watch', range_basis: inputs.range_basis };
        this.episodes.set(member.symbol, row);
      }
      Object.assign(row, { current_price: price, quote_at: inputs.quote_at, participation, relative, distance });
      if (crossed && distance > 0.6) this.event(row, 'extended', now, { reason: 'More than 0.6% beyond level; do not treat as a fresh trigger' });
      else if (crossed) this.event(row, 'triggered', now, { trigger_at: now.toISOString(), trigger_price: price, return_pct: 0, best_return_pct: 0, worst_return_pct: 0, reason: 'Level crossed with participation and relative strength' });
      else if (!watching) this.event(row, 'watch', now, { reason: 'Near range boundary with improving participation' });
    }
    this.coverage = coverage;
    try { await this.save({ version: RADAR_VERSION, episodes: [...this.episodes.values()], events: this.events }); this.storageError = null; }
    catch { this.storageError = 'Radar history write failed; transitions are pending retry'; }
  }
  snapshot(now = new Date()) {
    const open = sessionState(now).open;
    return { version: RADAR_VERSION, research_only: true, interval_seconds: 30, evaluated_at: this.lastAt,
      market_open: open, stale: !this.lastAt || now - Date.parse(this.lastAt) > 90000, storage_error: this.storageError,
      coverage: this.coverage, rows: [...this.episodes.values()].map(row => ({ ...row,
        quote_stale: !row.quote_at || now - Date.parse(row.quote_at) > 30000 })),
      events: this.events.slice(-100).reverse(), note: 'Experimental rules. No calibrated win probability; returns are observed price changes before costs, not trades.' };
  }
}
