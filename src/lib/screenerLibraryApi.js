import { supabase } from '@/lib/supabaseClient';
import { API_ORIGIN } from '@/config';
export async function screenerRequest(path, { method = 'GET', body, signal } = {}) {
  const { data } = await supabase.auth.getSession();
  const encoded = body ? JSON.stringify(body) : undefined;
  if (encoded && new TextEncoder().encode(encoded).length > 1800000) throw Error('The import is larger than 1.8 MB. Reduce the table size before submitting.');
  const response = await fetch(`${API_ORIGIN || ''}${path}`, {
    method, cache: 'no-store', signal: signal || AbortSignal.timeout(25000),
    headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...(data?.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}) },
    body: encoded,
  });
  const payload = await response.json().catch(() => ({ error: 'Screener service returned an unreadable response.' }));
  if (!response.ok || payload.error) throw Error(payload.error || 'Unable to load screener data.');
  return payload;
}
export const libraryRequest = (path = '', options) => screenerRequest(`/api/screener-library${path}`, options);
export const screenerDate = value => value ? new Date(`${value}T00:00:00Z`).toLocaleDateString('en-IN', { dateStyle: 'medium', timeZone: 'UTC' }) : 'Awaiting import';
export const recordedTime = value => value ? new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' }) + ' IST' : '—';
