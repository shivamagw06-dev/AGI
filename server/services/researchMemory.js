export const CHANGE_TYPES = Object.freeze(['THESIS_STRENGTHENING','THESIS_WEAKENING','VALUATION_IMPROVING','VALUATION_STRETCHING','MARKET_CONFIRMING','MARKET_DIVERGING','CATALYST_ADDED','RISK_ADDED','NO_MATERIAL_CHANGE']);
const numericFields = Object.freeze(['fundamental_score','valuation_score','sector_score','eod_confirmation','live_confirmation','catalyst_score','research_priority']);
const classRank = Object.freeze({ HIGH_CONFLUENCE: 6, CONFIRMED: 5, WATCH: 4, VALUATION_ONLY: 3, DEVELOPING: 2, CONTRADICTION: 1, TACTICAL_ONLY: 1, MOMENTUM_WITHOUT_VALUE: 1 });
const num = (value) => value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
const list = (value) => Array.isArray(value) ? value : [];
const added = (current, prior) => { const before = new Set(list(prior).map((item) => JSON.stringify(item))); return list(current).filter((item) => !before.has(JSON.stringify(item))); };

function evidenceFromSnapshot(snapshot) {
  const bull = [], bear = [];
  const add = (label, score) => { const value = num(score); if (value == null) return; if (value >= 60) bull.push({ label, score: value }); else if (value <= 40) bear.push({ label, score: value }); };
  add('Fundamental quality', snapshot.fundamental_score); add('Valuation attractiveness', snapshot.valuation_score);
  add('Groww EOD confirmation', snapshot.eod_confirmation); add('Upstox live confirmation', snapshot.live_confirmation); add('Sector rotation', snapshot.sector_score);
  for (const key of ['leadership','activity','breakout','dislocation','positioning']) add(key[0].toUpperCase() + key.slice(1), snapshot[key]);
  const catalystItems = list(snapshot.evidence_snapshot?.evidence?.catalysts);
  return { bull, bear, catalysts: catalystItems, risks: list(snapshot.evidence_snapshot?.evidence?.risks) };
}

export function createResearchMemoryState(event) {
  const evidence = evidenceFromSnapshot(event);
  return {
    state_key: `${event.symbol}:${event.captured_at}`, confluence_event_id: event.id, symbol: event.symbol, captured_at: event.captured_at,
    fundamental_score: num(event.fundamental_score), valuation_score: num(event.valuation_score), sector_score: num(event.evidence_snapshot?.components?.groww_sector?.effective),
    eod_confirmation: num(event.eod_confirmation), live_confirmation: num(event.live_confirmation), catalyst_score: num(event.catalyst_score),
    confluence_class: event.classification, research_priority: num(event.research_priority), market_regime: event.market_regime || null, sector: event.sector || null,
    key_bull_evidence: evidence.bull, key_bear_evidence: evidence.bear, risks: evidence.risks, catalysts: evidence.catalysts,
    source_snapshot: event.evidence_snapshot || {}, research_only: true,
  };
}

function fieldChanges(current, prior) {
  const changes = {};
  for (const field of numericFields) { const from = num(prior?.[field]), to = num(current?.[field]); if (from != null && to != null && Math.abs(to - from) >= 3) changes[field] = { from, to, delta: Number((to - from).toFixed(2)) }; }
  if (prior?.confluence_class !== current.confluence_class) changes.confluence_class = { from: prior?.confluence_class || null, to: current.confluence_class };
  return changes;
}

export function detectThesisChange(current, prior) {
  if (!prior) return { change_types: ['NO_MATERIAL_CHANGE'], field_changes: {}, material: false, interpretation: 'Initial research state recorded; no prior company state is available for comparison.' };
  const changes = fieldChanges(current, prior), types = [];
  const fundamentalDelta = changes.fundamental_score?.delta || 0, priorityDelta = changes.research_priority?.delta || 0;
  const valuationDelta = changes.valuation_score?.delta || 0, marketDelta = Math.max(changes.eod_confirmation?.delta || 0, changes.live_confirmation?.delta || 0);
  if (fundamentalDelta >= 5 || priorityDelta >= 8) types.push('THESIS_STRENGTHENING');
  if (fundamentalDelta <= -5 || priorityDelta <= -8) types.push('THESIS_WEAKENING');
  if (changes.confluence_class && !types.includes('THESIS_STRENGTHENING') && !types.includes('THESIS_WEAKENING')) {
    const rankDelta = (classRank[current.confluence_class] || 0) - (classRank[prior.confluence_class] || 0);
    if (rankDelta > 0) types.push('THESIS_STRENGTHENING');
    if (rankDelta < 0) types.push('THESIS_WEAKENING');
  }
  if (valuationDelta >= 5) types.push('VALUATION_IMPROVING');
  if (valuationDelta <= -5) types.push('VALUATION_STRETCHING');
  if (marketDelta >= 8) types.push('MARKET_CONFIRMING');
  if (marketDelta <= -8) types.push('MARKET_DIVERGING');
  const newCatalysts = added(current.catalysts, prior.catalysts), newRisks = added(current.risks, prior.risks);
  if (newCatalysts.length) types.push('CATALYST_ADDED'); if (newRisks.length) types.push('RISK_ADDED');
  if (!types.length && !changes.confluence_class) types.push('NO_MATERIAL_CHANGE');
  const material = types.some((type) => type !== 'NO_MATERIAL_CHANGE') || Boolean(changes.confluence_class);
  const leading = types.filter((type) => type !== 'NO_MATERIAL_CHANGE').map((type) => type.toLowerCase().replaceAll('_', ' '));
  const classification = changes.confluence_class ? ` Classification changed from ${changes.confluence_class.from || 'unclassified'} to ${changes.confluence_class.to}.` : '';
  const interpretation = material ? `${current.symbol} shows ${leading.join(', ') || 'a material classification change'}.${classification}` : `${current.symbol} has no material research change since the prior recorded state.`;
  return { change_types: types, field_changes: { ...changes, new_catalysts: newCatalysts, new_risks: newRisks }, material, interpretation };
}

export function assessPrediction(outcome) {
  if (outcome?.status !== 'completed' || num(outcome.sector_adjusted_alpha_pct) == null) return { result: 'PENDING', sector_adjusted_alpha_pct: null };
  const alpha = num(outcome.sector_adjusted_alpha_pct);
  return { result: alpha > 0 ? 'CONFIRMED' : alpha < 0 ? 'FAILED' : 'NEUTRAL', sector_adjusted_alpha_pct: alpha };
}
