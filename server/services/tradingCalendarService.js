import {
  getExchangeStatus,
  getMarketHolidays,
  getMarketTimings,
} from '../providers/upstox.js';

const IST_OFFSET_MS = 5.5 * 60 * 60_000;
const DAY_MS = 86_400_000;

function dateKey(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) throw new Error('Invalid calendar date.');
  const shifted = new Date(date.getTime() + IST_OFFSET_MS);
  return shifted.toISOString().slice(0, 10);
}

function utcDate(key, hour = 15, minute = 30) {
  const [year, month, day] = String(key).split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day, hour, minute) - IST_OFFSET_MS);
}

function rows(payload) {
  const data = payload?.data ?? payload;
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object') return [data];
  return [];
}

function exchangeNames(value) {
  return (Array.isArray(value) ? value : []).map((item) =>
    String(typeof item === 'string' ? item : item?.exchange || '').toUpperCase()
  ).filter(Boolean);
}

export class TradingCalendarService {
  constructor({ holidays = getMarketHolidays, timings = getMarketTimings, status = getExchangeStatus } = {}) {
    this.fetchHolidays = holidays;
    this.fetchTimings = timings;
    this.fetchStatus = status;
    this.holidays = new Map();
    this.sessions = new Map();
    this.exchangeStatus = new Map();
    this.state = { status: 'idle', last_refresh: null, last_error: null, holiday_rows: 0 };
  }

  ingestHolidays(payload) {
    for (const row of rows(payload)) {
      const key = String(row?.date || '').slice(0, 10);
      if (key) this.holidays.set(key, row);
    }
    this.state.holiday_rows = this.holidays.size;
  }

  ingestTimings(date, payload) {
    for (const row of rows(payload)) {
      const exchange = String(row?.exchange || row?.segment || '').toUpperCase();
      if (!exchange) continue;
      this.sessions.set(`${date}|${exchange}`, {
        date,
        exchange,
        start_time: row.start_time ?? row.startTime ?? null,
        end_time: row.end_time ?? row.endTime ?? null,
        source: 'upstox_market_timings',
      });
    }
  }

  ingestStatus(exchange, payload) {
    const data = payload?.data ?? payload ?? {};
    this.exchangeStatus.set(exchange, {
      exchange,
      status: data.status ?? data.market_status ?? data.exchange_status ?? 'UNKNOWN',
      raw: data,
      observed_at: new Date().toISOString(),
    });
  }

  isTradingDay(value, exchange = 'NSE') {
    const key = typeof value === 'string' ? value.slice(0, 10) : dateKey(value);
    const holiday = this.holidays.get(key);
    const target = String(exchange).toUpperCase();
    if (holiday) {
      const open = exchangeNames(holiday.open_exchanges);
      const closed = exchangeNames(holiday.closed_exchanges);
      if (open.includes(target)) return true;
      if (closed.includes(target)) return false;
      if (String(holiday.holiday_type || '').toUpperCase() === 'TRADING_HOLIDAY') return false;
    }
    const weekday = utcDate(key, 12, 0).getUTCDay();
    return weekday !== 0 && weekday !== 6;
  }

  sessionFor(value, exchange = 'NSE') {
    const key = typeof value === 'string' ? value.slice(0, 10) : dateKey(value);
    if (!this.isTradingDay(key, exchange)) return null;
    return this.sessions.get(`${key}|${String(exchange).toUpperCase()}`) || {
      date: key,
      exchange: String(exchange).toUpperCase(),
      start_time: utcDate(key, 9, 15).getTime(),
      end_time: utcDate(key, 15, 30).getTime(),
      source: 'weekday_fallback',
    };
  }

  addTradingDays(value, count, exchange = 'NSE') {
    let cursor = utcDate(dateKey(value));
    let remaining = Math.max(0, Number(count) || 0);
    while (remaining > 0) {
      cursor = new Date(cursor.getTime() + DAY_MS);
      if (this.isTradingDay(dateKey(cursor), exchange)) remaining -= 1;
    }
    const session = this.sessionFor(dateKey(cursor), exchange);
    return session?.end_time ? new Date(Number(session.end_time)) : cursor;
  }

  nextTradingDay(value, exchange = 'NSE') { return this.addTradingDays(value, 1, exchange); }

  previousTradingDay(value, exchange = 'NSE') {
    let cursor = utcDate(dateKey(value));
    do { cursor = new Date(cursor.getTime() - DAY_MS); }
    while (!this.isTradingDay(dateKey(cursor), exchange));
    return cursor;
  }

  tradingDaysBetween(start, end, exchange = 'NSE') {
    let cursor = utcDate(dateKey(start));
    const finish = utcDate(dateKey(end));
    let count = 0;
    while (cursor < finish) {
      cursor = new Date(cursor.getTime() + DAY_MS);
      if (cursor <= finish && this.isTradingDay(dateKey(cursor), exchange)) count += 1;
    }
    return count;
  }

  currentExchangeStatus(exchange = 'NSE') {
    return this.exchangeStatus.get(String(exchange).toUpperCase()) || null;
  }

  nextSession(exchange = 'NSE', now = new Date()) {
    const today = dateKey(now);
    const session = this.sessionFor(today, exchange);
    if (session && Number(session.end_time) > now.getTime()) return session;
    return this.sessionFor(dateKey(this.nextTradingDay(now, exchange)), exchange);
  }

  async refresh({ exchange = 'NSE', now = new Date() } = {}) {
    const today = dateKey(now);
    this.state.status = 'refreshing';
    try {
      const [holidays, timings, status] = await Promise.all([
        this.fetchHolidays(),
        this.fetchTimings(today),
        this.fetchStatus(exchange),
      ]);
      this.ingestHolidays(holidays);
      this.ingestTimings(today, timings);
      this.ingestStatus(exchange, status);
      this.state = { ...this.state, status: 'ready', last_refresh: new Date().toISOString(), last_error: null };
    } catch (error) {
      this.state = { ...this.state, status: 'degraded', last_refresh: new Date().toISOString(), last_error: error.message };
    }
    return this.health(exchange);
  }

  health(exchange = 'NSE') {
    return {
      ...this.state,
      exchange,
      today: dateKey(),
      is_trading_day: this.isTradingDay(new Date(), exchange),
      current_exchange_status: this.currentExchangeStatus(exchange),
      next_session: this.nextSession(exchange),
      fallback: this.holidays.size === 0,
    };
  }
}

export const tradingCalendar = new TradingCalendarService();
let refreshTimer = null;

export function startTradingCalendarService() {
  if (refreshTimer) return tradingCalendar.health();
  const refresh = () => tradingCalendar.refresh().catch(() => {});
  refresh();
  refreshTimer = setInterval(refresh, 6 * 60 * 60_000);
  refreshTimer.unref?.();
  return tradingCalendar.health();
}
