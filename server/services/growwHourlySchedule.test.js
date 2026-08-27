import assert from 'node:assert/strict';
import test from 'node:test';
import { activeHourlySlot, hasStoredStrategyRunInSlot, parseScheduleSlots } from './growwHourlySchedule.js';

test('parses, validates and orders hourly IST slots', () => {
  assert.deepEqual(parseScheduleSlots('13:00,10:00,bad,10:00', ''), [
    { label: '10:00', minuteOfDay: 600 },
    { label: '13:00', minuteOfDay: 780 },
  ]);
});

test('selects weekday slots inside the configured window only', () => {
  const slot = activeHourlySlot({ now: new Date('2026-08-11T06:33:00Z'), rawSlots: '12:00,13:00', fallbackSlots: '', windowMinutes: 20 });
  assert.equal(slot.key, '2026-08-11|12:00');
  assert.equal(activeHourlySlot({ now: new Date('2026-08-11T06:52:00Z'), rawSlots: '12:00', fallbackSlots: '', windowMinutes: 20 }), null);
  assert.equal(activeHourlySlot({ now: new Date('2026-08-09T06:33:00Z'), rawSlots: '12:00', fallbackSlots: '', windowMinutes: 20 }), null);
});

test('checks stored strategy runs from the beginning of a slot', async () => {
  const priorUrl = process.env.SUPABASE_URL;
  const priorKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  process.env.SUPABASE_URL = 'https://example.supabase.co';
  process.env.SUPABASE_SERVICE_ROLE_KEY = 'service-key';
  let requested;
  try {
    const found = await hasStoredStrategyRunInSlot('agi_equity_opportunity_v1', { startsAt: '2026-08-11T12:00:00+05:30' }, async (url) => {
      requested = new URL(url);
      return { ok: true, json: async () => [{ id: 'run-1' }] };
    });
    assert.equal(found, true);
    assert.equal(requested.searchParams.get('strategy'), 'eq.agi_equity_opportunity_v1');
    assert.equal(requested.searchParams.get('as_of'), 'gte.2026-08-11T12:00:00+05:30');
  } finally {
    if (priorUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = priorUrl;
    if (priorKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = priorKey;
  }
});
