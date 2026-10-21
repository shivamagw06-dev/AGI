/**
 * Client facade for Research Intelligence Hub (RIH).
 * Browser → /api/intelligence proxies → /v1/research/hub/*
 */

import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';

async function rihFetch(path, { method = 'GET', body, query } = {}) {
  const qs = query ? `?${new URLSearchParams(query).toString()}` : '';
  const url = `${BASE}/api/intelligence${path}${qs}`;
  const resp = await fetch(url, {
    method,
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await resp.text().catch(() => '');
  if (!resp.ok) {
    throw new Error(`RIH API error (${resp.status}) ${text.slice(0, 180)}`);
  }
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`RIH API invalid JSON for ${path}`);
  }
}

export const getResearchHubHealth = () => rihFetch('/rih/health');
export const getResearchHub = (noteId) => rihFetch(`/research/hub/${encodeURIComponent(noteId)}`);
export const getResearchHubGraph = (noteId) =>
  rihFetch(`/research/hub/${encodeURIComponent(noteId)}/graph`);
export const listResearchHubs = (limit = 20) =>
  rihFetch('/research/hub', { query: { limit: String(limit) } });
