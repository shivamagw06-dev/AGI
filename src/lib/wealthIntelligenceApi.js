import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';

export async function getWealthUniverse(params = {}, signal) {
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (!token) throw new Error('Sign in to view Wealth Intelligence.');
  const response = await fetch(`${API_ORIGIN || ''}/api/wealth/universe?${new URLSearchParams(params)}`, {
    signal, headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok || !payload || !Array.isArray(payload.items)) throw new Error(payload?.error || 'Wealth data could not be loaded.');
  return payload;
}
