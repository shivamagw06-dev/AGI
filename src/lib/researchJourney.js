const KEY = 'agi_research_journey_v1';

function readAll() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(value) {
  try {
    localStorage.setItem(KEY, JSON.stringify(value));
  } catch {
    /* ignore quota */
  }
}

function journeyKey(ticker, playbookKey) {
  const t = String(ticker || '_general').toUpperCase();
  const p = String(playbookKey || 'investment_assessment');
  return `${t}::${p}`;
}

/** @returns {object|null} */
export function getResearchJourneyState(ticker, playbookKey) {
  const all = readAll();
  return all[journeyKey(ticker, playbookKey)] || null;
}

/** Merge server state with local and persist. */
export function mergeResearchJourneyState(ticker, playbookKey, serverState) {
  if (!serverState || typeof serverState !== 'object') return null;
  const key = journeyKey(ticker, playbookKey);
  const prior = readAll()[key] || {};
  const completed = new Set([...(prior.completed_steps || []), ...(serverState.completed_steps || [])]);
  const merged = {
    ...prior,
    ...serverState,
    completed_steps: [...completed],
    updated_at: new Date().toISOString(),
  };
  const all = readAll();
  all[key] = merged;
  writeAll(all);
  return merged;
}

/** Recompute progress UI from journey map + merged state. */
export function enrichJourneyMap(journeyMap, mergedState) {
  if (!journeyMap || !mergedState) return journeyMap;
  const steps = journeyMap.steps || [];
  const completed = new Set(mergedState.completed_steps || []);
  const stepRows = steps.map((row) => ({
    ...row,
    completed: completed.has(row.label),
  }));
  const total = stepRows.length || 1;
  const done = stepRows.filter((s) => s.completed).length;
  const next = stepRows.find((s) => !s.completed && s.label !== 'Decision Complete');
  return {
    ...journeyMap,
    steps: stepRows,
    completed_steps: [...completed],
    progress_pct: Math.round((100 * done) / total),
    progress_label: `${done}/${total} steps`,
    next_step: next?.label || journeyMap.next_step,
    complete: done >= total - 1,
  };
}
