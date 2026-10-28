/**
 * Soft view-model for the Macro Chief Economist Workstation.
 * Maps /api/market/macro-briefing into explainable intelligence objects.
 */

function asList(v) {
  return Array.isArray(v) ? v.filter(Boolean) : [];
}

function evidenceForIndicator(brief, indicator = {}) {
  const evidence = brief?.evidence || {};
  const id = String(indicator.id || indicator.label || '').toLowerCase();
  const label = String(indicator.label || '').toLowerCase();
  if (/inflat|cpi|food/.test(id + label)) return evidence.inflation || {};
  if (/rate|yield|fed|rbi|policy/.test(id + label)) return evidence.interestRates || {};
  if (/fx|dollar|inr|currency/.test(id + label)) return evidence.currency || {};
  if (/oil|gold|commodit|energy/.test(id + label)) return evidence.commodities || {};
  if (/bond|duration/.test(id + label)) return evidence.bonds || {};
  return evidence.global || {};
}

export function buildExplainableCards(briefing) {
  const brief = briefing?.chiefEconomistBrief || {};
  const workspace = briefing?.workspace || {};
  const indicators = asList(workspace.indicators);
  const confidence = workspace.confidenceBreakdown || {};

  return indicators.map((item) => {
    const ev = evidenceForIndicator(brief, item);
    return {
      id: item.id,
      label: item.label,
      value: item.value,
      status: item.status,
      tone: item.tone || 'neutral',
      sparkline: item.sparkline || [],
      source: item.source || (briefing?.sourcesUsed || [])[0] || 'AGI desk',
      asOf: item.asOf,
      trend: item.status,
      why: ev.evidence || item.why || `${item.label} is assessed from the current institutional macro desk read.`,
      forecast: ev.marketImpact || 'Watch the next data print and policy communication for confirmation.',
      confidence: confidence.score ?? brief.confidence ?? null,
      risks: asList(brief.keyRisks)
        .slice(0, 2)
        .map((r) => (typeof r === 'string' ? r : r.label || r.why))
        .filter(Boolean),
      implication:
        ev.marketImpact ||
        (item.tone === 'positive'
          ? 'Supportive for risk assets and rate-sensitive domestic demand.'
          : item.tone === 'negative'
            ? 'Tightens financial conditions and raises selective risk premia.'
            : 'Neutral near-term; position sizing should stay data-dependent.'),
      drivers: asList(brief.whyReached)
        .slice(0, 3)
        .map((w) => w.title || w.explanation)
        .filter(Boolean),
    };
  });
}

const BASE_COUNTRIES = ['USA', 'Europe', 'China', 'Japan', 'UK', 'Emerging Markets', 'India'];

export function buildCountryCards(briefing) {
  const live = asList(briefing?.snapshot?.countries);
  const byName = new Map(live.map((c) => [String(c.name).toLowerCase(), c]));

  return BASE_COUNTRIES.map((name) => {
    const c =
      byName.get(name.toLowerCase()) ||
      live.find((row) => String(row.name || '').toLowerCase().includes(name.split(' ')[0].toLowerCase())) ||
      {};
    return {
      name: c.name || name,
      condition: c.condition || 'Data-dependent',
      why:
        c.why ||
        `${name} activity, inflation and policy remain a key input into global risk appetite and India’s external accounts.`,
      gdp: c.gdp || 'Watch next print',
      inflation: c.inflation || 'Watch next print',
      rates: c.rates || 'Policy path data-dependent',
      employment: c.employment || 'Labour market still material for demand',
      transmissionToIndia:
        /india/i.test(name)
          ? 'Domestic anchor for growth, inflation and policy.'
          : `${name} conditions transmit to India through trade, commodity demand, capital flows and global risk appetite.`,
      transmissionToMarkets:
        c.marketImpact ||
        'Equity risk premium, bond yields and INR move with the growth–inflation–policy triangle.',
      forecast: `Near-term outlook remains ${String(c.condition || 'data-dependent').toLowerCase()} pending the next activity and inflation prints.`,
    };
  });
}

const BASE_COMMODITIES = [
  'Oil',
  'Natural Gas',
  'Coal',
  'Gold',
  'Silver',
  'Copper',
  'Iron Ore',
  'Lithium',
  'Wheat',
  'Rice',
  'Corn',
  'Sugar',
  'Coffee',
];

