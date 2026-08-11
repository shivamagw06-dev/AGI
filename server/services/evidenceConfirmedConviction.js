const LABEL_ORDER = Object.freeze({ HIGH_CONVICTION: 5, CONFIRMED: 4, WATCH: 3, TACTICAL_ONLY: 2, CONTRADICTED: 1, INCOMPLETE: 0 });

const finite = (value) => {
  if (value == null || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};
const clamp = (value, minimum = 0, maximum = 100) => Math.max(minimum, Math.min(maximum, value));

function availableScores(item) {
  const scores = item?.scores || {};
  return [
    scores.fundamental_score,
    scores.valuation_score,
    scores.eod_confirmation_score,
    scores.live_confirmation_score,
    scores.catalyst_relevance_score,
  ].map(finite).filter((value) => value != null);
}

function labelFor(item, score, coverage) {
  if (item.confluence_class === 'CONTRADICTION') return 'CONTRADICTED';
  if (item.confluence_class === 'TACTICAL_ONLY') return 'TACTICAL_ONLY';
  if (coverage < 0.4) return 'INCOMPLETE';
  if (item.confluence_class === 'HIGH_CONFLUENCE' && coverage >= 0.8 && score >= 70) return 'HIGH_CONVICTION';
  if (['HIGH_CONFLUENCE', 'CONFIRMED'].includes(item.confluence_class) && coverage >= 0.6 && score >= 60) return 'CONFIRMED';
  return 'WATCH';
}

export function evaluateEvidenceConfirmedConviction(item) {
  const scores = availableScores(item);
  const coverage = scores.length / 5;
  const priority = finite(item?.research_priority_score) ?? (scores.length ? scores.reduce((sum, value) => sum + value, 0) / scores.length : 0);
  const bullishBreadth = Number(item?.bullish_signal_count || 0);
  const bearishBreadth = Number(item?.bearish_signal_count || 0);
  const agreement = clamp(50 + bullishBreadth * 15 - bearishBreadth * 15);
  const contradictionPenalty = Number(item?.contradiction_count || 0) * 10;
  let score = clamp(priority * 0.65 + agreement * 0.20 + coverage * 100 * 0.15 - contradictionPenalty);
  // Missing thesis evidence can still create a useful watch/tactical rank, but
  // it cannot masquerade as a high-conviction investment recommendation.
  if (item?.flags?.incomplete_research_evidence) score = Math.min(score, 59);
  score = Number(score.toFixed(2));
  const label = labelFor(item, score, coverage);
  const positives = [];
  const cautions = [];
  if ((item?.scores?.fundamental_score ?? 0) >= 65) positives.push('fundamental evidence is supportive');
  if ((item?.scores?.valuation_score ?? 0) >= 55) positives.push('valuation is not fighting the thesis');
  if ((item?.scores?.eod_confirmation_score ?? 0) >= 60) positives.push('Groww end-of-day leadership confirms');
  if ((item?.scores?.live_confirmation_score ?? 0) >= 60) positives.push('Upstox live participation confirms');
  if (item?.flags?.incomplete_research_evidence) cautions.push('fundamental or valuation evidence is incomplete');
  if (item?.contradiction_count) cautions.push(`${item.contradiction_count} market confirmation layer(s) contradict the thesis`);
  if ((item?.scores?.valuation_score ?? 100) < 45) cautions.push('valuation appears stretched');
  return {
    symbol: item.symbol,
    sector: item.sector || null,
    conviction_score: score,
    conviction_label: label,
    evidence_coverage: Number(coverage.toFixed(2)),
    confluence_class: item.confluence_class,
    market_regime: item?.anchors?.market_regime || null,
    eligible_for_research_shortlist: ['HIGH_CONVICTION', 'CONFIRMED'].includes(label),
    thesis: positives.length ? `Evidence supports the setup because ${positives.join('; ')}.` : 'The available evidence does not yet establish an investment thesis.',
    risk_note: cautions.length ? `Key caution: ${cautions.join('; ')}.` : 'No cross-signal contradiction is currently visible, but normal investment risk remains.',
    component_scores: item.scores,
    evidence_snapshot: item,
    research_only: true,
    execution_enabled: false,
  };
}

export function buildEvidenceConfirmedConvictionRanking(queue, { limit = 200 } = {}) {
  const rows = (queue?.items || []).map(evaluateEvidenceConfirmedConviction).sort((left, right) =>
    (LABEL_ORDER[right.conviction_label] - LABEL_ORDER[left.conviction_label])
    || (right.conviction_score - left.conviction_score)
    || left.symbol.localeCompare(right.symbol));
  return {
    strategy: 'evidence_confirmed_conviction_v1',
    universe: 'nifty200',
    generated_at: queue?.generated_at || new Date().toISOString(),
    universe_size: rows.length,
    research_only: true,
    execution_enabled: false,
    methodology: { priority: 0.65, signal_agreement: 0.20, evidence_coverage: 0.15, contradiction_penalty: 10, incomplete_thesis_cap: 59 },
    counts: Object.fromEntries(Object.keys(LABEL_ORDER).map((label) => [label, rows.filter((row) => row.conviction_label === label).length])),
    rows: rows.slice(0, Math.max(1, Math.min(200, limit))).map((row, index) => ({ ...row, rank: index + 1 })),
  };
}

export { LABEL_ORDER };
