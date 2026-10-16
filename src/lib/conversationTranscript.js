import { getAskConversationId } from './uiApi';

const PREFIX = 'agi.ask.transcript.v1.';
const MAX_TURNS = 20;

function storageKey(conversationId) {
  return `${PREFIX}${conversationId || getAskConversationId()}`;
}

function read(conversationId) {
  if (typeof window === 'undefined') return [];
  try {
    const parsed = JSON.parse(window.sessionStorage.getItem(storageKey(conversationId)) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(conversationId, turns) {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(storageKey(conversationId), JSON.stringify(turns.slice(-MAX_TURNS)));
  } catch {
    // A transcript is a convenience surface; quota failure must never block research.
  }
}

function compactText(value, limit = 1800) {
  const text = String(value || '').trim();
  return text.length > limit ? `${text.slice(0, limit).trim()}…` : text;
}

export function getConversationTranscript(conversationId) {
  return read(conversationId);
}

export function appendConversationTurn({ conversationId, question, pack }) {
  const q = compactText(question, 500);
  if (!q || !pack) return read(conversationId);
  const context = pack.conversation_context || pack.ask_orchestration?.conversation || {};
  const row = {
    id: String(pack.ask_orchestration?.ask_trace_id || `${Date.now()}-${q.slice(0, 32)}`),
    question: q,
    summary: compactText(pack.executive_summary || pack.answer?.summary || pack.investment_thesis),
    stance: compactText(pack.house_view_card?.stance || pack.house_view?.stance || pack.answer?.stance, 80),
    confidence: Number.isFinite(Number(pack.confidence)) ? Number(pack.confidence) : null,
    entities: Array.isArray(context.active_entities) ? context.active_entities.slice(0, 4) : [],
    focus: compactText(context.research_focus, 60),
    horizon: compactText(context.horizon, 20),
    createdAt: new Date().toISOString(),
  };
  const prior = read(conversationId).filter((item) => item.id !== row.id);
  const next = [...prior, row].slice(-MAX_TURNS);
  write(conversationId, next);
  return next;
}

export function clearConversationTranscript(conversationId) {
  if (typeof window !== 'undefined') window.sessionStorage.removeItem(storageKey(conversationId));
  return [];
}
