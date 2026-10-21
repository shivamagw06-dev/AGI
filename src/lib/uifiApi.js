import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';

async function request(path, { method = 'GET', body } = {}) {
  if (!BASE) {
    throw new Error('API origin is not configured. Set VITE_API_URL to the Render backend.');
  }
  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  });
  const text = await resp.text().catch(() => '');
  if (text.trim().startsWith('<')) {
    throw new Error(
      `AGI Data API returned HTML for ${path}. Check VITE_API_URL points at Render, not the website.`
    );
  }
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`AGI Data API returned invalid JSON for ${path}`);
  }
  if (!resp.ok || data?.ok === false) {
    throw new Error(data.error || data.message || `HTTP ${resp.status}`);
  }
  return data;
}

export function getUifiCoverage() {
  return request('/api/upstox/coverage');
}

export function getUifiFailures() {
  return request('/api/upstox/failures');
}

export function getUifiBootstrapStatus() {
  return request('/api/upstox/bootstrap/status');
}

export function getUifiSchedulerStatus() {
  return request('/api/upstox/scheduler');
}

export function startUifiBootstrap(body = {}) {
  return request('/api/upstox/bootstrap/start', { method: 'POST', body });
}

export function stopUifiBootstrap() {
  return request('/api/upstox/bootstrap/stop', { method: 'POST', body: {} });
}

export function bootstrapDataset(dataset, body = {}) {
  const path = {
    profile: '/api/upstox/profile/bootstrap',
    statements: '/api/upstox/statements/bootstrap',
    shareholding: '/api/upstox/shareholding/bootstrap',
    competitors: '/api/upstox/competitors/bootstrap',
    'corporate-actions': '/api/upstox/corporate-actions/bootstrap',
  }[dataset];
  if (!path) throw new Error(`unknown_dataset:${dataset}`);
  return request(path, { method: 'POST', body });
}

/** Upstox-first EMPTY statement fill (prefer over Yahoo on Render). */
export function getUpstoxEmptyFillStatus() {
  return request('/api/upstox/statements/fill-empty/status');
}

export function startUpstoxEmptyFill(body = {}) {
  return request('/api/upstox/statements/fill-empty', { method: 'POST', body });
}

export function stopUpstoxEmptyFill() {
  return request('/api/upstox/statements/fill-empty/stop', { method: 'POST', body: {} });
}

export function runUpstoxEmptyFill(body = {}) {
  return request('/api/upstox/statements/fill-empty/run', { method: 'POST', body });
}
