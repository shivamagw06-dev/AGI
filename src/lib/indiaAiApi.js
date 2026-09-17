import { API_ORIGIN } from '@/config';

const BASE = `${API_ORIGIN || ''}/api/india-ai`;

/**
 * The India AI intelligence endpoints.
 *
 * No session required: the universe is AGI's own screen over public filings,
 * and the evidence behind every admission is a citation to a document anyone
 * can read. Nothing here republishes a third party's work.
 */
async function request(path, { timeoutMs = 30_000 } = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(timeoutMs),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || `India AI request failed (${response.status})`);
    error.code = payload.code || null;
    error.status = response.status;
    throw error;
  }
  return payload;
}

export const fetchUniverse = () => request('/universe');
export const fetchLive = () => request('/live');
export const fetchSnapshots = () => request('/snapshots');
