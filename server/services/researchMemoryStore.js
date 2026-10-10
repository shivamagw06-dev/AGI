import { assessPrediction, createResearchMemoryState, detectThesisChange } from './researchMemory.js';

function config() { const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, ''), key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim(); if (!url || !key) throw new Error('Research memory requires Supabase credentials.'); return { url, key }; }
async function rest(table, { method = 'GET', query = '', body, prefer } = {}) { const { url, key } = config(); const response = await fetch(`${url}/rest/v1/${table}${query ? `?${query}` : ''}`, { method, headers: { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', ...(prefer ? { Prefer: prefer } : {}) }, body: body == null ? undefined : JSON.stringify(body) }); if (!response.ok) { const error = new Error(`Research memory storage failed (${response.status}): ${(await response.text()).slice(0, 240)}`); error.status = response.status; throw error; } const text = await response.text(); return text ? JSON.parse(text) : []; }

export async function syncResearchMemory({ limit = 500 } = {}) {
  const [events, existing] = await Promise.all([
    rest('research_confluence_events', { query: `select=*&order=captured_at.asc&limit=${Math.min(2000, limit)}` }),
    rest('research_memory_states', { query: 'select=*&order=captured_at.asc&limit=5000' }),
  ]);
  const existingEvents = new Set(existing.map((state) => state.confluence_event_id));
  const latest = new Map(); for (const state of existing) latest.set(state.symbol, state);
  const summary = { scanned: events.length, states_created: 0, changes_created: 0 };
  for (const event of events) {
    if (existingEvents.has(event.id)) continue;
    const stateInput = createResearchMemoryState(event);
    const prior = latest.get(event.symbol) || null;
    const saved = (await rest('research_memory_states', { method: 'POST', body: stateInput, prefer: 'return=representation' }))?.[0];
    if (!saved) continue;
    const change = detectThesisChange(saved, prior);
    await rest('research_memory_changes', { method: 'POST', body: { symbol: saved.symbol, current_state_id: saved.id, prior_state_id: prior?.id || null, detected_at: saved.captured_at, ...change }, prefer: 'return=minimal' });
    latest.set(saved.symbol, saved); summary.states_created += 1; summary.changes_created += 1;
  }
  return summary;
}

export async function getCompanyResearchMemory(symbol, { limit = 50 } = {}) {
  const ticker = String(symbol || '').trim().toUpperCase();
  const states = await rest('research_memory_states', { query: `select=*&symbol=eq.${encodeURIComponent(ticker)}&order=captured_at.desc&limit=${Math.min(200, limit)}` });
  const changes = await rest('research_memory_changes', { query: `select=*&symbol=eq.${encodeURIComponent(ticker)}&order=detected_at.desc&limit=${Math.min(200, limit)}` });
  const eventIds = states.map((state) => state.confluence_event_id);
  const outcomes = eventIds.length ? await rest('research_confluence_outcomes', { query: `select=event_id,horizon,status,sector_adjusted_alpha_pct,excess_return_pct,observed_at&event_id=in.(${eventIds.join(',')})&horizon=eq.5d` }) : [];
  const outcomeByEvent = new Map(outcomes.map((outcome) => [outcome.event_id, { ...outcome, accountability: assessPrediction(outcome) }]));
  return { symbol: ticker, latest: states[0] || null, states: states.map((state) => ({ ...state, prediction_accountability: outcomeByEvent.get(state.confluence_event_id) || { accountability: { result: 'PENDING', sector_adjusted_alpha_pct: null } } })), changes };
}

export async function screenResearchChanges({ type, days = 30, limit = 100 } = {}) {
  const since = new Date(Date.now() - Math.max(1, Math.min(365, days)) * 86_400_000).toISOString();
  let rows = await rest('research_memory_changes', { query: `select=*&detected_at=gte.${encodeURIComponent(since)}&material=eq.true&order=detected_at.desc&limit=${Math.min(500, limit)}` });
  if (type) rows = rows.filter((row) => (row.change_types || []).includes(String(type).toUpperCase()));
  return rows;
}
