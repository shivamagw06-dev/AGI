/**
 * Lightweight product analytics — local only, no third-party.
 * Measures Product V1 success criteria without exposing architecture.
 */

const KEY = 'agi_product_analytics_v1';

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) {
      return {
        questions_asked: 0,
        companies_viewed: 0,
        research_read: 0,
        follow_up_questions: 0,
        saved_companies: 0,
        prediction_views: 0,
        search_success: 0,
        research_conversion: 0,
        subscription_conversion: 0,
        sessions: 0,
        last_session_at: null,
        events: [],
      };
    }
    return JSON.parse(raw);
  } catch {
    return { events: [] };
  }
}

function write(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* ignore */
  }
}

export function trackProductEvent(name, payload = {}) {
  const state = read();
  const event = { name, payload, at: new Date().toISOString() };
  state.events = [event, ...(state.events || [])].slice(0, 200);

  if (name === 'question_asked') state.questions_asked = (state.questions_asked || 0) + 1;
  if (name === 'company_viewed') state.companies_viewed = (state.companies_viewed || 0) + 1;
  if (name === 'research_read') state.research_read = (state.research_read || 0) + 1;
  if (name === 'follow_up_question') state.follow_up_questions = (state.follow_up_questions || 0) + 1;
  if (name === 'saved_company') state.saved_companies = (state.saved_companies || 0) + 1;
  if (name === 'prediction_view') state.prediction_views = (state.prediction_views || 0) + 1;
  if (name === 'search_success') state.search_success = (state.search_success || 0) + 1;
  if (name === 'research_conversion') state.research_conversion = (state.research_conversion || 0) + 1;
  if (name === 'subscription_conversion') {
    state.subscription_conversion = (state.subscription_conversion || 0) + 1;
  }
  if (name === 'session_start') {
    state.sessions = (state.sessions || 0) + 1;
    state.last_session_at = event.at;
  }

  write(state);
  return state;
}

export function getProductAnalytics() {
  return read();
}
