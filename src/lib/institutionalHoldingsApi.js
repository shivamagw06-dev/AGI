import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';

const BASE = `${API_ORIGIN || ''}/api/institutional-holdings`;

async function request(path, { method = 'GET', body, admin = false, auth = false, timeoutMs = 180_000 } = {}) {
  const headers = body ? { 'Content-Type': 'application/json' } : {};
  if (admin || auth) {
    const { data } = await supabase.auth.getSession();
    const token = data?.session?.access_token;
    if (!token) throw new Error(admin ? 'Your admin session has expired. Sign in again.' : 'Sign in to use your institutional workspace.');
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `Institutional Holdings request failed (${response.status})`);
  return payload;
}

export const getInstitutionalOverview = () => request('/overview');
export const searchInstitutionalSecurities = (q, limit = 8) =>
  request(`/securities/search?q=${encodeURIComponent(q)}&limit=${limit}`);
export const getInstitutionalDecisionIntelligence = () => request('/decision-intelligence');
export const getInstitutionalResearchLayer = () => request('/research-layer');
export const runInstitutionalBacktest = (body) => request('/backtests', { method: 'POST', body, timeoutMs: 600_000 });
export const getInstitutionalWorkspace = () => request('/workspace', { auth: true });
export const createInstitutionalGroup = (body) => request('/workspace/groups', { method: 'POST', body, auth: true });
export const createInstitutionalWatchlist = (body) => request('/workspace/watchlists', { method: 'POST', body, auth: true });
export const markInstitutionalPersonalizedAlert = (id, is_read = true) => request(`/workspace/alerts/${encodeURIComponent(id)}`, { method: 'PATCH', body: { is_read }, auth: true });
export const getInstitutionalFund = (slug) => request(`/funds/${encodeURIComponent(slug)}`);
export const getInstitutionalStock = (key) => request(`/stocks/${encodeURIComponent(key)}`);
export const getInstitutionalAdmin = () => request('/admin', { admin: true });
export const refreshInstitutionalFilings = (body) => request('/admin/refresh', { method: 'POST', body, admin: true, timeoutMs: 600_000 });
export const saveInstitutionalSecurityMapping = (body) => request('/admin/security-mappings', { method: 'POST', body, admin: true });
export const updateInstitutionalManager = (id, body) => request(`/admin/managers/${encodeURIComponent(id)}`, { method: 'PATCH', body, admin: true });
export const markInstitutionalAlert = (id, is_read = true) => request(`/admin/alerts/${encodeURIComponent(id)}`, { method: 'PATCH', body: { is_read }, admin: true });
export const previewInstitutionalImport = (body) => request('/admin/imports/preview', { method: 'POST', body, admin: true, timeoutMs: 240_000 });
export const publishInstitutionalImport = (body) => request('/admin/imports/publish', { method: 'POST', body, admin: true, timeoutMs: 600_000 });
export const getInstitutionalResearchAdmin = () => request('/admin/research-layer', { admin: true });
export const refreshInstitutionalResearchLayer = (body = {}) => request('/admin/research-layer/refresh', { method: 'POST', body, admin: true, timeoutMs: 900_000 });
export const reviewInstitutionalBrief = (id, body) => request(`/admin/research-layer/briefs/${encodeURIComponent(id)}`, { method: 'PATCH', body, admin: true });
