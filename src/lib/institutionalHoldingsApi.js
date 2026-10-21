import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';

const BASE = `${API_ORIGIN || ''}/api/institutional-holdings`;

async function request(path, { method = 'GET', body, admin = false, auth = false, timeoutMs = 180_000 } = {}) {
  // A file goes as multipart, and the browser has to write that Content-Type
  // itself because it carries the boundary. Setting JSON here, or stringifying
  // the body, sends an upload as the text "{}".
  const multipart = typeof FormData !== 'undefined' && body instanceof FormData;
  const headers = body && !multipart ? { 'Content-Type': 'application/json' } : {};
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
    body: body ? (multipart ? body : JSON.stringify(body)) : undefined,
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
// The POST forces a fresh computation and is admin-only; it was declared here
// without `admin: true`, so it sent no token and could only ever have returned
// 401. Client surfaces use the GET, which serves the day's stored run.
export const runInstitutionalBacktest = (body) => request('/backtests', { method: 'POST', body, admin: true, timeoutMs: 600_000 });
export const getInstitutionalBacktest = (slug, { quarters = 12, topN = 10 } = {}) =>
  request(`/backtests/${encodeURIComponent(slug)}?quarters=${quarters}&topN=${topN}`, { auth: true, timeoutMs: 300_000 });
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

// The review queue for pasted publications. Admin only: these rows include
// claims nobody has read yet, unlike the public research-layer payload.
export const getPublicationClaims = ({ status = 'pending', slot = '', manager = '', limit = 50, offset = 0 } = {}) =>
  request(`/admin/publication-claims?status=${encodeURIComponent(status)}`
    + `&slot=${encodeURIComponent(slot)}&manager=${encodeURIComponent(manager)}`
    + `&limit=${limit}&offset=${offset}`, { admin: true });

// Decisions are sent as the ids the reviewer was shown. There is no
// "apply to everything matching this filter" on purpose.
export const reviewPublicationClaims = (ids, status) =>
  request('/admin/publication-claims', { method: 'PATCH', body: { ids, status }, admin: true });

// Paste a publication and extract it. Without `apply` nothing is written, so
// a reviewer can see what a document yields before committing 650 rows.
export const uploadPublication = (body) =>
  request('/admin/publications', { method: 'POST', body, admin: true, timeoutMs: 300_000 });
// An annual report read against the hundred underwriting questions. Not tied
// to a manager: those are fifty 13F filers, and any company has a report.
export const readAnnualReport = (body) =>
  request('/admin/annual-report', { method: 'POST', body, admin: true, timeoutMs: 300_000 });
// The same questions, read from the PDF itself. A paste loses the page each
// line sat on, and with it both the page number a reader checks a figure
// against and the running header that separates a company's figures from its
// group's. Reliance's operating cash flow is 79,059 crore on one page and
// 1,92,113 on another, under the same words.
export const readAnnualReportDocument = ({ file, company, revenueDefinition, store = false }) => {
  const form = new FormData();
  form.append('report', file);
  if (company) form.append('company', company);
  if (revenueDefinition) form.append('revenue_definition', revenueDefinition);
  form.append('store', store ? 'true' : 'false');
  return request('/admin/annual-report/document', { method: 'POST', body: form, admin: true, timeoutMs: 300_000 });
};
// The nine judgement questions. Separate from reading the report because it
// costs nine model requests, and the other ninety-one answers are worth having
// in front of a reader before any are spent.
// `auto: true` widens this from the nine judgement questions to every
// question still unanswered. It cannot make a document say what it does not
// say - a question the report is silent on comes back refused.
export const judgeAnnualReport = (body) =>
  request('/admin/annual-report/judgements', { method: 'POST', body, admin: true, timeoutMs: 900_000 });
export const refreshInstitutionalResearchLayer = (body = {}) => request('/admin/research-layer/refresh', { method: 'POST', body, admin: true, timeoutMs: 900_000 });
export const reviewInstitutionalBrief = (id, body) => request(`/admin/research-layer/briefs/${encodeURIComponent(id)}`, { method: 'PATCH', body, admin: true });
