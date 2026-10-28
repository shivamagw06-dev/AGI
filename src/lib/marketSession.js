/** India market session helpers (IST). */

export const SESSIONS = [
  {
    id: 'pre',
    label: 'Pre Market',
    window: '07:00–09:00',
    topics: [
      'Overnight Global Markets',
      'SGX / NIFTY GIFT',
      'US Markets',
      'Asian Markets',
      'Pre Market Outlook',
      "Today's Events",
      'Stocks To Watch',
      'Earnings Today',
    ],
  },
  {
    id: 'morning',
    label: 'Morning',
    window: '09:00–12:00',
    topics: [
      'Opening Analysis',
      'Market Breadth',
      'Breaking Research',
      'Live Company Updates',
      'RBI',
      'Sectors Moving',
    ],
  },
  {
    id: 'afternoon',
    label: 'Afternoon',
    window: '12:00–15:30',
    topics: [
      'Midday Market Wrap',
      'Institutional Flow Analysis',
      'Updated Company Notes',
      'Sector Rotation',
      'Macro Updates',
    ],
  },
  {
    id: 'post',
    label: 'Post Market',
    window: '15:30 onwards',
    topics: [
      'Closing Report',
      'Winners & Losers',
      'Earnings Analysis',
      'Institutional Summary',
      'Tomorrow Outlook',
      'AI Closing Note',
    ],
  },
  {
    id: 'global',
    label: 'Global',
    window: 'After India close',
    topics: [
      'Europe Open',
      'US Futures',
      'Commodities',
      'Dollar',
      'Treasury',
      'Asian Futures',
    ],
  },
];

export function istMinutesNow(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date);
  const hour = Number(parts.find((p) => p.type === 'hour')?.value || 0);
  const minute = Number(parts.find((p) => p.type === 'minute')?.value || 0);
  return hour * 60 + minute;
}

export function resolveMarketSession(date = new Date()) {
  const mins = istMinutesNow(date);
  if (mins >= 7 * 60 && mins < 9 * 60) return 'pre';
  if (mins >= 9 * 60 && mins < 12 * 60) return 'morning';
  if (mins >= 12 * 60 && mins < 15 * 60 + 30) return 'afternoon';
  if (mins >= 15 * 60 + 30 || mins < 7 * 60) {
    // After close through early morning → post, then tilt to global after 18:00 IST
    if (mins >= 18 * 60 || mins < 7 * 60) return 'global';
    return 'post';
  }
  return 'post';
}

export function formatIstTime(date = new Date()) {
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

export function sessionById(id) {
  return SESSIONS.find((s) => s.id === id) || SESSIONS[3];
}
