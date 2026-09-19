import { calculateSignalOutcome } from './alphaOutcomeTracker.js';
import { CandlePriceBook, todayIst } from './candlePriceBook.js';
import { rest } from './liveAlphaPersistence.js';
import { sessionState } from './liveAlphaSession.js';
import { sectorKeyForLabel } from './liveAlphaRuntime.js';

/**
 * Settle Live Alpha outcome rows against Upstox one-minute history.
 *
 * Every signal with a direction gets seven outcome rows (5m to 5d), but
 * nothing ever settled them: by 19 Sep 2026 all 33,904 signals were still
 * pending, so the page could not say whether any engine worked. This job
 * prices each due row from the candle book, the morning after it falls due.
 *
 * A row is marked missed, never priced, when its measurement would mean
 * nothing: a signal issued outside the session (the weekend lists), an
 * anchor that does not match the market at the signal minute, or an
 * instrument with no history after three attempts.
 */

const MAX_ATTEMPTS = 3;
// A live quote and the minute candle it falls in can differ by a tick for an
// index and by a fast move for a stock; beyond this the anchor is not the
// price the market showed, and the return would be measured from nowhere.
const ANCHOR_TOLERANCE = Object.freeze({ stock: 0.03, nifty: 0.01, sector: 0.01 });
const WRITE_FIELDS = Object.freeze([
  'id', 'signal_id', 'horizon', 'due_at', 'price_at_signal', 'nifty_at_signal', 'sector_at_signal',
  'estimated_cost_bps', 'status', 'attempt_count', 'last_error', 'observed_at',
  'future_price', 'future_nifty', 'future_sector', 'stock_return_pct', 'market_return_pct',
  'sector_return_pct', 'directional_return_pct', 'market_adjusted_alpha_pct',
  'sector_adjusted_alpha_pct', 'net_alpha_pct', 'positive_outcome',
]);

/** Start of the current IST day; history before it is published. */
export function publishedBefore(now = new Date()) {
  return new Date(`${todayIst(new Date(now).getTime())}T00:00:00+05:30`).toISOString();
}

export function createOutcomeRepository({ request = rest } = {}) {
  return {
    async listDue(beforeIso, limit) {
      const params = new URLSearchParams({
        select: 'id,signal_id,horizon,due_at,attempt_count,price_at_signal,nifty_at_signal,sector_at_signal,estimated_cost_bps,signal:live_alpha_signals(symbol,instrument_key,sector,direction,beta,factor_values,run:live_alpha_runs(as_of))',
        status: 'eq.pending',
        due_at: `lt.${beforeIso}`,
        // Rows that could not be priced move behind fresh ones, so a few dead
        // instruments cannot hold the head of the queue.
        order: 'attempt_count.asc,due_at.asc',
        limit: String(limit),
      });
      return (await request('live_alpha_signal_outcomes', { method: 'GET', query: params.toString(), body: undefined, prefer: undefined })) || [];
    },
    async save(rows) {
      for (let index = 0; index < rows.length; index += 250) {
        await request('live_alpha_signal_outcomes', {
          query: 'on_conflict=id',
          body: rows.slice(index, index + 250),
          prefer: 'resolution=merge-duplicates,return=minimal',
        });
      }
    },
  };
}

function writeRow(row, patch) {
  const merged = { ...row, estimated_cost_bps: row.estimated_cost_bps ?? 0, last_error: null, observed_at: null, ...patch };
  return Object.fromEntries(WRITE_FIELDS.map((field) => [field, merged[field] ?? null]));
}

function mismatch(anchor, market, tolerance) {
  return Math.abs(Number(anchor) / market - 1) > tolerance;
}

/**
 * Settle one row. Returns { row, outcome } where outcome is completed,
 * missed or deferred; `row` is the full-shape write, or null to leave it.
 */
