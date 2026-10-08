import { sessionState } from './liveAlphaSession.js';
import { parse } from 'csv-parse/sync';
import { getQuote, isGrowwConfigured } from '../providers/groww.js';
import { pollGrowwIndexSnapshots, growwQuotePreviousClose } from './sectorIndexGrowwFallback.js';

const INSTRUMENTS_URL = process.env.GROWW_INSTRUMENTS_URL || 'https://growwapi-assets.groww.in/instruments/instrument.csv';

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function positiveNumber(value) {
  const parsed = number(value);
  return parsed > 0 ? parsed : null;
}

import { normalizeSpreadBps } from './marketSpread.js';

// Re-exported: existing callers and tests import it from this module.
export { normalizeSpreadBps };

export function normalizeExchangeTimestamp(value) {
  const parsed = number(value);
  if (!(parsed > 0)) return null;
  if (parsed < 10_000_000_000) return parsed * 1_000;
  if (parsed > 10_000_000_000_000) return Math.floor(parsed / 1_000);
  return parsed;
}

function ohlc(value) {
  if (!value) return [];
  if (typeof value === 'object') return [value];
  try { return [JSON.parse(String(value).replace(/([a-zA-Z_]+)\s*:/g, '"$1":'))]; } catch { return []; }
}

function normalizeQuote(instrumentKey, quote, receivedAt) {
  const bid = number(quote?.bid_price ?? quote?.depth?.buy?.[0]?.price);
  const ask = number(quote?.offer_price ?? quote?.depth?.sell?.[0]?.price);
  const ltp = number(quote?.last_price);
  if (!(ltp > 0)) return null;
  return {
    instrument_key: instrumentKey, received_at: receivedAt,
    exchange_timestamp: normalizeExchangeTimestamp(quote?.last_trade_time), ltp,
    previous_close: growwQuotePreviousClose(quote),
    last_traded_quantity: number(quote?.last_trade_quantity),
    average_traded_price: positiveNumber(quote?.average_price),
    cumulative_volume: number(quote?.volume), open_interest: number(quote?.open_interest),
    implied_volatility: number(quote?.implied_volatility), best_bid: bid, best_ask: ask,
    spread_bps: normalizeSpreadBps(bid, ask),
    total_buy_quantity: number(quote?.total_buy_quantity), total_sell_quantity: number(quote?.total_sell_quantity),
    ohlc: ohlc(quote?.ohlc), request_mode: 'groww_quote', source: 'groww',
  };
}

async function nearestFutures(fetchImpl = globalThis.fetch) {
  const response = await fetchImpl(INSTRUMENTS_URL, { signal: AbortSignal.timeout(60_000) });
  if (!response.ok) throw new Error(`Groww instrument master failed (${response.status}).`);
  const rows = parse(await response.text(), { columns: true, skip_empty_lines: true, relax_column_count: true });
  const today = new Date().toISOString().slice(0, 10);
  const futures = new Map();
  for (const row of rows) {
    if (row.exchange !== 'NSE' || row.segment !== 'FNO' || row.instrument_type !== 'FUT' || row.expiry_date < today) continue;
    const current = futures.get(row.underlying_symbol);
    if (!current || row.expiry_date < current.expiry_date) futures.set(row.underlying_symbol, row);
  }
  return futures;
}

export async function attachGrowwDerivatives(universe, options = {}) {
  if (!isGrowwConfigured()) return universe;
  const futures = await nearestFutures(options.fetchImpl);
  const members = universe.members.map((member) => {
    const future = futures.get(member.symbol);
    return future ? {
      ...member,
      growwDerivativeInstrumentKey: `GROWW_FNO|${future.exchange_token}`,
      growwDerivativeTradingSymbol: future.trading_symbol,
      growwDerivativeExpiry: future.expiry_date,
    } : member;
  });
  const resolved = members.filter((row) => row.growwDerivativeTradingSymbol).length;
  return { ...universe, members, growwDerivativeResolution: { status: resolved >= 10 ? 'ready' : 'insufficient', resolved, missing: members.length - resolved } };
}

