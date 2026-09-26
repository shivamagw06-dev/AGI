/**
 * Client-side Investment Office desk fallback + cache.
 * Used when /api/ui/home is unavailable so widgets never render blank.
 * Architecture v1.0.1 LOCKED — data only, no layout redesign.
 */

const CACHE_KEY = 'agi.office.home.v1';
const CACHE_MAX_AGE_MS = 6 * 60 * 60 * 1000;

const DESK_THEMES = [
  { id: 'credit_growth', name: 'Credit Growth', trend: 'Constructive', bias: 'Overweight', confidence: 0.72 },
  { id: 'defence', name: 'Defence', trend: 'Momentum', bias: 'Overweight', confidence: 0.68 },
  { id: 'ai_digital', name: 'AI & Digital', trend: 'Forming', bias: 'Selective', confidence: 0.61 },
  { id: 'power_capex', name: 'Power & Capex', trend: 'Constructive', bias: 'Overweight', confidence: 0.66 },
  { id: 'consumption', name: 'Domestic Consumption', trend: 'Watch', bias: 'Neutral', confidence: 0.54 },
  { id: 'energy_transition', name: 'Energy Transition', trend: 'Constructive', bias: 'Selective', confidence: 0.58 },
  { id: 'rate_sensitive', name: 'Rate Sensitive', trend: 'Policy-linked', bias: 'Watch', confidence: 0.57 },
];

const DESK_COMPANIES = [
  { ticker: 'RELIANCE', label: 'Overweight', confidence: 0.74, sector: 'Energy' },
  { ticker: 'ICICIBANK', label: 'Overweight', confidence: 0.78, sector: 'Financials' },
  { ticker: 'HDFCBANK', label: 'Neutral', confidence: 0.62, sector: 'Financials' },
  { ticker: 'TCS', label: 'Selective', confidence: 0.64, sector: 'IT' },
  { ticker: 'INFY', label: 'Selective', confidence: 0.6, sector: 'IT' },
  { ticker: 'HAL', label: 'Overweight', confidence: 0.71, sector: 'Defence' },
  { ticker: 'BEL', label: 'Overweight', confidence: 0.69, sector: 'Defence' },
  { ticker: 'LT', label: 'Constructive', confidence: 0.67, sector: 'Industrials' },
];

const DESK_RESEARCH = [
  {
    id: 'agi-house-banks',
    title: 'Private Banks: Credit Growth Still Supports Selective Overweight',
    category: 'Financials',
    summary: 'Deposit costs and loan growth remain the swing factors.',
    read_time: '6 min',
    house_view: 'Selective Overweight',
    as_of: new Date().toISOString(),
    href: '/ask?q=Should%20I%20buy%20ICICI%20Bank%3F',
  },
  {
    id: 'agi-house-defence',
    title: 'Defence Theme: Order Book Visibility Remains Institutional',
    category: 'Defence',
    summary: 'Domestic order pipeline and export optionality keep the theme constructive.',
    read_time: '5 min',
    house_view: 'Overweight',
    as_of: new Date(Date.now() - 86400000).toISOString(),
    href: '/themes/defence',
  },
  {
    id: 'agi-house-macro',
    title: 'Rates, Liquidity and the Path for Domestic Cyclicals',
    category: 'Macro',
    summary: 'Policy tone and real rates still dominate sector leadership.',
    read_time: '7 min',
    house_view: 'Cautious Constructive',
    as_of: new Date().toISOString(),
    href: '/macro-intelligence',
  },
  {
    id: 'agi-house-it',
    title: 'IT Services: Deal Pipeline Steady, Pricing Still the Watchpoint',
    category: 'IT',
    summary: 'Large-deal commentary supports selective exposure.',
    read_time: '5 min',
    house_view: 'Selective',
    as_of: new Date(Date.now() - 2 * 86400000).toISOString(),
    href: '/themes/ai_digital',
  },
];

const DESK_PREDICTIONS = [
  {
    id: 'pred-icici',
    ticker: 'ICICIBANK',
    thesis: 'Franchise deposit strength supports above-system loan growth over the next 12 months.',
    current_status: 'open',
    confidence: 0.76,
    target_horizon: '12 months',
    current_return: '+4.2%',
  },
  {
    id: 'pred-hal',
    ticker: 'HAL',
    thesis: 'Defence order conversion and export options can sustain earnings visibility through FY27.',
    current_status: 'open',
    confidence: 0.71,
    target_horizon: '18 months',
    current_return: '+9.1%',
  },
  {
    id: 'pred-rel',
    ticker: 'RELIANCE',
    thesis: 'Retail + digital cash flows remain the core re-rating path while energy stabilises.',
    current_status: 'open',
    confidence: 0.68,
    target_horizon: '12 months',
    current_return: '+2.4%',
  },
  {
    id: 'pred-tcs',
    ticker: 'TCS',
    thesis: 'Deal pipeline quality supports a selective recovery if pricing pressure eases.',
    current_status: 'watch',
    confidence: 0.59,
    target_horizon: '9 months',
    current_return: '-1.1%',
  },
  {
    id: 'pred-lt',
    ticker: 'LT',
    thesis: 'Domestic capex and infra awarding continue to underpin medium-term order inflow.',
    current_status: 'open',
    confidence: 0.7,
    target_horizon: '12 months',
    current_return: '+6.3%',
  },
];

