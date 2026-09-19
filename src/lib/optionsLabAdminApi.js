import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';

async function request(path, options = {}) {
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (!token) throw new Error('Administrator session required.');
  const response = await fetch(
    `${String(API_ORIGIN || '').replace(/\/$/, '')}/api/intelligence/options-lab${path}`,
    {
      ...options,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
      signal: AbortSignal.timeout(options.timeoutMs || 35_000),
    },
  );
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false) {
    throw new Error(payload?.detail || payload?.error || `Options Lab request failed (${response.status})`);
  }
  return payload;
}

export const getOptionsValidationDashboard = () => request('/validation/dashboard');
export const priceOptionsSnapshotAdmin = (payload) => request('/price', {
  method: 'POST',
  body: JSON.stringify(payload),
});
