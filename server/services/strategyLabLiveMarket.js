import { getLiveAlphaMarketSnapshot } from './liveAlphaRuntime.js';

function signalRows(payload) {
  if (Array.isArray(payload?.signals)) return payload.signals;
  const strategies = Array.isArray(payload?.strategies)
    ? payload.strategies
    : payload?.strategies && typeof payload.strategies === 'object'
      ? Object.values(payload.strategies)
      : [];
  return strategies.flatMap((strategy) => Array.isArray(strategy?.signals) ? strategy.signals : []);
}

function marketClock(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23', weekday: 'short',
  }).formatToParts(now);
  const value = (type) => parts.find((part) => part.type === type)?.value;
  const hour = Number(value('hour'));
  const minute = Number(value('minute'));
  const weekday = value('weekday');
  const minutes = hour * 60 + minute;
  return {
    mode: 'LIVE',
    observed_at: now.toISOString(),
    local_date: `${value('year')}-${value('month')}-${value('day')}`,
    local_time: `${value('hour')}:${value('minute')}:${value('second')} IST`,
    session: !['Sat', 'Sun'].includes(weekday) && minutes >= 555 && minutes <= 930 ? 'OPEN' : 'CLOSED',
  };
}

export function enrichStrategyLabWithLiveMarket(payload, { now = new Date(), liveSnapshot = null } = {}) {
  if (!payload || typeof payload !== 'object') return payload;
  const rows = signalRows(payload);
  const symbols = rows.map((row) => row?.ticker).filter(Boolean);
  const live = liveSnapshot || getLiveAlphaMarketSnapshot(symbols, { now });

  for (const row of rows) {
    const quote = live.quotes?.[String(row.ticker || '').toUpperCase()];
    row.prices = {
      ...(row.prices || {}),
      live_price: quote?.ltp ?? null,
      live_source: quote?.ltp != null ? String(quote.source || 'upstox').toUpperCase() : null,
      live_observed_at: quote?.received_at || null,
      live_quote_age_ms: quote?.quote_age_ms ?? null,
    };
    row.live_validation = quote || {
      data_quality: 'BLOCKED',
      reason_codes: ['LIVE_QUOTE_NOT_REQUESTED'],
    };
  }

  return {
    ...payload,
    clocks: {
      signal: {
        mode: 'EOD',
        completed_session: payload?.session_health?.latest_completed_session
          || rows.find((row) => row?.signal_session)?.signal_session
          || null,
      },
      market: marketClock(now),
    },
    live_market: live,
  };
}
