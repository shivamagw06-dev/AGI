/**
 * Acquisition → activation funnel analytics.
 *
 * Stages (in order):
 * visitor → public_home / public_article → gated_feature_clicked → unlock_screen
 * → signup_started → signup_completed → returned_to_intended_page
 * → first_meaningful_action → day7_return
 *
 * Storage: local (debug / same-browser). Also forwards to window.gtag / dataLayer
 * when Google Analytics is present (VITE_GA_MEASUREMENT_ID or existing gtag).
 */

import { trackProductEvent } from '@/lib/productAnalytics';

const KEY = 'agi_funnel_analytics_v1';
const MAX_EVENTS = 300;

export const FUNNEL_STAGES = [
  'visitor_session',
  'public_home',
  'public_article',
  'gated_feature_clicked',
  'unlock_screen',
  'signup_started',
  'signup_completed',
  'login_completed',
  'returned_to_intended_page',
  'first_meaningful_action',
  'day7_return',
];

function emptyState() {
  return {
    visitor_id: null,
    signup_completed_at: null,
    first_action_at: null,
    day7_return_at: null,
    intended_path: null,
    counts: Object.fromEntries(FUNNEL_STAGES.map((s) => [s, 0])),
    events: [],
  };
}

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return emptyState();
    const parsed = JSON.parse(raw);
    return {
      ...emptyState(),
      ...parsed,
      counts: { ...emptyState().counts, ...(parsed.counts || {}) },
      events: Array.isArray(parsed.events) ? parsed.events : [],
    };
  } catch {
    return emptyState();
  }
}

function write(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* ignore quota */
  }
}

function ensureVisitorId(state) {
  if (state.visitor_id) return state;
  const id =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `v_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
  state.visitor_id = id;
  return state;
}

function forwardToGa(stage, payload, visitorId) {
  try {
    const detail = {
      event: 'agi_funnel',
      funnel_stage: stage,
      visitor_id: visitorId,
      ...payload,
    };
    if (typeof window === 'undefined') return;
    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push(detail);
    }
    if (typeof window.gtag === 'function') {
      window.gtag('event', stage, {
        event_category: 'agi_funnel',
        ...payload,
        visitor_id: visitorId,
      });
    }
  } catch {
    /* never break UX for analytics */
  }
}

/**
 * @param {string} stage
 * @param {Record<string, unknown>} payload
 * @param {{ once?: boolean, onceKey?: string }} [opts]
 */
export function trackFunnelEvent(stage, payload = {}, opts = {}) {
  if (typeof window === 'undefined') return null;
  const state = ensureVisitorId(read());

  if (opts.onceKey && (state.events || []).some((e) => e.onceKey === opts.onceKey)) {
    return state;
  }
  if (opts.once && !opts.onceKey && (state.counts?.[stage] || 0) > 0) {
    return state;
  }

  const at = new Date().toISOString();
  const event = {
    stage,
    payload,
    at,
    onceKey: opts.onceKey || null,
    visitor_id: state.visitor_id,
  };

  state.events = [event, ...(state.events || [])].slice(0, MAX_EVENTS);
  state.counts[stage] = (state.counts[stage] || 0) + 1;

  if (stage === 'signup_completed' && !state.signup_completed_at) {
    state.signup_completed_at = at;
  }
  if (stage === 'gated_feature_clicked' || stage === 'unlock_screen') {
    if (payload?.path || payload?.returnTo) {
      state.intended_path = String(payload.path || payload.returnTo);
    }
  }
  if (stage === 'first_meaningful_action' && !state.first_action_at) {
    state.first_action_at = at;
  }
  if (stage === 'day7_return' && !state.day7_return_at) {
    state.day7_return_at = at;
  }

  write(state);
  forwardToGa(stage, payload, state.visitor_id);

  if (stage === 'first_meaningful_action') {
    trackProductEvent('research_conversion', { funnel: true, ...payload });
  }
  if (stage === 'signup_completed') {
    trackProductEvent('subscription_conversion', { funnel: true, channel: 'free_signup', ...payload });
  }

  return state;
}

export function getFunnelAnalytics() {
  return read();
}

export function getFunnelSummary() {
  const state = read();
  const c = state.counts || {};
  const unlock = c.unlock_screen || 0;
  const signupStarted = c.signup_started || 0;
  const signupCompleted = c.signup_completed || 0;
  const activated = c.first_meaningful_action || 0;
  const pct = (num, den) => (den > 0 ? Math.round((num / den) * 1000) / 10 : null);

  return {
    visitor_id: state.visitor_id,
    signup_completed_at: state.signup_completed_at,
    first_action_at: state.first_action_at,
    day7_return_at: state.day7_return_at,
    intended_path: state.intended_path,
    counts: c,
    rates: {
      unlock_to_signup_start_pct: pct(signupStarted, unlock),
      signup_start_to_complete_pct: pct(signupCompleted, signupStarted),
      signup_to_activation_pct: pct(activated, signupCompleted),
    },
    recent: (state.events || []).slice(0, 25),
  };
}

/** Mark that the next auth success should count as signup completion. */
export function markSignupIntent(payload = {}) {
  try {
    sessionStorage.setItem(
      'agi_funnel_signup_intent',
      JSON.stringify({ at: new Date().toISOString(), ...payload })
    );
  } catch {
    /* ignore */
  }
  return trackFunnelEvent('signup_started', payload);
}

export function consumeSignupIntent() {
  try {
    const raw = sessionStorage.getItem('agi_funnel_signup_intent');
    sessionStorage.removeItem('agi_funnel_signup_intent');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function trackReturnedToIntended(path) {
  return trackFunnelEvent('returned_to_intended_page', { path }, { onceKey: `return:${path}` });
}

export function trackFirstMeaningfulAction(action, payload = {}) {
  return trackFunnelEvent(
    'first_meaningful_action',
    { action, ...payload },
    { once: true }
  );
}

export function maybeTrackDay7Return({ authenticated } = {}) {
  if (!authenticated) return null;
  const state = read();
  if (!state.signup_completed_at || state.day7_return_at) return state;
  const signed = Date.parse(state.signup_completed_at);
  if (!Number.isFinite(signed)) return state;
  const days = (Date.now() - signed) / 86400000;
  if (days < 7) return state;
  return trackFunnelEvent('day7_return', { days_since_signup: Math.floor(days) }, { once: true });
}

/** Soft bootstrap for GA when VITE_GA_MEASUREMENT_ID is set. Idempotent. */
export function ensureGoogleAnalytics() {
  try {
    const id = import.meta.env.VITE_GA_MEASUREMENT_ID;
    if (!id || typeof document === 'undefined') return false;
    if (typeof window.gtag === 'function') return true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };
    window.gtag('js', new Date());
    window.gtag('config', id, { send_page_view: false });
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    document.head.appendChild(script);
    return true;
  } catch {
    return false;
  }
}
