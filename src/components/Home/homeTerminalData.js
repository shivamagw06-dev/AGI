/** Curated homepage catalogs — soft fallbacks when live CMS/API is thin. */

export const TRENDING_CHIPS = [
  'Reliance',
  'HDFC Bank',
  'Defence',
  'RBI Policy',
  'Gold',
  'IPO Calendar',
];

export const SUGGESTED_SEARCHES = [
  'Reliance',
  'HDFC Bank',
  'Defence',
  'RBI Policy',
  'Gold',
  'IPO Calendar',
];

export const POPULAR_ASK_QUESTIONS = [
  'Should I buy HDFC Bank?',
  'Explain RBI policy.',
  'Compare Tata Motors vs Mahindra.',
  "Summarise today's market.",
  'Top banking stocks.',
];

export const POPULAR_RESEARCH_SEARCHES = [
  'Reliance',
  'RBI Policy',
  'Fed',
  'Defence',
  'Power',
  'IT',
  'IPO Calendar',
];

export const COMPANY_INTEL_EXAMPLES = [
  { label: 'Reliance', symbol: 'reliance' },
  { label: 'TCS', symbol: 'tcs' },
  { label: 'ICICI Bank', symbol: 'icicibank' },
  { label: 'HDFC Bank', symbol: 'hdfcbank' },
  { label: 'HAL', symbol: 'hal' },
];

export const COMPANY_INTEL_PANELS = [
  'Research',
  'Financials',
  'Valuation',
  'Ownership',
  'Filings',
  'Peers',
  'Timeline',
  'Ask AGI',
];

export const HERO_TRUST_LINE =
  '10+ original research notes published every trading day • 2500+ companies covered • Evidence-backed AI answers';

export const RESEARCH_THEMES = [
  { id: 'ai-tech', label: 'AI & Technology', path: '/themes/ai_productivity' },
  { id: 'defence', label: 'Defence', path: '/sectors/defence' },
  { id: 'banking', label: 'Banking', path: '/sectors/banks' },
  { id: 'energy', label: 'Energy Transition', path: '/themes/energy_transition' },
  { id: 'infra', label: 'Infrastructure', path: '/themes/capex_cycle' },
  { id: 'consumption', label: 'Consumption', path: '/sectors/fmcg' },
  { id: 'pharma', label: 'Pharma', path: '/sectors/pharma' },
  { id: 'manufacturing', label: 'Manufacturing', path: '/themes/manufacturing' },
  { id: 'china-plus-one', label: 'China+1', path: '/themes/china_plus_one' },
  { id: 'psu', label: 'PSU', path: '/themes/psu' },
  { id: 'smallcaps', label: 'Small Caps', path: '/ask?q=Small%20cap%20outlook%20India' },
];

export const FEATURED_LANES = [
  { id: 'editors', label: "Editor's Pick", path: '/research' },
  { id: 'institutional', label: 'Institutional Research', path: '/sections/research-notes' },
  { id: 'weekly', label: 'Weekly Outlook', path: '/market-intelligence' },
  { id: 'monthly', label: 'Monthly Outlook', path: '/macro-intelligence' },
  { id: 'thematic', label: 'Thematic Research', path: '/themes' },
  { id: 'strategy', label: 'Strategy Notes', path: '/ask?q=India%20equity%20strategy' },
];

export const DEFAULT_OUTLOOK = [
  { key: 'nifty50', label: 'NIFTY 50', sentiment: 'Bullish', score: 72, path: '/market-intelligence' },
  { key: 'sensex', label: 'SENSEX', sentiment: 'Bullish', score: 70, path: '/market-intelligence' },
  { key: 'banknifty', label: 'BANK NIFTY', sentiment: 'Neutral', score: 55, path: '/market-intelligence' },
  { key: 'usdinr', label: 'USD/INR', sentiment: 'Neutral', score: 52, path: '/macro-intelligence' },
  { key: 'gold', label: 'GOLD', sentiment: 'Bullish', score: 66, path: '/macro-intelligence' },
  { key: 'brent', label: 'BRENT', sentiment: 'Bearish', score: 42, path: '/macro-intelligence' },
  { key: 'us10y', label: 'US 10Y', sentiment: 'Neutral', score: 51, path: '/global-markets' },
  { key: 'btc', label: 'BTC', sentiment: 'Bullish', score: 61, path: '/global-markets' },
  { key: 'india10y', label: 'India 10Y', sentiment: 'Neutral', score: 54, path: '/macro-intelligence' },
];

