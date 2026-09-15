/** IST market-session helpers for the Home Terminal countdown. */

const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;

function toIstParts(date = new Date()) {
  const utc = date.getTime() + date.getTimezoneOffset() * 60_000;
  const ist = new Date(utc + IST_OFFSET_MS);
  return {
    y: ist.getFullYear(),
    m: ist.getMonth(),
    d: ist.getDate(),
    h: ist.getHours(),
    min: ist.getMinutes(),
    sec: ist.getSeconds(),
    day: ist.getDay(), // 0 Sun
  };
}

function istDate(y, m, d, h, min = 0, sec = 0) {
  // Build an absolute Instant corresponding to that IST wall time
  const asUtcGuess = Date.UTC(y, m, d, h, min, sec) - IST_OFFSET_MS;
  return new Date(asUtcGuess);
}

export function getMarketSession(now = new Date()) {
  const p = toIstParts(now);
  const isWeekend = p.day === 0 || p.day === 6;
  const open = istDate(p.y, p.m, p.d, 9, 15, 0);
  const close = istDate(p.y, p.m, p.d, 15, 30, 0);

  if (isWeekend) {
    // Next Monday 9:15
    const daysUntilMon = p.day === 0 ? 1 : 2;
    const next = istDate(p.y, p.m, p.d + daysUntilMon, 9, 15, 0);
    return { phase: 'weekend', label: 'Market opens', target: next, open, close };
  }
  if (now < open) {
    return { phase: 'pre', label: 'Market opens in', target: open, open, close };
  }
  if (now <= close) {
    return { phase: 'open', label: 'Market closes in', target: close, open, close };
  }
  const next = istDate(p.y, p.m, p.d + 1, 9, 15, 0);
  // Skip weekend if Friday after close
  if (p.day === 5) {
    return {
      phase: 'closed',
      label: 'Market opens',
      target: istDate(p.y, p.m, p.d + 3, 9, 15, 0),
      open,
      close,
    };
  }
  return { phase: 'closed', label: 'Market opens', target: next, open, close };
}

export function formatCountdown(target, now = new Date()) {
  const ms = Math.max(0, target.getTime() - now.getTime());
  const total = Math.floor(ms / 1000);
  const h = String(Math.floor(total / 3600)).padStart(2, '0');
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

export function greetingForHour(now = new Date()) {
  const h = toIstParts(now).h;
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
}
