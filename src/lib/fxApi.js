import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';

export async function getFxIntelligence() {
  const response = await fetch(`${BASE}/api/market/fx-intelligence`, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) throw new Error(`FX market reference unavailable (${response.status})`);
  const payload = await response.json();
  if (!payload?.ok && !payload?.pairs?.length) {
    throw new Error(payload?.error || 'FX market reference unavailable');
  }
  return payload;
}