export const DEFAULT_HIGHLIGHTS = [
  'RBI commentary improves banking outlook.',
  'Defence sector continues to outperform.',
  'Domestic institutions remain constructive on financials.',
  'Oil softness eases input-cost pressure.',
  'Capex and order-book visibility stay institutional themes.',
];

export const CALENDAR_BLOCKS = [
  { id: 'earnings', label: 'Upcoming Earnings', hint: 'Results desk', path: '/events' },
  { id: 'economic', label: 'Economic Events', hint: 'Macro releases', path: '/macro-intelligence' },
  { id: 'ipo', label: 'IPO Calendar', hint: 'Offer calendar', path: '/ipo-intelligence' },
  { id: 'global', label: 'Global Events', hint: 'World desk', path: '/global' },
  { id: 'rbi', label: 'RBI Events', hint: 'Policy & speeches', path: '/macro-intelligence' },
  { id: 'fed', label: 'Fed', hint: 'Global policy', path: '/macro-intelligence' },
];

export const GLOBAL_SNAPSHOT = [
  { id: 'us', label: 'US', path: '/global' },
  { id: 'europe', label: 'Europe', path: '/global' },
  { id: 'asia', label: 'Asia', path: '/global' },
  { id: 'fx', label: 'Currencies', path: '/global' },
  { id: 'commodities', label: 'Commodities', path: '/global' },
  { id: 'bonds', label: 'Bond Yields', path: '/global' },
];

export const RESEARCH_TABS = [
  { id: 'morning', label: 'Morning Desk', match: /morning|pre-?market|open/i },
  { id: 'post', label: 'Post Market', match: /post|close|wrap/i },
  { id: 'global', label: 'Global Desk', match: /global|us|fed|asia|europe/i },
  { id: 'macro', label: 'Macro', match: /macro|rbi|rates|inflation|gdp/i },
  { id: 'ipo', label: 'IPO', match: /ipo|offer|listing/i },
  { id: 'sector', label: 'Sector', match: /sector|bank|defence|pharma|it |energy/i },
  { id: 'weekend', label: 'Weekend', match: /weekend|weekly|sunday|saturday/i },
];

export const MARKET_BOARD = {
  india: [
    { key: 'nifty', label: 'NIFTY', match: /nifty(?!\s*next)|nifty\s*50/i },
    { key: 'banknifty', label: 'BANK NIFTY', match: /bank/i },
    { key: 'midcap', label: 'MIDCAP', match: /midcap|mid\s*cap/i },
    { key: 'smallcap', label: 'SMALLCAP', match: /smallcap|small\s*cap/i },
    { key: 'sensex', label: 'SENSEX', match: /sensex/i },
  ],
  global: [
    { key: 'sp500', label: 'S&P500', match: /s&p|spx|s\s*&\s*p/i },
    { key: 'nasdaq', label: 'NASDAQ', match: /nasdaq/i },
    { key: 'dow', label: 'DOW', match: /dow/i },
    { key: 'ftse', label: 'FTSE', match: /ftse/i },
    { key: 'nikkei', label: 'NIKKEI', match: /nikkei/i },
    { key: 'hangseng', label: 'HANG SENG', match: /hang\s*seng|hsi/i },
  ],
  macro: [
    { key: 'usdinr', label: 'USDINR', match: /usd\s*inr|usdinr|inr/i },
    { key: 'dxy', label: 'DXY', match: /dxy|dollar\s*index/i },
    { key: 'brent', label: 'BRENT', match: /brent|crude|oil/i },
    { key: 'gold', label: 'GOLD', match: /gold/i },
    { key: 'us10y', label: 'US10Y', match: /us\s*10|ust\s*10|treasury/i },
    { key: 'india10y', label: 'India 10Y', match: /india\s*10|g-?sec|in10/i },
    { key: 'vix', label: 'VIX', match: /vix/i },
  ],
};

