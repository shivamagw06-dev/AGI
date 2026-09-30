export const SCREENER_CATEGORIES = [
  { id: 'all', label: 'All screens' },
  { id: 'sentiment', label: 'Sentiment' },
  { id: 'conviction', label: 'Conviction' },
  { id: 'review', label: 'Risk review' },
  { id: 'market', label: 'Market activity' },
];

export const SCREENER_PRESETS = [
  { id: 'all', category: 'all', title: 'All NSE equities', description: 'Every NSE equity in the latest Upstox instrument list.', filters: {} },
  { id: 'strong-bullish', category: 'sentiment', title: 'Strong bullish', description: 'Names with the highest positive research sentiment.', filters: { sentiment: 'Strong Bullish' } },
  { id: 'bullish-conviction', category: 'conviction', title: 'Bullish conviction', description: 'Bullish names with score 70+ and confidence 70%+.', filters: { sentiment: 'Bullish side', minScore: 70, minConfidence: 70 } },
  { id: 'neutral-watch', category: 'conviction', title: 'Neutral watchlist', description: 'Neutral names with confidence 70%+ for further review.', filters: { sentiment: 'Neutral', minConfidence: 70 } },
  { id: 'bearish', category: 'sentiment', title: 'Bearish signals', description: 'Names with bearish or strongly bearish research sentiment.', filters: { sentiment: 'Bearish side' } },
  { id: 'low-score', category: 'review', title: 'Weak research scores', description: 'Names scoring 35 or lower, including unresolved risks.', filters: { maxScore: 35 } },
  { id: 'risk-heavy', category: 'review', title: 'More risks to inspect', description: 'Names with at least three recorded risk factors.', filters: { minRisks: 3 } },
  { id: 'gainers', category: 'market', title: 'Rising today', description: 'Quoted NSE equities up at least 2% versus the previous close.', filters: { minChange: 2 } },
  { id: 'decliners', category: 'market', title: 'Falling today', description: 'Quoted NSE equities down at least 2% versus the previous close.', filters: { maxChange: -2 } },
  { id: 'active', category: 'market', title: 'High share volume', description: 'At least 1 million shares traded in the latest session.', filters: { minVolume: 1000000 } },
];

const SENTIMENT_SIDES = {
  'Bullish side': ['Strong Bullish', 'Bullish'],
  'Bearish side': ['Strong Bearish', 'Bearish'],
};

export function matchScreenerItem(item, filters = {}) {
  const score = item.agiResearchScore == null ? null : Number(item.agiResearchScore);
  const confidence = item.aiConfidencePercent == null ? null : Number(item.aiConfidencePercent);
  const change = item.changePercent == null ? null : Number(item.changePercent);
  const price = item.lastPrice == null ? null : Number(item.lastPrice);
  const volume = item.volume == null ? null : Number(item.volume);
  if (filters.search && !`${item.symbol || ''} ${item.name || ''}`.toUpperCase().includes(String(filters.search).trim().toUpperCase())) return false;
  if (filters.coverage === 'research' && !item.hasResearch) return false;
  if (filters.sentiment) {
    const allowed = SENTIMENT_SIDES[filters.sentiment] || [filters.sentiment];
    if (!allowed.includes(item.overallSentiment)) return false;
  }
  if (filters.minScore !== '' && filters.minScore != null && (score == null || !Number.isFinite(score) || score < Number(filters.minScore))) return false;
  if (filters.maxScore !== '' && filters.maxScore != null && (score == null || !Number.isFinite(score) || score > Number(filters.maxScore))) return false;
  if (filters.minConfidence !== '' && filters.minConfidence != null && (confidence == null || !Number.isFinite(confidence) || confidence < Number(filters.minConfidence))) return false;
  if (filters.minRisks !== '' && filters.minRisks != null && (item.hasResearch === false || (item.riskFactors?.length || 0) < Number(filters.minRisks))) return false;
  if (filters.minChange !== '' && filters.minChange != null && (change == null || change < Number(filters.minChange))) return false;
  if (filters.maxChange !== '' && filters.maxChange != null && (change == null || change > Number(filters.maxChange))) return false;
  if (filters.minPrice !== '' && filters.minPrice != null && (price == null || price < Number(filters.minPrice))) return false;
  if (filters.maxPrice !== '' && filters.maxPrice != null && (price == null || price > Number(filters.maxPrice))) return false;
  if (filters.minVolume !== '' && filters.minVolume != null && (volume == null || volume < Number(filters.minVolume))) return false;
  return true;
}

export function sortScreenerItems(items, sort = 'score-desc') {
  return [...items].sort((a, b) => {
    if (sort === 'symbol-asc') return a.symbol.localeCompare(b.symbol);
    if (sort === 'change-desc' || sort === 'change-asc' || sort === 'volume-desc' || sort === 'price-desc') {
      const key = sort.startsWith('change') ? 'changePercent' : sort.startsWith('volume') ? 'volume' : 'lastPrice';
      const av = a[key] == null ? null : Number(a[key]);
      const bv = b[key] == null ? null : Number(b[key]);
      if (av == null) return bv == null ? a.symbol.localeCompare(b.symbol) : 1;
      if (bv == null) return -1;
      return (sort === 'change-asc' ? av - bv : bv - av) || a.symbol.localeCompare(b.symbol);
    }
    if (sort === 'confidence-desc') return Number(b.aiConfidencePercent ?? -1) - Number(a.aiConfidencePercent ?? -1) || a.symbol.localeCompare(b.symbol);
    if (sort === 'risk-desc') return (b.riskFactors?.length || 0) - (a.riskFactors?.length || 0) || a.symbol.localeCompare(b.symbol);
    if (sort === 'score-asc') return Number(a.agiResearchScore ?? Infinity) - Number(b.agiResearchScore ?? Infinity) || a.symbol.localeCompare(b.symbol);
    return Number(b.agiResearchScore ?? -1) - Number(a.agiResearchScore ?? -1) || a.symbol.localeCompare(b.symbol);
  });
}