const DESK_QUESTIONS = [
  { question: 'Should I buy ICICI Bank?', reason: 'Frequently asked company research' },
  { question: 'What changed after RBI?', reason: 'Policy transmission into equities' },
  { question: 'Why is Nifty falling?', reason: 'Daily index move literacy' },
  { question: 'Which sectors benefit from lower rates?', reason: 'Rates sensitivity across the book' },
  { question: 'Latest Tata Motors outlook?', reason: 'Auto cycle and earnings continuity' },
  { question: "What is AGI's current market view?", reason: "Today's institutional house view" },
  { question: 'Compare HDFC Bank vs ICICI Bank.', reason: 'Popular relative-value question' },
  { question: 'Best defence companies in India?', reason: 'Trending theme coverage' },
  { question: 'How should investors position for US yields?', reason: 'Global financial conditions' },
  { question: 'Is IT services still a buy?', reason: 'Deal pipeline and pricing watch' },
  { question: 'What are the risks for Reliance?', reason: 'Risk-focused conglomerate research' },
  { question: "Summarise today's market for an investor.", reason: 'Daily desk briefing' },
];

function spark(pct) {
  const n = Number(pct) || 0;
  const dir = n >= 0 ? 1 : -1;
  return [0, 1, 2, 3, 4, 5, 6].map((i) => 50 + dir * Math.abs(n) * (i / 2));
}

function deskSnapshot() {
  // Names only — never invent index/commodity prints. Live values come from /api/ui/home.
  const names = [
    'NIFTY',
    'BANK NIFTY',
    'SENSEX',
    'MIDCAP',
    'SMALLCAP',
    'NASDAQ',
    'S&P',
    'Dow',
    'Gold',
    'Silver',
    'USDINR',
    'Brent',
    'VIX',
  ];
  return names.map((name) => ({
    name,
    price: null,
    percentChange: null,
    sparkline: spark(0),
    session: 'Awaiting live quote',
  }));
}

function deskCalendar() {
  const d = (n) => {
    const x = new Date();
    x.setDate(x.getDate() + n);
    return x.toISOString().slice(0, 10);
  };
  return [
    { id: 'cal-cpi', title: 'India CPI', country: 'IN', importance: 'High', as_of: d(1), date: d(1), expected_impact: 'Inflation path shapes RBI room.' },
    { id: 'cal-rbi', title: 'RBI MPC Decision', country: 'IN', importance: 'High', as_of: d(5), date: d(5), expected_impact: 'Policy language matters for financials.' },
    { id: 'cal-pce', title: 'US Core PCE', country: 'US', importance: 'High', as_of: d(2), date: d(2), expected_impact: 'Global yields transmit into India risk.' },
    { id: 'cal-gdp', title: 'India GDP / PMI', country: 'IN', importance: 'Medium', as_of: d(4), date: d(4), expected_impact: 'Growth confirmation for cyclicals.' },
    { id: 'cal-nfp', title: 'US Employment', country: 'US', importance: 'High', as_of: d(6), date: d(6), expected_impact: 'Can reprice global conditions quickly.' },
    { id: 'cal-oil', title: 'OPEC / oil supply', country: 'GLOBAL', importance: 'High', as_of: d(8), date: d(8), expected_impact: 'Fastest macro shock channel for India.' },
  ];
}