export function buildCommodityCards(briefing) {
  const live = asList(briefing?.snapshot?.commodities);
  const byName = new Map(live.map((c) => [String(c.name).toLowerCase(), c]));

  return BASE_COMMODITIES.map((name) => {
    const c =
      byName.get(name.toLowerCase()) ||
      live.find((row) => String(row.name || '').toLowerCase().includes(name.toLowerCase().split(' ')[0])) ||
      {};
    const label = c.name || name;
    return {
      name: label,
      direction: c.direction || 'Monitor',
      source: c.source || 'AGI Commodities Desk',
      why:
        c.implication ||
        `${label} is ${String(c.direction || 'stable').toLowerCase()} — relevant for India’s inflation, deficits and sector margins.`,
      indiaImpact:
        /oil|crude|natgas|gas|coal/i.test(label)
          ? 'Energy complex feeds CPI, CAD and transport costs; banks/autos/airlines absorb second-round effects.'
          : /gold|silver/i.test(label)
            ? 'Precious metals track global real rates, INR and safe-haven demand.'
            : /wheat|rice|corn|sugar|coffee|food/i.test(label)
              ? 'Food complex feeds CPI, rural incomes and RBI’s inflation reaction function.'
              : 'Commodity impulse feeds input costs, export competitiveness and sector earnings.',
      investment:
        String(c.direction).toLowerCase() === 'easing'
          ? 'Easing impulse supports consumers and rate-sensitive demand; energy producers face pricing pressure.'
          : String(c.direction).toLowerCase() === 'firming'
            ? 'Firming prices raise inflation risk and support commodity-linked producers.'
            : 'Monitor inventories, geopolitics and INR pass-through.',
    };
  });
}

export function buildFxCards(briefing) {
  return asList(briefing?.snapshot?.fx).map((fx) => ({
    pair: fx.pair,
    value: fx.value,
    direction: fx.direction,
    implication: fx.implication,
    asOf: fx.asOf,
    why: fx.implication || 'FX conditions shape imported inflation and portfolio flows.',
  }));
}

export function buildScenarios(briefing) {
  const risks = asList(briefing?.snapshot?.risks || briefing?.chiefEconomistBrief?.keyRisks);
  const base = [
    {
      id: 'oil-120',
      title: 'Oil at $120',
      probability: 'Low–Medium',
      gdp: 'Lower growth impulse',
      inflation: 'Higher CPI / sticky core',
      rates: 'RBI stays on hold longer',
      inr: 'Pressure via CAD',
      nifty: 'PE compression in rate-sensitive names',
      sectors: { winners: ['Energy producers'], losers: ['Airlines', 'Autos', 'FMCG margins'] },
    },
    {
      id: 'fed-cuts',
      title: 'Fed cuts 100bps',
      probability: 'Medium',
      gdp: 'Supportive for EM growth',
      inflation: 'Global disinflation narrative improves',
      rates: 'Domestic financial conditions ease',
      inr: 'Supportive vs USD',
      nifty: 'Risk-on bid for financials & cyclicals',
      sectors: { winners: ['Banks', 'Real Estate', 'Capital Goods'], losers: ['Defensive cash proxies'] },
    },
    {
      id: 'india-drought',
      title: 'India drought / weak monsoon',
      probability: 'Low–Medium',
      gdp: 'Rural demand softens',
      inflation: 'Food inflation spikes',
      rates: 'RBI policy room narrows',
      inr: 'Mixed',
      nifty: 'Selective derating in rural/consumer',
      sectors: { winners: ['Agri-inputs selective'], losers: ['FMCG', 'Autos', 'Rural lenders'] },
    },
  ];

  const fromRisks = risks.slice(0, 3).map((r, i) => ({
    id: `risk-${i}`,
    title: typeof r === 'string' ? r : r.label,
    probability: typeof r === 'object' ? r.level || 'Medium' : 'Medium',
    gdp: 'Path-dependent on shock severity',
    inflation: /oil|inflat/i.test(JSON.stringify(r)) ? 'Upside risk' : 'Data-dependent',
    rates: 'Policy stays cautious',
    inr: 'Watch capital-flow channel',
    nifty: 'Higher risk premium until clarity',
    sectors: {
      winners: [],
      losers: asList(typeof r === 'object' ? r.affected : []),
    },
    why: typeof r === 'object' ? r.why : null,
    watch: typeof r === 'object' ? r.watch : null,
  }));

  return [...base, ...fromRisks];
}

export function buildCentralBanks(briefing) {
  const rates = asList(briefing?.snapshot?.rates);
  const policy = asList(briefing?.snapshot?.policyTracker);
  const fed = rates.find((r) => /federal funds/i.test(r.label));
  const us10y = rates.find((r) => /10y/i.test(r.label));
  const rbi = policy.find((p) => /rbi/i.test(p.body));
  const finance = policy.find((p) => /finance|budget/i.test(p.body));

  return [
    {
      id: 'fed',
      name: 'Federal Reserve',
      currentRate: fed?.value != null ? `${fed.value}%` : '—',
      direction: fed?.direction || 'Data-dependent',
      marketPricing: us10y ? `US 10Y ${us10y.value}%` : 'Watch UST curve',
      nextMeeting: 'See economic calendar',
      aiOpinion:
        briefing?.chiefEconomistBrief?.evidence?.interestRates?.evidence ||
        'Global rates remain a key EM liquidity and valuation transmission channel.',
      history: fed?.history || us10y?.history || [],
      source: fed?.source || 'FRED',
    },
    {
      id: 'rbi',
      name: 'Reserve Bank of India',
      currentRate: 'Data-dependent stance',
      direction: rbi?.whatChanged || 'Growth–inflation trade-off',
      marketPricing: 'Domestic financial conditions',
      nextMeeting: asList(briefing?.snapshot?.calendar).find((c) => /rbi/i.test(c.event))?.date || 'Upcoming',
      aiOpinion: rbi?.whyItMatters || 'RBI anchors credit, duration and INR stability for India portfolios.',
      affected: rbi?.whoAffected,
      history: [],
      source: 'AGI Policy Tracker',
    },
    {
      id: 'fiscal',
      name: 'India Fiscal Impulse',
      currentRate: finance?.whatChanged || 'Capex orientation',
      direction: 'Structural',
      marketPricing: 'Bond supply vs growth durability',
      nextMeeting: 'Budget / GST cycle',
      aiOpinion: finance?.whyItMatters || 'Fiscal quality influences growth durability and bond supply.',
      affected: finance?.whoAffected,
      history: [],
      source: 'AGI Policy Tracker',
    },
  ];
}

