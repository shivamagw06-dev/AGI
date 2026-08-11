const HALF_LIFE_HOURS = Object.freeze({ fundamental: 2160, valuation: 720, groww_equity: 120, groww_sector: 240, leadership: 2, activity: 2, breakout: 1, dislocation: 1, positioning: 4, catalyst: 168 });
const ENGINE_KEYS = Object.freeze({ cross_sectional_momentum_v1: 'leadership', volume_liquidity_anomaly_v1: 'activity', opening_range_expansion_v1: 'breakout', intraday_mean_reversion_v1: 'dislocation', derivatives_positioning_v1: 'positioning' });
const ALPHA_OPPORTUNITY_WEIGHTS = Object.freeze({ fundamental: 0.30, valuation: 0.25, eod: 0.20, live: 0.15, catalyst: 0.10 });

const finite = (value) => {
  if (value == null || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};
const clamp = (value, minimum = 0, maximum = 100) => Math.max(minimum, Math.min(maximum, value));

export function decayScore(score, observedAt, now = new Date(), halfLifeHours = 24) {
  const raw = finite(score);
  const observed = Date.parse(observedAt || '');
  if (raw == null) return { raw: null, effective: null, freshness: 0, age_hours: null };
  if (!Number.isFinite(observed)) return { raw: clamp(raw), effective: clamp(raw), freshness: 1, age_hours: null };
  const ageHours = Math.max(0, (now.getTime() - observed) / 3_600_000);
  const freshness = 2 ** (-ageHours / Math.max(0.01, halfLifeHours));
  const effective = 50 + (clamp(raw) - 50) * freshness;
  return { raw: Number(clamp(raw).toFixed(2)), effective: Number(clamp(effective).toFixed(2)), freshness: Number(freshness.toFixed(4)), age_hours: Number(ageHours.toFixed(2)) };
}

function mean(values) {
  const available = values.map(finite).filter((value) => value != null);
  return available.length ? available.reduce((sum, value) => sum + value, 0) / available.length : null;
}

function signedLiveScore(signal) {
  const quality = finite(signal?.empirical_confidence_score ?? signal?.signal_quality_score) ?? 50;
  if (signal?.direction === 'positive') return quality;
  if (signal?.direction === 'negative') return 100 - quality;
  return 50;
}

function classify({ fundamental, valuation, eod, live }) {
  const thesis = fundamental != null && valuation != null && fundamental >= 65 && valuation >= 50;
  const marketHigh = Math.max(eod ?? 50, live ?? 50) >= 70;
  const marketWeak = Math.min(eod ?? 50, live ?? 50) <= 40;
  if (thesis && eod >= 60 && live >= 60) return 'HIGH_CONFLUENCE';
  if (thesis && marketWeak) return 'CONTRADICTION';
  if (thesis && (eod >= 60 || live >= 60)) return 'CONFIRMED';
  if (fundamental != null && fundamental < 50 && marketHigh) return 'TACTICAL_ONLY';
  if (valuation != null && valuation >= 70 && (fundamental ?? 50) < 55 && Math.max(eod ?? 50, live ?? 50) < 60) return 'VALUATION_ONLY';
  if (valuation != null && valuation < 45 && (fundamental ?? 0) >= 70 && marketHigh) return 'MOMENTUM_WITHOUT_VALUE';
  if (thesis) return 'WATCH';
  return 'DEVELOPING';
}

function weightedScore(scores) {
  const available = Object.keys(ALPHA_OPPORTUNITY_WEIGHTS).filter((key) => scores[key] != null);
  const weight = available.reduce((sum, key) => sum + ALPHA_OPPORTUNITY_WEIGHTS[key], 0);
  if (!weight) return null;
  return Number((available.reduce((sum, key) => sum + scores[key] * ALPHA_OPPORTUNITY_WEIGHTS[key], 0) / weight).toFixed(2));
}

export function evaluateResearchConfluence(evidence, { now = new Date() } = {}) {
  const symbol = String(evidence?.symbol || '').trim().toUpperCase();
  if (!symbol) throw new Error('Research confluence requires a symbol.');
  const at = evidence.observed_at || {};
  const fundamental = decayScore(evidence.fundamental_score, at.fundamental, now, HALF_LIFE_HOURS.fundamental);
  const valuation = decayScore(evidence.valuation_score, at.valuation, now, HALF_LIFE_HOURS.valuation);
  const growwEquity = decayScore(evidence.groww_equity_score, at.groww_equity, now, HALF_LIFE_HOURS.groww_equity);
  const growwSector = decayScore(evidence.groww_sector_rotation_score, at.groww_sector, now, HALF_LIFE_HOURS.groww_sector);
  const catalyst = decayScore(evidence.catalyst_score, at.catalyst, now, HALF_LIFE_HOURS.catalyst);
  const liveComponents = Object.fromEntries(Object.values(ENGINE_KEYS).map((key) => [key, decayScore(evidence[`upstox_${key}_score`], at[key], now, HALF_LIFE_HOURS[key])]));
  const scores = { fundamental: fundamental.effective, valuation: valuation.effective, eod: mean([growwEquity.effective, growwSector.effective]), live: mean(Object.values(liveComponents).map((item) => item.effective)), catalyst: catalyst.effective };
  const bullish = [scores.eod, scores.live].filter((score) => score != null && score >= 60).length;
  const bearish = [scores.eod, scores.live].filter((score) => score != null && score <= 40).length;
  const researchPositive = (scores.fundamental ?? 50) >= 65 && (scores.valuation ?? 50) >= 50;
  return {
    symbol, sector: evidence.sector || null, timestamp: now.toISOString(), research_only: true,
    anchors: evidence.anchors || null,
    components: { fundamental, valuation, groww_equity: growwEquity, groww_sector: growwSector, live: liveComponents, catalyst },
    evidence: { key_bull_evidence: evidence.key_bull_evidence || [], key_bear_evidence: evidence.key_bear_evidence || [], risks: evidence.risks || [], catalysts: evidence.provenance?.catalyst?.items || evidence.catalysts || [], provenance: evidence.provenance || {} },
    scores: { fundamental_score: scores.fundamental, valuation_score: scores.valuation, eod_confirmation_score: scores.eod == null ? null : Number(scores.eod.toFixed(2)), live_confirmation_score: scores.live == null ? null : Number(scores.live.toFixed(2)), catalyst_relevance_score: scores.catalyst },
    bullish_signal_count: bullish, bearish_signal_count: bearish, contradiction_count: researchPositive ? bearish : bullish,
    confluence_class: classify(scores), research_priority_score: weightedScore(scores),
    flags: { value_trap_risk: (scores.valuation ?? 0) >= 75 && (scores.fundamental ?? 100) < 45 && Math.max(scores.eod ?? 50, scores.live ?? 50) < 45, valuation_stretched: (scores.valuation ?? 100) < 45, incomplete_research_evidence: scores.fundamental == null || scores.valuation == null },
  };
}

export function buildConfluenceQueue({ workspace, research = [], now = new Date(), limit = 25 } = {}) {
  const bySymbol = new Map(research.map((row) => [String(row.symbol || '').toUpperCase(), { ...row }]));
  const sectorScores = new Map((workspace?.groww?.sectors || []).map((row) => [String(row.sector || '').toUpperCase(), row]));
  const equityRun = (workspace?.groww?.runs || []).find((run) => run.strategy === 'agi_equity_opportunity_v1');
  const sectorRun = (workspace?.groww?.runs || []).find((run) => run.strategy === 'agi_sector_rotation_v1');
  for (const row of workspace?.groww?.equities || []) {
    const symbol = String(row.symbol || '').toUpperCase(); const existing = bySymbol.get(symbol) || {};
    bySymbol.set(symbol, { ...existing, symbol, groww_equity_score: row.score, observed_at: { ...(existing.observed_at || {}), groww_equity: equityRun?.as_of } });
  }
  for (const signal of workspace?.signals || []) {
    const symbol = String(signal.symbol || '').toUpperCase(); const key = ENGINE_KEYS[signal.engine];
    if (!symbol || !key) continue;
    const existing = bySymbol.get(symbol) || { symbol, sector: signal.sector };
    const sectorRow = sectorScores.get(String(signal.sector || existing.sector || '').toUpperCase());
    bySymbol.set(symbol, { ...existing, symbol, sector: signal.sector || existing.sector, groww_sector_rotation_score: existing.groww_sector_rotation_score ?? sectorRow?.score, [`upstox_${key}_score`]: signedLiveScore(signal), anchors: existing.anchors || { captured_at: signal.as_of || signal.created_at, instrument_key: signal.instrument_key, price_at_signal: signal.price_at_signal, benchmark_at_signal: signal.nifty_at_signal, sector_index_at_signal: signal.sector_at_signal, market_regime: signal.market_regime || null }, observed_at: { ...(existing.observed_at || {}), groww_sector: existing.observed_at?.groww_sector || sectorRun?.as_of, [key]: signal.as_of || signal.created_at } });
  }
  const items = [...bySymbol.values()].map((row) => evaluateResearchConfluence(row, { now })).sort((a, b) => (b.research_priority_score ?? -1) - (a.research_priority_score ?? -1) || a.symbol.localeCompare(b.symbol));
  return { generated_at: now.toISOString(), research_only: true, methodology: { weights: ALPHA_OPPORTUNITY_WEIGHTS, half_life_hours: HALF_LIFE_HOURS, decay: 'toward_neutral_exponential' }, completeness: { full_evidence: items.filter((item) => !item.flags.incomplete_research_evidence).length, total: items.length }, items: items.slice(0, Math.max(1, Math.min(200, limit))) };
}

export { ALPHA_OPPORTUNITY_WEIGHTS, ENGINE_KEYS, HALF_LIFE_HOURS };
