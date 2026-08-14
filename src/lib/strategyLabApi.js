import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';

async function request(path, options = {}) {
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (!token) throw new Error('Administrator session required.');
  const response = await fetch(`${String(API_ORIGIN || '').replace(/\/$/, '')}/api/intelligence/strategy-lab${path}`, {
    ...options,
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(options.headers || {}) },
    signal: AbortSignal.timeout(options.timeoutMs || 190_000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false) throw new Error(payload?.detail || payload?.error || `Strategy Lab request failed (${response.status})`);
  return payload;
}

export const getStrategyLabHealth = () => request('/health', { timeoutMs: 35_000 });
export const getStrategyLabDashboard = (limit = 5) => request(`/dashboard?limit=${limit}`);
export const getStrategyLabScan = (strategyId, limit = 30) => request(`/scan/${encodeURIComponent(strategyId)}?limit=${limit}`);
export const runStrategyLabBacktest = (strategyId, parameters = {}) => request(`/backtest/${encodeURIComponent(strategyId)}`, { method: 'POST', body: JSON.stringify(parameters) });