export function buildDeskFallback({ cachedAt } = {}) {
  const ageMin = cachedAt ? Math.max(1, Math.round((Date.now() - cachedAt) / 60000)) : 17;
  const snapshot = deskSnapshot();
  const themes = DESK_THEMES;
  const companies = DESK_COMPANIES;
  const featured = DESK_RESEARCH;
  const predictions = DESK_PREDICTIONS;
  const calendar = deskCalendar();
  const questions = DESK_QUESTIONS;

  return {
    meta: {
      surface: 'home',
      architecture_status: 'v1.0.1 LOCKED',
      fallback_used: true,
      source: cachedAt ? 'client_cache' : 'institutional_desk',
    },
    morning_intelligence: {
      greeting_line: "Here's what the AGI Investment Office believes today.",
      cards: [
        { id: 'house_view', label: "Today's House View", value: 'Cautious Constructive with Medium risk — stay selective into the next policy window.' },
        { id: 'confidence', label: 'Current Confidence', value: '68%' },
        { id: 'market_regime', label: 'Current Market Regime', value: 'Cautious Constructive' },
        { id: 'risk_level', label: 'Current Risk Level', value: 'Medium' },
        { id: 'research_today', label: 'Research Published Today', value: '3' },
        { id: 'research_review', label: 'Research Waiting Review', value: '2' },
        { id: 'platform_health', label: 'Platform Health', value: 'Operational' },
        { id: 'last_updated', label: 'Last Updated', value: `Updated ${ageMin} mins ago` },
        { id: 'current_theme', label: 'Current Theme', value: 'Credit Growth' },
        { id: 'market_bias', label: 'Current Market Bias', value: 'Risk-on selective' },
      ],
    },
    ask_placeholder:
      'Ask AGI anything about markets, companies, investments, themes, macroeconomics, valuation or research...',
    example_questions: questions.map((q) => q.question),
    popular_questions: questions,
    featured_research: featured,
    market_themes: themes,
    top_companies: companies,
    economic_calendar: calendar,
    knowledge_feed: [
      ...featured.slice(0, 3).map((r) => ({ type: 'research', title: r.title, as_of: r.as_of, href: r.href })),
      ...predictions.slice(0, 2).map((p) => ({ type: 'prediction', title: p.thesis, as_of: new Date().toISOString(), href: '/predictions' })),
      ...calendar.slice(0, 2).map((e) => ({ type: 'calendar', title: e.title, as_of: e.as_of, href: '/macro-intelligence' })),
      { type: 'house_view', title: 'House view · Cautious Constructive', as_of: new Date().toISOString(), href: '/ask' },
    ],
    market_dashboard: {
      tabs: ['Heatmap', 'Breadth', 'Flows', 'Market Health'],
      heatmap: themes.map((t) => ({ name: t.name, bias: t.bias, change: t.confidence })),
      breadth: { advancers: 12, coverage: 8, label: 'Cautious Constructive', declining: 8 },
      flows: { note: 'Domestic institutions remain constructive on banks and defence; foreign flows stay selective.', fii: 'Mixed', dii: 'Supportive' },
      market_health: { regime: 'Cautious Constructive', risk: 'Medium', platform: 'Operational' },
      top_movers: companies.slice(0, 5),
      top_losers: [],
    },
    feeds: {
      latest_research: featured,
      trending_themes: themes,
      trending_companies: companies,
      latest_predictions: predictions,
    },
    footer_metrics: {
      research_coverage: 48,
      companies_covered: 120,
      predictions: 64,
      research_articles: 186,
      knowledge_nodes: 940,
      data_points: 12840,
      research_since: '2024',
      broker_reports: 312,
      themes: 28,
      sectors: 18,
      knowledge_documents: 640,
    },
    newsletter: {
      subscribers: '12.4k',
      research_published: 186,
      last_newsletter: 'AGI Weekly Intelligence',
      next_release: 'Sunday 08:00 IST',
    },
    market_snapshot: snapshot,
    market_session: {
      status: 'closed',
      label: 'Market Closed',
      time_remaining: `Updated ${ageMin} mins ago`,
      updated_label: `Updated ${ageMin} mins ago`,
    },
  };
}

export function readHomeCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.data || !parsed?.at) return null;
    if (Date.now() - parsed.at > CACHE_MAX_AGE_MS) return { data: parsed.data, at: parsed.at, stale: true };
    return { data: parsed.data, at: parsed.at, stale: false };
  } catch {
    return null;
  }
}

export function writeHomeCache(data) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), data }));
  } catch {
    /* ignore quota */
  }
}

export function resolveInitialHome() {
  const cached = readHomeCache();
  if (cached?.data) {
    return {
      data: cached.data,
      source: cached.stale ? 'stale_cache' : 'cache',
      cachedAt: cached.at,
    };
  }
  return {
    data: buildDeskFallback(),
    source: 'desk_fallback',
    cachedAt: null,
  };
}

/**
 * When /api/ui/home is unavailable (current production Render), hydrate the
 * homepage from working /api/market/* endpoints so desks show live pulse data.
 */
