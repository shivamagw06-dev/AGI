import crypto from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import protobuf from 'protobufjs';
import WebSocket from 'ws';
import { resolveUpstoxAccessToken } from '../providers/upstox.js';

const protoPath = path.join(path.dirname(fileURLToPath(import.meta.url)), '../providers/MarketDataFeedV3.proto');
const AUTHORIZE_URL = process.env.UPSTOX_FEED_AUTHORIZE_URL || 'https://api.upstox.com/v3/feed/market-data-feed/authorize';
const MAX_FULL_KEYS = 1500;
let feedTypePromise;

export async function loadFeedResponseType() {
  if (!feedTypePromise) {
    feedTypePromise = protobuf.load(protoPath).then((root) => root.lookupType('com.upstox.marketdatafeederv3udapi.rpc.proto.FeedResponse'));
  }
  return feedTypePromise;
}

export async function decodeMarketFeedMessage(buffer) {
  const type = await loadFeedResponseType();
  const decoded = type.decode(new Uint8Array(buffer));
  return type.toObject(decoded, { longs: String, enums: String, defaults: false, objects: true });
}

function numeric(value) {
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function feedBody(feed) {
  return feed?.fullFeed?.marketFF
    || feed?.fullFeed?.indexFF
    || feed?.firstLevelWithGreeks
    || (feed?.ltpc ? { ltpc: feed.ltpc } : null);
}

export function normalizeFeedResponse(message, receivedAt = new Date()) {
  const receivedMs = receivedAt.getTime();
  const serverMs = numeric(message?.currentTs);
  const snapshots = [];
  for (const [instrumentKey, feed] of Object.entries(message?.feeds || {})) {
    const body = feedBody(feed);
    const ltpc = body?.ltpc;
    if (!body || !ltpc || numeric(ltpc.ltp) === null) continue;
    const depth = body.marketLevel?.bidAskQuote || (body.firstDepth ? [body.firstDepth] : []);
    const best = depth[0] || {};
    const bid = numeric(best.bidP);
    const ask = numeric(best.askP);
    const ohlc = (body.marketOHLC?.ohlc || []).map((row) => ({
      interval: row.interval,
      open: numeric(row.open), high: numeric(row.high), low: numeric(row.low), close: numeric(row.close),
      volume: numeric(row.vol), timestamp: numeric(row.ts),
    }));
    snapshots.push({
      instrument_key: instrumentKey,
      received_at: receivedAt.toISOString(),
      exchange_timestamp: numeric(ltpc.ltt),
      server_timestamp: serverMs,
      feed_latency_ms: serverMs === null ? null : Math.max(0, receivedMs - serverMs),
      ltp: numeric(ltpc.ltp),
      previous_close: numeric(ltpc.cp),
      last_traded_quantity: numeric(ltpc.ltq),
      average_traded_price: numeric(body.atp),
      cumulative_volume: numeric(body.vtt),
      open_interest: numeric(body.oi),
      implied_volatility: numeric(body.iv),
      best_bid: bid,
      best_ask: ask,
      spread_bps: bid && ask ? Number((((ask - bid) / ((ask + bid) / 2)) * 10_000).toFixed(4)) : null,
      total_buy_quantity: numeric(body.tbq),
      total_sell_quantity: numeric(body.tsq),
      ohlc,
      request_mode: feed.requestMode || null,
    });
  }
  return {
    type: message?.type || null,
    server_timestamp: serverMs,
    market_status: message?.marketInfo?.segmentStatus || null,
    snapshots,
  };
}

export class SynchronizedSnapshotStore {
  constructor({ staleAfterMs = 15_000 } = {}) {
    this.staleAfterMs = staleAfterMs;
    this.latest = new Map();
    this.marketStatus = {};
  }

  ingest(normalized) {
    if (normalized.market_status) this.marketStatus = normalized.market_status;
    for (const snapshot of normalized.snapshots || []) this.latest.set(snapshot.instrument_key, snapshot);
  }

  get(instrumentKey) {
    return this.latest.get(instrumentKey) || null;
  }

  synchronized(instrumentKeys, { now = new Date(), maximumSkewMs = 5_000 } = {}) {
    const rows = instrumentKeys.map((key) => this.latest.get(key)).filter(Boolean);
    const timestamps = rows.map((row) => Date.parse(row.received_at));
    const stale = instrumentKeys.filter((key) => {
      const row = this.latest.get(key);
      return !row || now.getTime() - Date.parse(row.received_at) > this.staleAfterMs;
    });
    const skewMs = timestamps.length ? Math.max(...timestamps) - Math.min(...timestamps) : null;
    return {
      ready: rows.length === instrumentKeys.length && stale.length === 0 && skewMs <= maximumSkewMs,
      requested: instrumentKeys.length,
      available: rows.length,
      stale_instruments: stale,
      skew_ms: skewMs,
      as_of: timestamps.length ? new Date(Math.max(...timestamps)).toISOString() : null,
      snapshots: rows,
    };
  }
}

export async function authorizeMarketFeed({ fetchImpl = globalThis.fetch } = {}) {
  const { token } = resolveUpstoxAccessToken();
  if (!token) throw new Error('Upstox access token is required for the V3 live feed.');
  const response = await fetchImpl(AUTHORIZE_URL, { headers: { Accept: 'application/json', Authorization: `Bearer ${token}` } });
  const json = await response.json().catch(() => ({}));
  const url = json?.data?.authorized_redirect_uri;
  if (!response.ok || !url?.startsWith('wss://')) throw new Error(json?.errors?.[0]?.message || json?.message || `Upstox feed authorization failed (${response.status}).`);
  return url;
}

export class UpstoxMarketFeedV3 {
  constructor({ instrumentKeys, mode = 'full', snapshotStore = new SynchronizedSnapshotStore(), authorize = authorizeMarketFeed, websocketFactory, decoder = decodeMarketFeedMessage, onBatch = async () => {}, reconnect = true } = {}) {
    this.instrumentKeys = [...new Set((instrumentKeys || []).map(String).map((key) => key.trim()).filter(Boolean))];
    if (!this.instrumentKeys.length || this.instrumentKeys.some((key) => !key.includes('|'))) throw new Error('Valid Upstox instrument keys are required.');
    if (mode === 'full' && this.instrumentKeys.length > MAX_FULL_KEYS) throw new Error(`Full-mode feed is limited to ${MAX_FULL_KEYS} combined instrument keys.`);
    this.mode = mode;
    this.snapshotStore = snapshotStore;
    this.authorize = authorize;
    this.websocketFactory = websocketFactory || ((url) => new WebSocket(url, { followRedirects: true }));
    this.decoder = decoder;
    this.onBatch = onBatch;
    this.reconnect = reconnect;
    this.socket = null;
    this.timer = null;
    this.stopped = true;
    this.attempt = 0;
    this.state = { status: 'idle', connected_at: null, last_message_at: null, reconnects: 0, messages: 0, decode_errors: 0, last_error: null };
  }

  async start() {
    if (!this.stopped) return this.status();
    this.stopped = false;
    await this.#connect();
    return this.status();
  }

  async #connect() {
    this.state.status = 'authorizing';
    try {
      const url = await this.authorize();
      if (this.stopped) return;
      const socket = this.websocketFactory(url);
      this.socket = socket;
      socket.binaryType = 'arraybuffer';
      socket.on('open', () => {
        this.attempt = 0;
        this.state.status = 'connected';
        this.state.connected_at = new Date().toISOString();
        const request = { guid: crypto.randomUUID(), method: 'sub', data: { mode: this.mode, instrumentKeys: this.instrumentKeys } };
        socket.send(Buffer.from(JSON.stringify(request)));
      });
      socket.on('message', async (data) => {
        try {
          const decoded = await this.decoder(data);
          const normalized = normalizeFeedResponse(decoded, new Date());
          this.snapshotStore.ingest(normalized);
          this.state.messages += 1;
          this.state.last_message_at = new Date().toISOString();
          await this.onBatch(normalized);
        } catch (error) {
          this.state.decode_errors += 1;
          this.state.last_error = error.message;
        }
      });
      socket.on('error', (error) => { this.state.last_error = error.message; });
      socket.on('close', () => { this.socket = null; this.state.status = this.stopped ? 'stopped' : 'reconnecting'; this.#scheduleReconnect(); });
    } catch (error) {
      this.state.last_error = error.message;
      this.state.status = 'reconnecting';
      this.#scheduleReconnect();
    }
  }

  #scheduleReconnect() {
    if (this.stopped || !this.reconnect || this.timer) return;
    const delay = Math.min(30_000, 1_000 * (2 ** this.attempt)) + Math.floor(Math.random() * 250);
    this.attempt += 1;
    this.state.reconnects += 1;
    this.timer = setTimeout(() => { this.timer = null; this.#connect(); }, delay);
  }

  stop() {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.socket?.close();
    this.socket = null;
    this.state.status = 'stopped';
    return this.status();
  }

  status() {
    return { ...this.state, mode: this.mode, subscribed_instruments: this.instrumentKeys.length, research_only: true };
  }
}