export async function settleOutcome(row, { book, universeBySymbol }) {
  const signal = row.signal || {};
  const asOf = signal.run?.as_of;
  const attempts = Number(row.attempt_count || 0) + 1;
  const missed = (reason) => ({ outcome: 'missed', reason, row: writeRow(row, { status: 'missed', attempt_count: attempts, last_error: reason }) });
  if (!asOf || !sessionState(asOf).open) return missed('signal_outside_session');
  if (!signal.direction) return missed('signal_without_direction');
  const member = universeBySymbol.get(signal.symbol);
  const keys = {
    stock: signal.instrument_key || member?.instrumentKey,
    nifty: 'NSE_INDEX|Nifty 50',
    // The key recorded with the signal, else the index for the sector label
    // stored with it. The symbol's current sector is the last resort: it
    // changed when the universe did, and priced 136 August bank signals
    // against Financial Services instead of Nifty Bank.
    sector: signal.factor_values?.sector_instrument_key || sectorKeyForLabel(signal.sector) || member?.sectorInstrumentKey,
  };
  if (!keys.stock || !keys.sector) return missed('instrument_not_mapped');

  const retry = (reason) => attempts >= MAX_ATTEMPTS
    ? missed(reason)
    : { outcome: 'deferred', reason, row: writeRow(row, { status: 'pending', attempt_count: attempts, last_error: reason }) };

  const anchors = { stock: row.price_at_signal, nifty: row.nifty_at_signal, sector: row.sector_at_signal };
  const future = {};
  for (const leg of ['stock', 'nifty', 'sector']) {
    const atSignal = await book.priceAt(keys[leg], asOf);
    if (atSignal.price == null) return atSignal.reason === 'before_first_candle' ? missed(`${leg}_before_first_candle`) : retry(`${leg}_${atSignal.reason}`);
    if (mismatch(anchors[leg], atSignal.price, ANCHOR_TOLERANCE[leg])) return missed(`${leg}_anchor_mismatch`);
    const atDue = await book.priceAt(keys[leg], row.due_at);
    if (atDue.price == null) return retry(`${leg}_${atDue.reason}`);
    future[leg] = atDue;
  }
  const result = calculateSignalOutcome({
    direction: signal.direction,
    priceAtSignal: anchors.stock,
    futurePrice: future.stock.price,
    niftyAtSignal: anchors.nifty,
    futureNifty: future.nifty.price,
    sectorAtSignal: anchors.sector,
    futureSector: future.sector.price,
    beta: signal.beta ?? 1,
    estimatedCostBps: row.estimated_cost_bps ?? 0,
  });
  return {
    outcome: 'completed',
    row: writeRow(row, {
      ...result,
      status: 'completed',
      attempt_count: attempts,
      observed_at: future.stock.candle_end,
      future_price: future.stock.price,
      future_nifty: future.nifty.price,
      future_sector: future.sector.price,
    }),
  };
}

export async function settleDueLiveAlphaOutcomes({ repository, book, universe, now = new Date(), limit = 500 }) {
  const due = await repository.listDue(publishedBefore(now), limit);
  const universeBySymbol = new Map((universe?.members || []).map((member) => [member.symbol, member]));
  const summary = { due: due.length, completed: 0, missed: 0, deferred: 0, reasons: {}, halted: null };
  const writes = [];
  for (const row of due) {
    let settled;
    try {
      settled = await settleOutcome(row, { book, universeBySymbol });
    } catch (error) {
      // A throttled or failing history call stops the batch; the rows keep
      // their place and the next cycle resumes after a pause.
      summary.halted = String(error?.message || error).slice(0, 200);
      break;
    }
    summary[settled.outcome] += 1;
    if (settled.reason) summary.reasons[settled.reason] = (summary.reasons[settled.reason] || 0) + 1;
    if (settled.row) writes.push(settled.row);
  }
  if (writes.length) await repository.save(writes);
  return summary;
}

let timer = null;
let state = { enabled: false, status: 'disabled', last_run: null, last_summary: null, last_error: null, totals: { completed: 0, missed: 0 } };

export function startLiveAlphaOutcomeScheduler({ loadUniverse }) {
  const enabled = String(process.env.LIVE_ALPHA_SHADOW_ENABLED || '').toLowerCase() === 'true'
    && String(process.env.LIVE_ALPHA_OUTCOMES_ENABLED || 'true').toLowerCase() !== 'false';
  if (!enabled || timer) { state.enabled = enabled; return state; }
  state = { ...state, enabled: true, status: 'idle' };
  const repository = createOutcomeRepository();
  const book = new CandlePriceBook();
  const schedule = (ms) => { timer = setTimeout(tick, ms); timer.unref?.(); };
  async function tick() {
    state.status = 'running';
    let next = 15 * 60_000;
    try {
      const universe = await loadUniverse();
      const summary = await settleDueLiveAlphaOutcomes({ repository, book, universe });
      state.totals = { completed: state.totals.completed + summary.completed, missed: state.totals.missed + summary.missed };
      state = { ...state, status: 'idle', last_run: new Date().toISOString(), last_summary: summary, last_error: summary.halted, candle_book: book.stats };
      // Work through a backlog steadily; otherwise look again in 15 minutes.
      if (summary.due >= 500 && !summary.halted) next = 30_000;
    } catch (error) {
      state = { ...state, status: 'degraded', last_run: new Date().toISOString(), last_error: error.message };
    }
    schedule(next);
  }
  schedule(90_000);
  return state;
}

export function getLiveAlphaOutcomeStatus() {
  return { ...state, research_only: true };
}
