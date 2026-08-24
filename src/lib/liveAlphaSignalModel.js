export const LIVE_ALPHA_STRATEGIES = Object.freeze([
  ['cross_sectional_momentum_v1', 'Leadership', 'Cross-Sectional Momentum'],
  ['volume_liquidity_anomaly_v1', 'Activity', 'Volume & Liquidity Anomaly'],
  ['opening_range_expansion_v1', 'Breakout', 'Opening-Range Expansion'],
  ['intraday_mean_reversion_v1', 'Dislocation', 'Intraday Mean Reversion'],
  ['derivatives_positioning_v1', 'Positioning', 'Derivatives Positioning'],
]);

export function signedSignalScore(signal) {
  if (!signal?.direction) return 0;
  const magnitude = Math.min(99, Math.round(Math.abs(Number(signal.alpha_z) || 0) * 28 + (Number(signal.signal_quality_score) || 0) * 0.35));
  return signal.direction === 'negative' ? -magnitude : magnitude;
}

/**
 * How much weight the model puts on its own signal — never a probability.
 *
 * `score` is the engines' heuristic signal quality. `sample` is the count of
 * historical comparable observations behind it, which is currently 0 for every
 * signal because the empirical calibration layer has never produced one.
 *
 * The previous thresholds let a signal read 'HIGH' on score alone, so a name
 * with no historical basis whatsoever could be badged with a word clients
 * reasonably hear as evidential. Model strength and empirical evidence are now
 * separate axes: without comparables the label is capped at MODEL-ONLY,
 * however strong the heuristic looks.
 */
export function confidenceLabel(score, sample = 0) {
  const samples = Number(sample) || 0;
  if (samples < 30) return score >= 60 ? 'MODEL-ONLY' : 'LOW';
  if (samples >= 100 && score >= 70) return 'SAMPLE-RICH';
  return score >= 80 ? 'HIGH' : score >= 60 ? 'MEDIUM' : 'LOW';
}

/** Plain-language basis for the label, so the page never has to imply one. */
export function confidenceBasis(sample = 0) {
  const samples = Number(sample) || 0;
  if (samples < 30) return 'Model state only — no historical comparables behind this signal yet.';
  if (samples < 100) return `Partial evidence — ${samples} comparable observations, below the 100 required.`;
  return `${samples} comparable observations - sample threshold met, not research validation.`;
}

export function componentState(signal, strategyHealth = {}) {
  if (signal?.direction) return 'ACTIVE';
  if (signal) return 'NO SIGNAL';
  const health = strategyHealth?.status;
  if (health === 'never_run') return 'NOT EVALUATED';
  if (['persistence_failed', 'stale'].includes(health)) return 'UNAVAILABLE';
  return 'NO SIGNAL';
}

export function interpretCanonicalSignal(row) {
  const active = [...row.active].sort((a, b) => Math.abs(signedSignalScore(b)) - Math.abs(signedSignalScore(a)));
  const positive = active.filter((signal) => signal.direction === 'positive');
  const negative = active.filter((signal) => signal.direction === 'negative');
  const conflicting = positive.length > 0 && negative.length > 0;
  const direction = row.composite > 0 ? 'POSITIVE' : row.composite < 0 ? 'NEGATIVE' : 'NEUTRAL';
  const structure = conflicting ? 'CONFLICTING' : !active.length ? 'NEUTRAL' : `${active.length > 1 ? 'MULTI-FACTOR' : 'SINGLE-FACTOR'} ${direction}`;
  const alignment = conflicting ? 'CONFLICTING' : active.length >= 2 ? 'HIGH ALIGNMENT' : active.length === 1 ? 'LOW ALIGNMENT' : 'LOW ALIGNMENT';
  const primary = conflicting ? null : active[0] || null;
  const supporting = primary ? active.filter((signal) => signal !== primary && signal.direction === primary.direction) : [];
  const contradicting = conflicting ? active : active.filter((signal) => primary && signal.direction !== primary.direction);
  const positiveLead = positive[0] || null;
  const negativeLead = negative[0] || null;
  const label = (signal) => LIVE_ALPHA_STRATEGIES.find(([key]) => key === signal?.engine)?.[1] || signal?.engine || 'Unknown';
  const scored = (signal) => `${label(signal)} ${signal ? `${signedSignalScore(signal) > 0 ? '+' : ''}${signedSignalScore(signal)}` : '—'}`;
  let summary;
  if (conflicting) summary = `${scored(positiveLead)} is offset by ${scored(negativeLead)}. The opposing components produce a ${direction.toLowerCase()} composite research score of ${row.composite > 0 ? '+' : ''}${row.composite}.`;
  else if (primary && supporting.length) summary = `${scored(primary)} is the primary driver, with ${supporting.map(scored).join(', ')} providing directionally aligned confirmation.`;
  else if (primary) summary = `The current ${direction.toLowerCase()} signal is driven by ${scored(primary)} without another active component providing confirmation.`;
  else summary = 'No component currently has an active directional research classification.';
  return {
    direction, structure, alignment, primary_driver: primary, supporting_components: supporting,
    contradicting_components: contradicting, dominant_positive: positiveLead, dominant_negative: negativeLead,
    active_components: active, inactive_components: LIVE_ALPHA_STRATEGIES.map(([key]) => key).filter((key) => !row.strategies[key]?.direction),
    summary,
    why_flagged: [primary ? `${scored(primary)} is the primary measurable driver` : null, ...supporting.map((signal) => `${scored(signal)} is supporting`), conflicting ? 'Active components point in opposing directions' : active.length > 1 ? 'Active components are directionally aligned' : null, `Composite research signal is ${row.composite > 0 ? '+' : ''}${row.composite}`].filter(Boolean),
    caveats: [active.length === 1 ? 'The signal currently lacks independent component confirmation.' : null, conflicting ? 'This is a mixed research state, not a clean directional signal.' : null, 'Confidence is model-state confidence, not probability of future return.', 'Historical predictive validation is still collecting.'].filter(Boolean),
    strengthening_conditions: ['Continued persistence in the primary component', active.length === 1 ? 'Independent confirmation from another strategy' : 'Continued component agreement', 'Stable input quality and freshness', 'Positive forward outcomes during validation'],
    weakening_conditions: ['Primary component weakening materially', 'Component disagreement increasing', 'Signal becoming stale', 'Strategy or data-quality degradation'],
  };
}

