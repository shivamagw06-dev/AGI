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
}
