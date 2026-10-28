import assert from 'node:assert/strict';
import test from 'node:test';
import { TradingCalendarService } from './tradingCalendarService.js';

function service() {
  return new TradingCalendarService({ holidays: async () => ({ data: [] }), timings: async () => ({ data: [] }), status: async () => ({ data: {} }) });
}

test('holiday-aware trading-day arithmetic skips weekends and NSE holidays', () => {
  const calendar = service();
  calendar.ingestHolidays({ data: [{ date: '2026-08-10', holiday_type: 'TRADING_HOLIDAY', closed_exchanges: ['NSE'], open_exchanges: [] }] });
  assert.equal(calendar.isTradingDay('2026-08-10'), false);
  assert.equal(calendar.addTradingDays(new Date('2026-08-07T10:00:00Z'), 1).toISOString(), '2026-08-11T10:00:00.000Z');
});

test('special open session overrides trading-holiday label', () => {
  const calendar = service();
  calendar.ingestHolidays({ data: [{ date: '2026-08-09', holiday_type: 'TRADING_HOLIDAY', closed_exchanges: [], open_exchanges: [{ exchange: 'NSE', start_time: 1, end_time: 2 }] }] });
  assert.equal(calendar.isTradingDay('2026-08-09'), true);
  calendar.ingestTimings('2026-08-09', { data: [{ exchange: 'NSE', start_time: 1, end_time: 2 }] });
  assert.equal(calendar.sessionFor('2026-08-09').source, 'upstox_market_timings');
});

test('settlement holiday does not close NSE trading without a closed-exchange entry', () => {
  const calendar = service();
  calendar.ingestHolidays({ data: [{ date: '2026-08-12', holiday_type: 'SETTLEMENT_HOLIDAY', closed_exchanges: ['CDS'], open_exchanges: [] }] });
  assert.equal(calendar.isTradingDay('2026-08-12', 'NSE'), true);
});

test('refresh combines holiday, timing and live exchange status', async () => {
  const calendar = new TradingCalendarService({
    holidays: async () => ({ data: [{ date: '2026-08-15', holiday_type: 'TRADING_HOLIDAY', closed_exchanges: ['NSE'] }] }),
    timings: async () => ({ data: [{ exchange: 'NSE', start_time: 10, end_time: 20 }] }),
    status: async () => ({ data: { status: 'CLOSED' } }),
  });
  const health = await calendar.refresh({ now: new Date('2026-08-11T05:00:00Z') });
  assert.equal(health.status, 'ready');
  assert.equal(calendar.currentExchangeStatus('NSE').status, 'CLOSED');
  assert.equal(calendar.sessionFor('2026-08-11').source, 'upstox_market_timings');
});

test('warehouse calendar rows preserve official holiday provenance', () => {
  const calendar = service();
  calendar.ingestHolidays({ data: [{
    date: '2026-08-15', holiday_type: 'TRADING_HOLIDAY', closed_exchanges: ['NSE'],
  }] });
  const rows = calendar.warehouseRows('NSE', new Date('2026-08-15T06:00:00Z'));
  const holiday = rows.find((row) => row.date === '2026-08-15');
  assert.equal(holiday.is_trading_day, false);
  assert.equal(holiday.calendar_source, 'upstox_holidays_plus_market_timings');
  assert.equal(holiday.source, 'upstox_market_calendar');
  assert.equal(holiday.raw.holiday_type, 'TRADING_HOLIDAY');
});
