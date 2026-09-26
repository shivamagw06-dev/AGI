import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';

function stocksBoardUrl() {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return '/api/market/stocks-board';
    }
  }
  return `${String(BASE).replace(/\/$/, '')}/api/market/stocks-board`;
}

export async function getStocksBoard() {
  const response = await fetch(stocksBoardUrl(), {
    credentials: 'include',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(45_000),
  });
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    throw new Error('Stocks board returned a non-JSON response.');
  }
  const payload = await response.json();
  if (!response.ok && !payload?.ok) {
    throw new Error(payload?.error || `Stocks board unavailable (${response.status})`);
  }
  return payload;
}
