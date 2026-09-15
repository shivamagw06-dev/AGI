import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';

const BASE = `${String(API_ORIGIN || '').replace(/\/$/, '')}/api/market/live-broadcasts`;

async function request(path = '', options = {}) {
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (!token) throw new Error('Administrator session required.');
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(25_000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false) {
    throw new Error(payload?.detail || payload?.error || `Broadcast update failed (${response.status})`);
  }
  return payload;
}

export const getLiveBroadcastSettings = () => request();
export const saveLiveBroadcastSetting = (id, youtubeUrl) => request(`/${encodeURIComponent(id)}`, {
  method: 'PUT',
  body: JSON.stringify({ youtubeUrl }),
});
