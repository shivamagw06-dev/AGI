/**
 * Client facade for UI Aggregation Layer.
 * Browser → /api/ui/* (Express) → /v1/ui/* (intelligence-engine).
 * Never call engines directly from the frontend.
 */

import { API_ORIGIN } from '@/config';
import { hydrateHomeFromMarketApis } from '@/office/homeDeskFallback';

const BASE = API_ORIGIN || '';

async function uiFetch(path, { method = 'GET', body, query, timeoutMs = 45_000 } = {}) {
  const qs = query ? `?${new URLSearchParams(query).toString()}` : '';
  const url = `${BASE}/api/ui${path}${qs}`;
  let resp;
  try {
    resp = await fetch(url, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    const name = err?.name || '';
    if (name === 'TimeoutError' || name === 'AbortError' || /timed out|aborted/i.test(String(err?.message || ''))) {
      throw new Error(`UI API timed out after ${Math.round(timeoutMs / 1000)}s (${path})`);
    }
    throw err;
  }
  const contentType = resp.headers.get('content-type') || '';
  const text = await resp.text().catch(() => '');
  if (!resp.ok) {
    throw new Error(`UI API error (${resp.status}) ${text.slice(0, 180)}`);
  }
  // Hostinger SPA fallback can return index.html with 200 for unknown /api paths.
  if (!contentType.includes('application/json') && text.trim().startsWith('<')) {
    throw new Error(`UI API returned HTML instead of JSON for ${path}`);
  }
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`UI API invalid JSON for ${path}`);
  }
}

export const getUiHealth = () => uiFetch('/health');

/** Home: prefer /api/ui/home, else hydrate from working /api/market/* desks. */
export async function getUiHome() {
  try {
    return await uiFetch('/home');
  } catch (uiError) {
    try {
      return await hydrateHomeFromMarketApis(BASE);
    } catch {
      throw uiError;
    }
  }
}
export const getUiDashboard = () => uiFetch('/dashboard', { timeoutMs: 12_000 });
export const getUiMacro = () => uiFetch('/macro');
export const getUiPortfolio = () => uiFetch('/portfolio');
export const getUiWorkflow = () => uiFetch('/workflow');
export const getUiCompany = (ticker) => uiFetch(`/company/${encodeURIComponent(ticker)}`);
export const getUiResearch = (id) => uiFetch(`/research/${encodeURIComponent(id)}`);
export const getUiTheme = (id) => uiFetch(`/theme/${encodeURIComponent(id)}`);
export const getUiSector = (id) => uiFetch(`/sector/${encodeURIComponent(id)}`);
export const getUiArticle = (id, ticker) =>
  uiFetch(`/article/${encodeURIComponent(id)}`, ticker ? { query: { ticker } } : undefined);
export const getUiTimeline = (entity) => uiFetch(`/timeline/${encodeURIComponent(entity)}`);
export const getUiAutocomplete = (q) => uiFetch('/autocomplete', { query: { q: q || '' } });
export const getUiPredictions = () => uiFetch('/predictions');
export const getUiCalendar = () => uiFetch('/calendar');
export const getUiCopilot = (params = {}) => uiFetch('/copilot', { query: params });

const ASK_CONVERSATION_KEY = 'agi.ask.conversation.v1';

export function getAskConversationId() {
  if (typeof window === 'undefined') return '';
  let value = window.sessionStorage.getItem(ASK_CONVERSATION_KEY);
  if (!value) {
    value = globalThis.crypto?.randomUUID?.() || `ask-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    window.sessionStorage.setItem(ASK_CONVERSATION_KEY, value);
  }
  return value;
}

export function resetAskConversation() {
  if (typeof window !== 'undefined') window.sessionStorage.removeItem(ASK_CONVERSATION_KEY);
  return getAskConversationId();
}

export async function postUiSearch(question, ticker, options = {}) {
  const conversationId = options.conversationId || getAskConversationId();
  const conversation = {
    ...(conversationId ? { conversation_id: conversationId } : {}),
    ...(options.resetConversation ? { reset_conversation: true } : {}),
  };
  try {
    return await uiFetch('/search', {
      method: 'POST',
      body: { question, ticker, ...conversation },
      timeoutMs: 60_000,
    });
  } catch (err) {
    const msg = String(err?.message || '');
    // A browser timeout already gave the desk a full 60 seconds. Retrying it
    // automatically doubles the visitor wait and leaves an apparently frozen
    // Ask page. Network/5xx failures can still receive one wake-and-retry.
    const retryable = /503|502|research_desk_unavailable|unavailable/i.test(msg) && !/timed out/i.test(msg);
    if (!retryable) throw err;
    // One wake/retry — give the engine a moment after the gateway wake probe.
    await new Promise((r) => setTimeout(r, 2500));
    return uiFetch('/search', {
      method: 'POST',
      body: { question, ticker, ...conversation },
      timeoutMs: 60_000,
    });
  }
}
