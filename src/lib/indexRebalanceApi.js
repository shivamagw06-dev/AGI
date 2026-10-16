import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';

const BASE = `${API_ORIGIN || ''}/api/index-rebalance`;

async function request(path, { method = 'GET', body, admin = false, timeoutMs = 60_000 } = {}) {
  const headers = body ? { 'Content-Type': 'application/json' } : {};
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  // Every path here needs a session, reads included: these rows carry
  // third-party flow estimates and are written for clients, not for the open
  // web.
  if (!token) throw new Error(admin ? 'Your admin session has expired. Sign in again.' : 'Sign in to view index rebalance research.');
  headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Index rebalance request failed (${response.status})`);
  return payload;
}

export const listRebalanceEvents = () => request('/');
export const getRebalanceEvent = (id) => request(`/${encodeURIComponent(id)}`);
export const previewRebalancePaste = (text) => request('/preview', { method: 'POST', body: { text }, admin: true });
export const publishRebalance = (event, text) => request('/publish', { method: 'POST', body: { event, text }, admin: true });
