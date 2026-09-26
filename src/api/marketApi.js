import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';
const PUBLIC_TIMEOUT_MS = 7_000;

async function marketFetch(path, { method = 'GET', body, timeoutMs = PUBLIC_TIMEOUT_MS } = {}) {
  const url = `${BASE}/api/market${path}`;
  const resp = await fetch(url, {
    method,
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (resp.status === 429) {
    // Rate limited — return empty so UI keeps last cached state
    console.warn('[marketApi] rate limited, using cached UI state');
    return null;
  }
  if (!resp.ok) throw new Error(`Market API error (${resp.status})`);
  return resp.json();
}

export const getMarketIntelligence = () => marketFetch('/intelligence');
export const getMarketTicker = () => marketFetch('/ticker');
export const getMarketPulse = () => marketFetch('/pulse');
export const getMarketDashboard = () => marketFetch('/dashboard');
export const getMarketBriefing = () => marketFetch('/briefing');
export const getMacroBriefing = () => marketFetch('/macro-briefing');
export const askMacroEconomist = (query) => marketFetch('/macro-ask', { method: 'POST', body: { query } });
export const getPreMarketBriefing = () => marketFetch('/pre-market-briefing');