export class GrowwLiveAlphaFeed {
  constructor({ universe, onBatch = async () => {}, pollMs = Number(process.env.LIVE_ALPHA_GROWW_POLL_MS || 180_000), marketOpen = () => sessionState().open, quote = getQuote, indices = pollGrowwIndexSnapshots, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
    this.marketOpen = marketOpen; this.quote = quote; this.indices = indices; this.sleep = sleep;
    this.universe = universe;
    this.onBatch = onBatch;
    this.pollMs = Math.max(60_000, pollMs);
    this.instrumentKeys = [...new Set([universe.benchmarkKey, ...universe.members.flatMap((row) => [row.instrumentKey, row.sectorInstrumentKey, row.growwDerivativeInstrumentKey]).filter(Boolean)])];
    this.timer = null; this.stopped = true; this.inFlight = false;
    this.state = { status: 'idle', connected_at: null, last_message_at: null, reconnects: 0, messages: 0, decode_errors: 0, request_errors: 0, last_request_status: null, last_error: null };
  }

  async start() {
    if (!isGrowwConfigured()) throw new Error('Groww is not configured.');
    this.stopped = false; this.state.status = 'connected'; this.state.connected_at = new Date().toISOString();
    await this.poll();
    this.timer = setInterval(() => void this.poll(), this.pollMs); this.timer.unref?.();
    return this.status();
  }

  async poll() {
    if (this.stopped || this.inFlight) return;
    if (!this.marketOpen()) { this.state.status = 'market_closed'; return; }
    this.inFlight = true;
    try {
      let published = 0;
      const snapshots = [];
      const quoteJobs = this.universe.members.flatMap((member) => [
        { key: member.instrumentKey, segment: 'CASH', symbol: member.symbol },
        ...(member.growwDerivativeTradingSymbol ? [{ key: member.growwDerivativeInstrumentKey, segment: 'FNO', symbol: member.growwDerivativeTradingSymbol }] : []),
      ]);
      // One quote per second leaves capacity inside the shared two/second budget.
      // Stop on authentication or quota failures instead of retrying all 500 names.
      for (let index = 0; index < quoteJobs.length; index += 1) {
        if (this.stopped || !this.marketOpen()) break;
        const group = quoteJobs.slice(index, index + 1);
        const settled = await Promise.allSettled(group.map((job) => this.quote('NSE', job.segment, job.symbol)));
        let blockingError = null;
        settled.forEach((result, offset) => {
          if (result.status === 'fulfilled') {
            const snapshot = normalizeQuote(group[offset].key, result.value, new Date().toISOString());
            if (snapshot) snapshots.push(snapshot); else this.state.decode_errors += 1;
          } else {
            this.state.request_errors += 1;
            const error = result.reason;
            this.state.last_request_status = Number(error?.status) || null;
            if (error?.isRateLimit || [401,403,429].includes(Number(error?.status))) blockingError = error;
          }
        });
        if (snapshots.length && !this.stopped) {
          const batch = snapshots.splice(0); published += batch.length;
          await this.onBatch({ type: 'groww_live_alpha', snapshots: batch });
          this.state.last_message_at = new Date().toISOString();
        }
        if (blockingError) throw blockingError;
        if (index + 1 < quoteJobs.length) await this.sleep(1_050);
      }
      if (this.stopped || !this.marketOpen()) return;
      const indexKeys = [...new Set([this.universe.benchmarkKey, ...this.universe.members.map((row) => row.sectorInstrumentKey)])];
      try {
        snapshots.push(...await this.indices(indexKeys));
        this.state.last_index_error = null;
      } catch (error) {
        // Preserve valid equity and futures observations when an individual
        // index alias changes at the provider. Evaluation will remain in
        // warm-up until the benchmark and sector anchors are available.
        this.state.last_index_error = error.message;
      }
      if (snapshots.length) {
        await this.onBatch({ type: 'groww_live_alpha', snapshots });
        published += snapshots.length;
      }
      if (published) {
        this.state.status = 'connected'; this.state.messages += 1; this.state.last_message_at = new Date().toISOString(); this.state.last_error = null;
      } else throw new Error('Groww returned no usable Live Alpha snapshots.');
    } catch (error) {
      this.state.last_error = [401,403].includes(Number(error?.status)) ? 'Groww authentication rejected. Refresh the configured credential.' : error?.isRateLimit || Number(error?.status)===429 ? 'Groww request budget unavailable; next poll will retry.' : 'Groww feed request failed; inspect provider health.';
      this.state.status = [401,403].includes(Number(error?.status)) ? 'auth_failed' : 'degraded';
    } finally { this.inFlight = false; }
  }

  stop() { this.stopped = true; if (this.timer) clearInterval(this.timer); this.timer = null; this.state.status = 'stopped'; }
  status() { return { ...this.state, provider: 'groww', mode: 'quote_polling', subscribed_instruments: this.instrumentKeys.length, poll_ms: this.pollMs, research_only: true }; }
}
