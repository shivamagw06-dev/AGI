export function istParts(now = new Date()) {
  return Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata', weekday: 'short', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(now).map((part) => [part.type, part.value]));
}

export function parseScheduleSlots(raw, fallback) {
  const slots = String(raw || fallback).split(',').map((value) => value.trim()).filter(Boolean).map((label) => {
    const [hour, minute] = label.split(':').map(Number);
    return Number.isInteger(hour) && hour >= 0 && hour <= 23 && Number.isInteger(minute) && minute >= 0 && minute <= 59
      ? { label: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`, minuteOfDay: hour * 60 + minute }
      : null;
  }).filter(Boolean);
  return [...new Map(slots.map((slot) => [slot.label, slot])).values()].sort((left, right) => left.minuteOfDay - right.minuteOfDay);
}

export function activeHourlySlot({ now = new Date(), rawSlots, fallbackSlots, windowMinutes = 20 } = {}) {
  const parts = istParts(now);
  if (['Sat', 'Sun'].includes(parts.weekday)) return null;
  const currentMinute = Number(parts.hour) * 60 + Number(parts.minute);
  const slot = parseScheduleSlots(rawSlots, fallbackSlots).find(({ minuteOfDay }) => currentMinute >= minuteOfDay && currentMinute < minuteOfDay + windowMinutes);
  if (!slot) return null;
  const day = `${parts.year}-${parts.month}-${parts.day}`;
  return { ...slot, day, key: `${day}|${slot.label}`, startsAt: `${day}T${slot.label}:00+05:30` };
}

export async function hasStoredStrategyRunInSlot(strategy, slot, fetchImpl = globalThis.fetch) {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key || !strategy || !slot?.startsAt || typeof fetchImpl !== 'function') return false;
  const params = new URLSearchParams({ strategy: `eq.${strategy}`, as_of: `gte.${slot.startsAt}`, select: 'id', limit: '1' });
  const response = await fetchImpl(`${url}/rest/v1/research_strategy_runs?${params}`, { headers: { apikey: key, Authorization: `Bearer ${key}` } });
  if (!response.ok) return false;
  const rows = await response.json();
  return Array.isArray(rows) && rows.length > 0;
}