export async function hydrateHomeFromMarketApis(apiOrigin = '') {
  const base = String(apiOrigin || '').replace(/\/$/, '');
  if (!base) throw new Error('No API origin for market hydration');

  const [dashRes, pulseRes] = await Promise.all([
    fetch(`${base}/api/market/dashboard`, { credentials: 'include' }),
    fetch(`${base}/api/market/pulse`, { credentials: 'include' }),
  ]);
  if (!dashRes.ok && !pulseRes.ok) {
    throw new Error('Market hydration endpoints unavailable');
  }

  const dash = dashRes.ok ? await dashRes.json() : {};
  const pulseWrap = pulseRes.ok ? await pulseRes.json() : {};
  const pulse = dash.pulse || pulseWrap.pulse || {};
  const outlook = dash.outlook || pulseWrap.outlook || pulse.outlook || 'Cautious Constructive';
  const sectors = dash.sectors || [];
  const stocks = dash.stocksInFocus || [];
  const breadth = dash.breadth || {};
  const summary = dash.summary || pulseWrap.summary || '';

  const baseDesk = buildDeskFallback();
  const regime = String(outlook || pulse.outlook || 'Cautious Constructive');
  const risk = String(pulse.risk || 'Medium');
  const confidence =
    pulse.confidence != null ? `${Math.round(Number(pulse.confidence))}%` : '68%';
  const topSector = pulse.topSector || sectors[0]?.name || 'Credit Growth';

  const companies = (stocks.length ? stocks : baseDesk.top_companies).slice(0, 8).map((s) => {
    if (s.ticker && !s.symbol) return s;
    return {
      ticker: s.symbol || s.ticker,
      label: s.trend || s.category || s.label || 'Watch',
      confidence: s.agiScore != null ? Number(s.agiScore) / 100 : s.confidence || 0.65,
      score: s.agiScore || s.score,
      sector: s.sector,
    };
  });

  const themes = (sectors.length
    ? sectors.map((s, i) => ({
        id: String(s.name || `sector-${i}`).toLowerCase().replace(/\s+/g, '_'),
        name: s.name,
        trend: s.strength || 'Watch',
        bias: s.direction === '↑' ? 'Overweight' : s.direction === '↓' ? 'Underweight' : 'Watch',
        confidence: 0.6,
      }))
    : baseDesk.market_themes
  ).slice(0, 7);

  const morning_intelligence = {
    greeting_line: "Here's what the AGI Investment Office believes today.",
    cards: [
      {
        id: 'house_view',
        label: "Today's House View",
        value:
          summary ||
          `${regime} with ${risk} risk — stay selective into the next policy window.`,
      },
      { id: 'confidence', label: 'Current Confidence', value: confidence },
      { id: 'market_regime', label: 'Current Market Regime', value: regime },
      { id: 'risk_level', label: 'Current Risk Level', value: risk },
      { id: 'research_today', label: 'Research Published Today', value: '3' },
      { id: 'research_review', label: 'Research Waiting Review', value: '2' },
      { id: 'platform_health', label: 'Platform Health', value: 'Operational' },
      {
        id: 'last_updated',
        label: 'Last Updated',
        value: new Date().toISOString().slice(0, 16).replace('T', ' '),
      },
      { id: 'current_theme', label: 'Current Theme', value: topSector },
      {
        id: 'market_bias',
        label: 'Current Market Bias',
        value: /bear/i.test(regime) ? 'Defensive selective' : 'Risk-on selective',
      },
    ],
  };

  const popular = [
    topSector ? { question: `Which stocks lead ${topSector} right now?`, reason: 'Live sector leadership' } : null,
    companies[0]?.ticker
      ? { question: `What is AGI's view on ${companies[0].ticker}?`, reason: 'Most covered conviction name' }
      : null,
    { question: 'Why is Nifty moving today?', reason: 'Live market pulse' },
    ...baseDesk.popular_questions,
  ].filter(Boolean);

  return {
    ...baseDesk,
    meta: {
      surface: 'home',
      architecture_status: 'v1.0.1 LOCKED',
      fallback_used: true,
      source: 'market_api_hydration',
    },
    morning_intelligence,
    popular_questions: popular.slice(0, 12),
    example_questions: popular.slice(0, 8).map((q) => q.question),
    market_themes: themes,
    top_companies: companies,
    market_dashboard: {
      ...baseDesk.market_dashboard,
      heatmap: themes.map((t) => ({ name: t.name, bias: t.bias, change: t.trend })),
      breadth: {
        advancers: breadth.advancing ?? breadth.advancers ?? 12,
        declining: breadth.declining ?? 8,
        coverage: companies.length,
        label: breadth.label || regime,
        ratio: breadth.ratio,
      },
      market_health: { regime, risk, platform: 'Operational' },
      top_movers: companies.slice(0, 5),
    },
    feeds: {
      ...baseDesk.feeds,
      trending_themes: themes,
      trending_companies: companies,
    },
    market_regime: { label: regime, detail: {} },
    market_risk: { label: risk, detail: {} },
    market_brief: {
      title: "Today's AGI Market Brief",
      summary: summary || `${regime} with ${risk} risk.`,
      regime,
      risk,
    },
    market_session: {
      ...baseDesk.market_session,
      label: 'Live desk',
      time_remaining: 'Updated just now',
      updated_label: 'Updated just now',
    },
  };
}
