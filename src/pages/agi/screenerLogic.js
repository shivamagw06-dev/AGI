export const SCREENER_CATEGORIES = [
  { id: 'all', label: 'All screens' },
  { id: 'sentiment', label: 'Sentiment' },
  { id: 'conviction', label: 'Conviction' },
  { id: 'review', label: 'Risk review' },
];

export const SCREENER_PRESETS = [
  { id: 'all', category: 'all', title: 'Entire research universe', description: 'All names in the latest published AGI research run.', filters: {} },
  { id: 'strong-bullish', category: 'sentiment', title: 'Strong bullish', description: 'Names with the highest positive research sentiment.', filters: { sentiment: 'Strong Bullish' } },
  { id: 'bullish-conviction', category: 'conviction', title: 'Bullish conviction', description: 'Bullish names with score 70+ and confidence 70%+.', filters: { sentiment: 'Bullish side', minScore: 70, minConfidence: 70 } },
  { id: 'neutral-watch', category: 'conviction', title: 'Neutral watchlist', description: 'Neutral names with confidence 70%+ for further review.', filters: { sentiment: 'Neutral', minConfidence: 70 } },
  { id: 'bearish', category: 'sentiment', title: 'Bearish signals', description: 'Names with bearish or strongly bearish research sentiment.', filters: { sentiment: 'Bearish side' } },
  { id: 'low-score', category: 'review', title: 'Weak research scores', description: 'Names scoring 35 or lower, including unresolved risks.', filters: { maxScore: 35 } },
  { id: 'risk-heavy', category: 'review', title: 'More risks to inspect', description: 'Names with at least three recorded risk factors.', filters: { minRisks: 3 } },
];

const SENTIMENT_SIDES = {
  'Bullish side': ['Strong Bullish', 'Bullish'],
  'Bearish side': ['Strong Bearish', 'Bearish'],
};

export function matchScreenerItem(item, filters = {}) {
  const score = Number(item.agiResearchScore);
  const confidence = Number(item.aiConfidencePercent);
  if (filters.search && !String(item.symbol || '').toUpperCase().includes(String(filters.search).trim().toUpperCase())) return false;
  if (filters.sentiment) {
    const allowed = SENTIMENT_SIDES[filters.sentiment] || [filters.sentiment];
    if (!allowed.includes(item.overallSentiment)) return false;
  }
  if (filters.minScore !== '' && filters.minScore != null && (!Number.isFinite(score) || score < Number(filters.minScore))) return false;
  if (filters.maxScore !== '' && filters.maxScore != null && (!Number.isFinite(score) || score > Number(filters.maxScore))) return false;
  if (filters.minConfidence !== '' && filters.minConfidence != null && (!Number.isFinite(confidence) || confidence < Number(filters.minConfidence))) return false;
  if (filters.minRisks !== '' && filters.minRisks != null && (item.riskFactors?.length || 0) < Number(filters.minRisks)) return false;
  return true;
}

export function sortScreenerItems(items, sort = 'score-desc') {
  return [...items].sort((a, b) => {
    if (sort === 'symbol-asc') return a.symbol.localeCompare(b.symbol);
    if (sort === 'confidence-desc') return Number(b.aiConfidencePercent) - Number(a.aiConfidencePercent) || a.symbol.localeCompare(b.symbol);
    if (sort === 'risk-desc') return (b.riskFactors?.length || 0) - (a.riskFactors?.length || 0) || a.symbol.localeCompare(b.symbol);
    if (sort === 'score-asc') return Number(a.agiResearchScore) - Number(b.agiResearchScore) || a.symbol.localeCompare(b.symbol);
    return Number(b.agiResearchScore) - Number(a.agiResearchScore) || a.symbol.localeCompare(b.symbol);
  });
}
