/**
 * Phase 7.4d — Upstox bootstrap admin API client.
 * Never calls Upstox directly — Node BFF only.
 */

function apiBase() {
  const raw = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
  return raw;
}

async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    method,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text?.slice(0, 400) };
  }
  if (!response.ok) {
    const err = new Error(data?.error || `http_${response.status}`);
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

export function getUpstoxBootstrapStatus() {
  return request('/api/market/upstox-bootstrap/status');
}

export function getUpstoxBootstrapMissingIsin(limit = 500) {
  return request(`/api/market/upstox-bootstrap/missing-isin?limit=${limit}`);
}

export function getUpstoxBootstrapFailures(limit = 200) {
  return request(`/api/market/upstox-bootstrap/failures?limit=${limit}`);
}

export function startUpstoxBootstrap(opts = {}) {
  return request('/api/market/upstox-bootstrap/start', { method: 'POST', body: opts });
}

export function stopUpstoxBootstrap() {
  return request('/api/market/upstox-bootstrap/stop', { method: 'POST', body: {} });
}

export function resetUpstoxBootstrap() {
  return request('/api/market/upstox-bootstrap/reset', { method: 'POST', body: {} });
}
