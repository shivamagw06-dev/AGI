const SESSION_KEY = 'agi_research_session_v1';

function readAll() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(value) {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(value));
  } catch {
    /* ignore quota */
  }
}

function sessionKey(ticker, workflowKey) {
  const t = String(ticker || '_general').toUpperCase();
  const w = String(workflowKey || 'investment_opportunity_evaluation');
  return `${t}::${w}`;
}

/** @returns {object|null} */
export function getResearchSession(ticker, workflowKey) {
  return readAll()[sessionKey(ticker, workflowKey)] || null;
}

/** Merge server session with local and persist. */
export function mergeResearchSession(ticker, workflowKey, serverSession) {
  if (!serverSession || typeof serverSession !== 'object') return null;
  const key = sessionKey(ticker, workflowKey);
  const prior = readAll()[key] || {};
  const questions = new Set([...(prior.questions_asked || []), ...(serverSession.questions_asked || [])]);
  const playbooks = new Set([...(prior.playbooks_completed || []), ...(serverSession.playbooks_completed || [])]);
  const merged = {
    ...prior,
    ...serverSession,
    questions_asked: [...questions].slice(-20),
    playbooks_completed: [...playbooks],
    updated_at: new Date().toISOString(),
  };
  const all = readAll();
  all[key] = merged;
  writeAll(all);
  return merged;
}
