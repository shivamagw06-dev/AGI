import assert from 'node:assert/strict';
import test from 'node:test';
import { selectDailyForecastEvents } from './probabilisticForecastStore.js';
import { indiaTradingDayAfterClose } from './dailyForecastSchedule.js';

test('selects one latest confluence event per stock and trading date', () => {
  const rows=selectDailyForecastEvents([{id:'a1',symbol:'INFY',captured_at:'2026-08-11T04:00:00Z'},{id:'a2',symbol:'INFY',captured_at:'2026-08-11T10:00:00Z'},{id:'b1',symbol:'TCS',captured_at:'2026-08-11T09:00:00Z'}]);
  assert.deepEqual(rows.map((row)=>row.id),['b1','a2']);
});

test('opens the daily forecast window only after 15:40 IST on weekdays', () => {
  assert.equal(indiaTradingDayAfterClose(new Date('2026-08-11T10:09:00Z')),null);
  assert.equal(indiaTradingDayAfterClose(new Date('2026-08-11T10:10:00Z')),'2026-08-11');
  assert.equal(indiaTradingDayAfterClose(new Date('2026-08-15T11:00:00Z')),null);
});
