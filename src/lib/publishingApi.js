import { API_ORIGIN } from '@/config';

const BASE = API_ORIGIN || '';

function adminHeaders() {
  const token =
    (typeof localStorage !== 'undefined' && localStorage.getItem('agi_admin_token')) ||
    import.meta.env.VITE_PUBLISHING_ADMIN_TOKEN ||
    import.meta.env.VITE_INTELLIGENCE_ENGINE_TOKEN ||
    'dev-intelligence-token';
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    'X-AGI-Admin-Token': token,
  };
}

async function pubFetch(path, { method = 'GET', body, admin = false } = {}) {
  const resp = await fetch(`${BASE}/api${path}`, {
    method,
    credentials: 'include',
    headers: admin ? adminHeaders() : body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await resp.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!resp.ok) {
    throw new Error(data?.error || data?.message || `Publishing API ${resp.status}`);
  }
  return data;
}

export const newsletterSubscribe = (payload) =>
  pubFetch('/newsletter/subscribe', { method: 'POST', body: payload });

export const newsletterUnsubscribe = (payload) =>
  pubFetch('/newsletter/unsubscribe', { method: 'POST', body: payload });

export const newsletterPreferences = (payload) =>
  pubFetch('/newsletter/preferences', { method: 'PATCH', body: payload });

export const listNewsletterSubscribers = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return pubFetch(`/newsletter/subscribers${qs ? `?${qs}` : ''}`, { admin: true });
};

export const importNewsletterCsv = (payload) =>
  pubFetch('/newsletter/import', { method: 'POST', body: payload, admin: true });

export const getNewsletterAnalytics = () =>
  pubFetch('/newsletter/analytics', { admin: true });

export const listNewsletterCampaigns = () =>
  pubFetch('/newsletter/campaigns', { admin: true });

export const listPublishJobs = () =>
  pubFetch('/newsletter/jobs', { admin: true });

export const previewNewsletter = (article) =>
  pubFetch('/newsletter/preview', { method: 'POST', body: { article }, admin: true });

export const publishArticleDistribution = (payload) =>
  pubFetch('/publish/article', { method: 'POST', body: payload, admin: true });

export const sendNewsletter = (payload) =>
  pubFetch('/newsletter/send', { method: 'POST', body: payload, admin: true });