export const DEFAULT_OPPORTUNITY_QUEUE = [
  {
    company: 'HDFCBANK',
    name: 'HDFC Bank',
    opportunityScore: 78,
    researchPriority: 'High',
    whyNow: 'Deposit franchise and loan growth commentary remains the swing factor for private banks.',
    catalysts: ['Earnings', 'NIM trajectory', 'Deposit costs'],
    confidence: 0.74,
  },
  {
    company: 'RELIANCE',
    name: 'Reliance Industries',
    opportunityScore: 74,
    researchPriority: 'High',
    whyNow: 'Retail and digital cash-flow visibility keeps the conglomerate on the institutional watchlist.',
    catalysts: ['Jio / Retail updates', 'Energy margin'],
    confidence: 0.7,
  },
  {
    company: 'HAL',
    name: 'Hindustan Aeronautics',
    opportunityScore: 81,
    researchPriority: 'Critical',
    whyNow: 'Defence order-book conversion and export optionality keep visibility elevated.',
    catalysts: ['Order inflow', 'Export pipeline'],
    confidence: 0.76,
  },
  {
    company: 'TCS',
    name: 'Tata Consultancy Services',
    opportunityScore: 66,
    researchPriority: 'Medium',
    whyNow: 'Deal pipeline quality supports selective IT coverage if pricing pressure eases.',
    catalysts: ['Large deals', 'Pricing commentary'],
    confidence: 0.62,
  },
  {
    company: 'NTPC',
    name: 'NTPC',
    opportunityScore: 71,
    researchPriority: 'High',
    whyNow: 'Power and capex cycle remain constructive for regulated cash-flow compounders.',
    catalysts: ['Capacity updates', 'Thermal / RE mix'],
    confidence: 0.68,
  },
  {
    company: 'SUNPHARMA',
    name: 'Sun Pharma',
    opportunityScore: 64,
    researchPriority: 'Medium',
    whyNow: 'Specialty franchise and US portfolio updates warrant continued research coverage.',
    catalysts: ['US specialty', 'Guidance'],
    confidence: 0.61,
  },
];

export const DEFAULT_AI_BRIEF = {
  marketSummary:
    'Indian equities trade in a selective risk-on regime. Financials and defence retain institutional attention while midcap breadth stays mixed.',
  keyRisks: [
    'Global yield volatility transmitting into domestic risk appetite',
    'Oil price rebound compressing consumption margins',
    'Earnings misses among rate-sensitive names',
  ],
  topOpportunities: [
    'Private banks with deposit franchise strength',
    'Defence names with order-book visibility',
    'Power / capex beneficiaries with regulated cash flows',
  ],
  sectorRotation: 'Leadership remains concentrated in financials, defence and selective industrials; IT stays watch-list selective.',
  institutionalFlows: 'Domestic institutions remain constructive; foreign flows stay selective across large-caps.',
  macroOutlook: 'Policy tone, real rates and USDINR remain the primary macro swing factors for the next research window.',
};

export const DEFAULT_COVERAGE = {
  companiesCovered: 120,
  researchNotesPublished: 186,
  morningOfficeStatus: 'Operational',
  knowledgeGraph: 'Online',
  companyMemory: 'Online',
  opportunityEngine: 'Online',
  regressionStatus: 'Passing',
  dataFreshness: 'Intraday',
  lastSync: null,
};

export function scoreFromSentiment(sentiment = '', strength = '') {
  const s = String(sentiment).toLowerCase();
  const n = Number(String(strength).replace(/[^\d.]/g, ''));
  if (Number.isFinite(n) && n > 0) return Math.min(99, Math.round(n));
  if (s.includes('bull')) return 68;
  if (s.includes('bear')) return 38;
  if (s.includes('neutral')) return 52;
  return 50;
}

export function normalizeSentiment(sentiment = '') {
  const s = String(sentiment).toLowerCase();
  if (s.includes('bull')) return 'Bullish';
  if (s.includes('bear')) return 'Bearish';
  if (s.includes('neutral')) return 'Neutral';
  if (s.includes('calculat') || s.includes('pending') || s.includes('sync')) return 'Syncing';
  return sentiment || 'Neutral';
}

