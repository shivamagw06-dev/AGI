import { parse } from 'csv-parse/sync';
import { getLTP, getQuote, isGrowwConfigured } from '../providers/groww.js';
import { growwSymbolForIndex } from './sectorIndexGrowwFallback.js';

const INSTRUMENTS_URL = process.env.GROWW_INSTRUMENTS_URL || 'https://growwapi-assets.groww.in/instruments/instrument.csv';

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function positiveNumber(value) {
  const parsed = number(value);
  return parsed > 0 ? parsed : null;
}

export function normalizeSpreadBps(bid, ask) {
  const normalizedBid = positiveNumber(bid);
  const normalizedAsk = positiveNumber(ask);
  if (normalizedBid === null || normalizedAsk === null || normalizedAsk < normalizedBid) return null;
  return Number((((normalizedAsk - normalizedBid) / ((normalizedAsk + normalizedBid) / 2)) * 10_000).toFixed(4));
}

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
    previous_close: positiveNumber(ohlc(quote?.ohlc)?.[0]?.close),
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
  constructor({ universe, onBatch = async () => {}, pollMs = Number(process.env.LIVE_ALPHA_GROWW_POLL_MS || 180_000) } = {}) {
    this.universe = universe;
    this.onBatch = onBatch;
    this.pollMs = Math.max(60_000, pollMs);
    this.instrumentKeys = [...new Set([universe.benchmarkKey, ...universe.members.flatMap((row) => [row.instrumentKey, row.sectorInstrumentKey, row.growwDerivativeInstrumentKey]).filter(Boolean)])];
    this.timer = null; this.stopped = true; this.inFlight = false;
    this.state = { status: 'idle', connected_at: null, last_message_at: null, reconnects: 0, messages: 0, decode_errors: 0, last_error: null };
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
    this.inFlight = true;
    try {
      const snapshots = [];
      const quoteJobs = this.universe.members.flatMap((member) => [
        { key: member.instrumentKey, segment: 'CASH', symbol: member.symbol },
        ...(member.growwDerivativeTradingSymbol ? [{ key: member.growwDerivativeInstrumentKey, segment: 'FNO', symbol: member.growwDerivativeTradingSymbol }] : []),
      ]);
      // Groww's 300/minute live-data limit is shared with the rest of AGI.
      // Three requests per second leaves capacity for dashboards and scheduled
      // research while a complete cash + futures cycle finishes in ~2m10s.
      for (let index = 0; index < quoteJobs.length; index += 3) {
        const group = quoteJobs.slice(index, index + 3);
        const settled = await Promise.allSettled(group.map((job) => getQuote('NSE', job.segment, job.symbol)));
        settled.forEach((result, offset) => {
          if (result.status === 'fulfilled') {
            const snapshot = normalizeQuote(group[offset].key, result.value, new Date().toISOString());
            if (snapshot) snapshots.push(snapshot);
          } else this.state.decode_errors += 1;
        });
        if (index + 3 < quoteJobs.length) await new Promise((resolve) => setTimeout(resolve, 1_050));
      }
      const indexKeys = [...new Set([this.universe.benchmarkKey, ...this.universe.members.map((row) => row.sectorInstrumentKey)])];
      const indexMap = new Map(indexKeys.map((key) => [key, growwSymbolForIndex(key)]).filter(([, symbol]) => symbol));
      try {
        const exchangeSymbols = [...new Set([...indexMap.values()].map((symbol) => `NSE_${symbol}`))];
        const prices = await getLTP(exchangeSymbols, 'CASH');
        for (const [key, symbol] of indexMap) {
          const price = number(prices?.[`NSE_${symbol}`] ?? prices?.[`NSE:${symbol}`] ?? prices?.[symbol]);
          if (price > 0) snapshots.push({ instrument_key: key, received_at: new Date().toISOString(), ltp: price, request_mode: 'groww_ltp', source: 'groww' });
        }
      } catch (error) {
        // Preserve valid equity and futures observations when an individual
        // index alias changes at the provider. Evaluation will remain in
        // warm-up until the benchmark and sector anchors are available.
        this.state.last_index_error = error.message;
      }
      if (snapshots.length) {
        await this.onBatch({ type: 'groww_live_alpha', snapshots });
        this.state.status = 'connected'; this.state.messages += 1; this.state.last_message_at = new Date().toISOString(); this.state.last_error = null;
      } else throw new Error('Groww returned no usable Live Alpha snapshots.');
    } catch (error) {
      this.state.last_error = error.message;
      this.state.status = 'degraded';
    } finally { this.inFlight = false; }
  }

  stop() { this.stopped = true; if (this.timer) clearInterval(this.timer); this.timer = null; this.state.status = 'stopped'; }
  status() { return { ...this.state, provider: 'groww', mode: 'quote_polling', subscribed_instruments: this.instrumentKeys.length, poll_ms: this.pollMs, research_only: true }; }
}
