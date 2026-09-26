const asArray = (value) => (Array.isArray(value) ? value : []);

const firstText = (...values) => {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
};

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const normalizeSymbol = (value) => {
  const symbol = firstText(value);
  return symbol ? symbol.toUpperCase() : null;
};

const normalizeDirection = (value) => {
  const direction = firstText(value)?.toLowerCase();
  if (!direction) return 'unavailable';
  if (['positive', 'upside', 'beneficial', 'bullish'].includes(direction)) return 'positive';
  if (['negative', 'downside', 'adverse', 'bearish'].includes(direction)) return 'negative';
  if (['mixed', 'two-sided', 'uncertain', 'neutral'].includes(direction)) return 'mixed';
  return 'unavailable';
};

const normalizeSeverity = (value) => {
  const severity = firstText(value)?.toLowerCase();
  if (['critical', 'very high', 'high', 'material'].includes(severity)) return 'high';
  if (['medium', 'moderate'].includes(severity)) return 'medium';
  if (['low', 'minor'].includes(severity)) return 'low';
  return 'unavailable';
};

const normalizeConfidence = (impact) => {
  const numeric = finiteNumber(
    impact.confidence_score ?? impact.confidenceScore ?? impact.confidence,
  );
  if (numeric !== null) {
    const normalized = numeric > 1 ? numeric / 100 : numeric;
    return Math.max(0, Math.min(1, normalized));
  }

  const label = firstText(impact.confidence)?.toLowerCase();
  if (label === 'high') return 0.85;
  if (label === 'medium' || label === 'moderate') return 0.6;
  if (label === 'low') return 0.3;
  return null;
};

const normalizeEvidence = (impact) => {
  const raw = [
    ...asArray(impact.evidence),
    ...asArray(impact.sources),
    ...asArray(impact.citations),
  ];

  const direct = firstText(
    impact.evidence_summary,
    impact.evidenceSummary,
    impact.source,
    impact.source_url,
    impact.sourceUrl,
  );
  if (direct) raw.push(direct);

  const seen = new Set();
  return raw.flatMap((entry) => {
    const label = typeof entry === 'string'
      ? entry.trim()
      : firstText(entry?.title, entry?.label, entry?.source, entry?.url);
    if (!label || seen.has(label)) return [];
    seen.add(label);
    return [{
      label,
      url: typeof entry === 'object' ? firstText(entry?.url, entry?.source_url) : null,
    }];
  });
};

const holdingSymbols = (holdings) => new Set(
  asArray(holdings)
    .map((holding) => normalizeSymbol(
      holding.symbol ?? holding.ticker ?? holding.security_symbol ?? holding.asset_symbol,
    ))
    .filter(Boolean),
);

const priorityFor = ({ severity, direction, confidence, evidence, portfolioMatch }) => {
  let score = portfolioMatch ? 24 : 8;
  score += severity === 'high' ? 30 : severity === 'medium' ? 18 : severity === 'low' ? 8 : 0;
  score += direction === 'negative' ? 18 : direction === 'mixed' ? 12 : direction === 'positive' ? 8 : 0;
  score += confidence === null ? 0 : Math.round(confidence * 12);
  score += evidence.length ? 8 : 0;

  if (!evidence.length || direction === 'unavailable') {
    return { score, priority: 'research_gap', action: 'Complete evidence review' };
  }
  if (portfolioMatch && (severity === 'high' || (severity === 'medium' && direction === 'negative'))) {
    return { score, priority: 'review_now', action: 'Review portfolio impact' };
  }
  return { score, priority: 'monitor', action: 'Monitor evidence' };
};

const normalizeImpact = (impact, index, symbols) => {
  const symbol = normalizeSymbol(
    impact.symbol ?? impact.ticker ?? impact.security_symbol ?? impact.asset_symbol,
  );
  const direction = normalizeDirection(
    impact.direction ?? impact.impact_direction ?? impact.portfolio_direction,
  );
  const severity = normalizeSeverity(
    impact.severity ?? impact.materiality ?? impact.impact_level,
  );
  const confidence = normalizeConfidence(impact);
  const evidence = normalizeEvidence(impact);
  const portfolioMatch = symbol ? symbols.has(symbol) : Boolean(
    impact.portfolio_relevant ?? impact.portfolioRelevant ?? impact.is_portfolio_relevant,
  );
  const priority = priorityFor({ severity, direction, confidence, evidence, portfolioMatch });

  return {
    id: firstText(impact.id, impact.impact_id, impact.research_id) || `research-impact-${index + 1}`,
    symbol,
    title: firstText(impact.title, impact.headline, impact.topic, impact.name) || 'Research impact',
    summary: firstText(
      impact.summary,
      impact.portfolio_impact,
      impact.portfolioImpact,
      impact.description,
    ),
    category: firstText(impact.category, impact.impact_type, impact.type) || 'General research',
    direction,
    severity,
    confidence,
    evidence,
    effectiveDate: firstText(impact.effective_date, impact.event_date, impact.published_at, impact.as_of),
    portfolioMatch,
    availability: evidence.length && direction !== 'unavailable' ? 'available' : 'partial',
    ...priority,
  };
};

export function buildPortfolioDecisionQueue({ researchImpacts = [], holdings = [] } = {}) {
  const symbols = holdingSymbols(holdings);
  const items = asArray(researchImpacts)
    .filter((impact) => impact && typeof impact === 'object')
    .map((impact, index) => normalizeImpact(impact, index, symbols))
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return left.title.localeCompare(right.title);
    });

  const counts = items.reduce((summary, item) => {
    summary[item.priority] += 1;
    if (item.portfolioMatch) summary.portfolioMatched += 1;
    return summary;
  }, {
    review_now: 0,
    monitor: 0,
    research_gap: 0,
    portfolioMatched: 0,
  });

  return {
    status: items.length ? 'available' : 'unavailable',
    message: items.length
      ? null
      : 'No portfolio-linked research impacts are available yet.',
    methodology: 'Evidence priority, portfolio relevance, materiality and stated confidence. No automatic trading action.',
    counts,
    items,
  };
}

export default buildPortfolioDecisionQueue;