export function buildCanonicalSignals(signals, strategyHealth = {}) {
  const latest = new Map();
  for (const signal of signals || []) {
    const key = `${signal.symbol}|${signal.engine}`;
    if (!latest.has(key) || Date.parse(signal.as_of) > Date.parse(latest.get(key).as_of)) latest.set(key, signal);
  }
  const symbols = new Map();
  for (const signal of latest.values()) {
    const row = symbols.get(signal.symbol) || { instrument: signal.instrument_key, symbol: signal.symbol, sector: signal.sector || '—', strategies: {}, timestamp: signal.as_of };
    row.strategies[signal.engine] = signal;
    if (Date.parse(signal.as_of) > Date.parse(row.timestamp)) row.timestamp = signal.as_of;
    symbols.set(signal.symbol, row);
  }
  return [...symbols.values()].map((row) => {
    const active = Object.values(row.strategies).filter((signal) => signal.direction);
    const scores = active.map(signedSignalScore);
    const composite = Math.max(-99, Math.min(99, scores.length ? Math.round(scores.reduce((sum, value) => sum + value, 0) / Math.sqrt(scores.length)) : 0));
    const quality = active.length ? Math.round(active.reduce((sum, signal) => sum + Number(signal.empirical_confidence_score ?? signal.signal_quality_score ?? 0), 0) / active.length) : 0;
    const samples = Math.max(0, ...active.map((signal) => Number(signal.comparable_observations) || 0));
    const canonical = {
      ...row, newest: row.timestamp, input_timestamp: row.timestamp, data_cutoff: row.timestamp,
      signal_score: composite, composite, quality, samples, confidence: confidenceLabel(quality, samples),
      confidence_basis: confidenceBasis(samples), active,
      validation_status: samples >= 100 ? 'SAMPLE THRESHOLD MET' : 'EVIDENCE BUILDING', strategy_status: 'RESEARCH ONLY',
      strategy_version: 'live-alpha-v1', model_version: 'signal-composite-v1',
      input_data_status: active.every((signal) => signal.liquidity_ok) ? 'READY' : 'REVIEW REQUIRED',
      data_fingerprint: active.map((signal) => signal.id).filter(Boolean).sort().join(':'),
      component_states: Object.fromEntries(LIVE_ALPHA_STRATEGIES.map(([key]) => [key, componentState(row.strategies[key], strategyHealth[key])])),
    };
    canonical.interpretation = interpretCanonicalSignal(canonical);
    canonical.agreement = canonical.interpretation.alignment;
    canonical.signal_structure = canonical.interpretation.structure;
    return canonical;
  });
}

export function reconcileLiveAlpha({ liveUniverse, canonicalSignals, strategySignalCount }) {
  const positive = canonicalSignals.filter((row) => row.composite > 0).length;
  const negative = canonicalSignals.filter((row) => row.composite < 0).length;
  const neutral = Math.max(0, liveUniverse - positive - negative);
  const uniqueActiveNames = positive + negative;
  return {
    positive, negative, neutral, uniqueActiveNames, strategySignalCount,
    valid: positive + negative + neutral === liveUniverse && uniqueActiveNames <= strategySignalCount,
  };
}