const INDIA_DESK = [
  'GDP',
  'Headline Inflation',
  'Core Inflation',
  'Fiscal Deficit',
  'GST Collections',
  'Power Demand',
  'Rail Freight',
  'UPI',
  'Bank Credit',
  'Manufacturing PMI',
  'Services PMI',
  'Exports',
  'Imports',
  'Forex Reserves',
  'Current Account',
  'Government Spending',
  'Consumption',
  'Housing',
  'Auto Sales',
  'Employment',
  'Rural Demand',
  'Monsoon',
  'Food Inflation',
  'MSP',
];

export function indiaIndicators(briefing) {
  const cards = buildExplainableCards(briefing);
  const live = cards.filter((c) => /india|gst|upi|credit|monsoon|cpi|gdp|pmi|fiscal|export|import|forex/i.test(`${c.id} ${c.label}`));
  const byLabel = new Map(live.map((c) => [String(c.label).toLowerCase(), c]));
  const weather = briefing?.snapshot?.weather || {};

  return INDIA_DESK.map((label) => {
    const hit =
      byLabel.get(label.toLowerCase()) ||
      live.find((c) => String(c.label || '').toLowerCase().includes(label.split(' ')[0].toLowerCase()));
    if (hit) return hit;
    const monsoonHint =
      /monsoon|food|rural|msp/i.test(label) && weather.implication
        ? weather.implication
        : null;
    return {
      id: `india-${label.toLowerCase().replace(/\s+/g, '-')}`,
      label,
      value: 'Desk watch',
      status: 'Monitor',
      tone: 'neutral',
      why:
        monsoonHint ||
        `${label} is part of the India high-frequency / structural monitor used by the AGI economist desk.`,
      forecast: 'Awaiting the next official print or high-frequency update.',
      confidence: briefing?.workspace?.confidenceBreakdown?.score ?? briefing?.chiefEconomistBrief?.confidence ?? null,
      implication: 'Interpret jointly with growth, inflation, fiscal and RBI stance before sizing India risk.',
      source: 'AGI India Monitor',
    };
  });
}

export function WORKSPACES() {
  return [
    { id: 'overview', label: 'Executive Brief', group: 'Desk' },
    { id: 'global', label: 'Global Monitor', group: 'Desk' },
    { id: 'india', label: 'India Monitor', group: 'Desk' },
    { id: 'central-banks', label: 'Central Banks', group: 'Markets' },
    { id: 'dashboard', label: 'Macro Dashboard', group: 'Markets' },
    { id: 'commodities', label: 'Commodities', group: 'Markets' },
    { id: 'currencies', label: 'Currencies', group: 'Markets' },
    { id: 'calendar', label: 'Economic Calendar', group: 'Policy' },
    { id: 'policy', label: 'Policy Tracker', group: 'Policy' },
    { id: 'transmission', label: 'Transmission Maps', group: 'Intelligence' },
    { id: 'sectors', label: 'Sector Impact', group: 'Intelligence' },
    { id: 'scenarios', label: 'Scenario Analysis', group: 'Intelligence' },
    { id: 'historical', label: 'Historical Data', group: 'Intelligence' },
    { id: 'forecasts', label: 'Forecast Models', group: 'Intelligence' },
    { id: 'research', label: 'Research Library', group: 'Intelligence' },
    { id: 'knowledge', label: 'Knowledge Graph', group: 'Intelligence' },
    { id: 'watchlist', label: 'Watchlists', group: 'Personal' },
    { id: 'alerts', label: 'Alerts', group: 'Personal' },
    { id: 'ask', label: 'Ask AI Economist', group: 'Personal' },
    { id: 'settings', label: 'Settings', group: 'Personal' },
  ];
}

export const TOP_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'global', label: 'Global Economy' },
  { id: 'india', label: 'India Focus' },
  { id: 'central-banks', label: 'Monetary Policy' },
  { id: 'commodities', label: 'Commodities' },
  { id: 'currencies', label: 'Currencies' },
  { id: 'policy', label: 'Policy Tracker' },
  { id: 'watchlist', label: 'Watchlist' },
];