export function matchOutlookIndices(indexSentiments = []) {
  const aliases = [
    { key: 'nifty50', match: /nifty\s*50(?!\s*next)|^nifty$/i, label: 'NIFTY 50' },
    { key: 'sensex', match: /sensex/i, label: 'SENSEX' },
    { key: 'banknifty', match: /bank/i, label: 'BANK NIFTY' },
    { key: 'usdinr', match: /usd\s*inr|usdinr|inr/i, label: 'USD/INR' },
    { key: 'gold', match: /gold/i, label: 'GOLD' },
    { key: 'brent', match: /brent|crude|oil/i, label: 'BRENT' },
    { key: 'us10y', match: /us\s*10|ust\s*10|treasury/i, label: 'US 10Y' },
    { key: 'btc', match: /btc|bitcoin/i, label: 'BTC' },
    { key: 'india10y', match: /india\s*10|g-?sec|in10/i, label: 'India 10Y' },
  ];
  return aliases.map((alias) => {
    const hit = indexSentiments.find((row) => alias.match.test(row.label || row.key || row.name || ''));
    const fallback = DEFAULT_OUTLOOK.find((d) => d.key === alias.key);
    if (!hit) return { ...fallback };
    const sentiment = normalizeSentiment(hit.sentiment || hit.mood || hit.direction);
    return {
      key: alias.key,
      label: alias.label,
      sentiment,
      score: scoreFromSentiment(hit.sentiment, hit.strength || hit.score),
      path: fallback?.path || '/market-intelligence',
    };
  });
}

export function resolveBoardRow(defs, snapshot = [], sentiments = []) {
  return defs.map((def) => {
    const fromSnap = snapshot.find((row) => def.match.test(row.name || row.label || row.key || ''));
    const fromSent = sentiments.find((row) => def.match.test(row.label || row.key || row.name || ''));
    const price = fromSnap?.price ?? fromSnap?.last ?? fromSnap?.value ?? null;
    const pct = fromSnap?.percentChange ?? fromSnap?.change_pct ?? fromSnap?.pct ?? null;
    const sentiment = normalizeSentiment(fromSent?.sentiment || fromSnap?.session || '');
    return {
      key: def.key,
      label: def.label,
      price,
      pct,
      sentiment: sentiment === 'Syncing' ? '—' : sentiment,
      session: fromSnap?.session || null,
    };
  });
}

export function articleMatchesTab(article, tab) {
  if (!article || !tab) return false;
  const blob = [
    article.title,
    article.excerpt,
    article.section,
    article.category,
    ...(Array.isArray(article.tags) ? article.tags : []),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return tab.match.test(blob);
}

export function articleMatchesSession(article, session) {
  if (!article || !session) return false;
  const blob = [
    article.title,
    article.excerpt,
    article.section,
    article.category,
    ...(Array.isArray(article.tags) ? article.tags : []),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return session.topics.some((topic) => {
    const words = topic.toLowerCase().split(/\s+/).filter((w) => w.length > 3);
    return words.some((w) => blob.includes(w));
  });
}

export function enrichResearchCard(article) {
  if (!article) return null;
  const excerpt = article.excerpt || article.summary || '';
  return {
    ...article,
    href: article.href || null,
    executiveSummary: article.executiveSummary || excerpt,
    whyItMatters:
      article.whyItMatters ||
      article.why_it_matters ||
      (excerpt
        ? `Institutional relevance: ${excerpt.slice(0, 140)}${excerpt.length > 140 ? '…' : ''}`
        : 'Material for portfolio and sector monitoring.'),
    affectedCompanies: article.affectedCompanies || article.companies || article.tickers || [],
    affectedSectors: article.affectedSectors || (article.sector ? [article.sector] : article.category ? [article.category] : []),
    marketImpact: article.marketImpact || article.market_impact || 'Monitor positioning and relative performance.',
    readTime: article.readTime || article.read_time || '3 min read',
    premium: Boolean(article.premium || article.isPremium || /premium|institutional/i.test(article.section || '')),
    publishedLabel: article.publishedLabel || article.date || article.published_at,
  };
}
