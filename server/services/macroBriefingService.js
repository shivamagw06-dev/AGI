/**
 * AGI Chief Economist briefing — one AI note + structured macro intelligence.
 * Persists through macroRepository so restarts and upstream failures never blank the page.
 */

import { getMacroContext } from './macroContextService.js';
import {
  getBriefingCache,
  saveBriefingCache,
  isFresh,
  MACRO_REFRESH_MS,
} from './macroRepository.js';

const CACHE_MS = MACRO_REFRESH_MS.macro_briefing;
let memory = null;
let inflight = null;
let scheduler = null;

function oilDirection(commodities = []) {
  return commodities.find((item) => /oil|crude/i.test(item.name))?.direction || 'Stable';
}

function goldDirection(commodities = []) {
  return commodities.find((item) => /gold/i.test(item.name))?.direction || 'Stable';
}

function buildTransmissionMaps(context) {
  const oil = oilDirection(context.commodities);
  const fx = context.fx?.[0]?.direction || 'Stable';
  const weather = context.weather?.rainfallOutlook || 'Mixed';

  return [
    {
      id: 'oil',
      title: 'Oil transmission',
      trigger: oil === 'Firming' ? 'Higher oil prices' : oil === 'Easing' ? 'Softer oil prices' : 'Stable oil prices',
      steps: oil === 'Firming'
        ? ['Higher transportation costs', 'Stickier inflation pressure', 'Narrower room for policy easing', 'Pressure on autos and discretionary demand', 'Support for energy producers']
        : oil === 'Easing'
          ? ['Lower transportation costs', 'Softer inflation impulse', 'Wider room for growth-supportive policy', 'Relief for rate-sensitive demand', 'Weaker near-term energy pricing power']
          : ['Contained energy impulse', 'Inflation remains data-dependent', 'Policy remains cautious', 'Sector impact stays selective', 'Institutions watch geopolitics'],
    },
    {
      id: 'dollar',
      title: 'Dollar / INR transmission',
      trigger: fx === 'Firming' ? 'Stronger dollar backdrop' : 'Dollar conditions remain mixed',
      steps: [
        'Imported inflation sensitivity changes',
        'Current-account and commodity cost pressure adjusts',
        'RBI policy trade-offs shift',
        'Export competitiveness and overseas earnings are reassessed',
        'Financial conditions for EM assets recalibrate',
      ],
    },
    {
      id: 'monsoon',
      title: 'Weather / monsoon transmission',
      trigger: weather === 'Dry' ? 'Weak rainfall outlook' : weather === 'Wet' ? 'Supportive rainfall outlook' : 'Mixed weather outlook',
      steps: weather === 'Dry'
        ? ['Food-price risk rises', 'Rural income uncertainty increases', 'Inflation stickiness becomes more policy-relevant', 'Agri and FMCG demand paths diverge', 'Power and irrigation stress is monitored']
        : ['Food-price risk eases at the margin', 'Rural demand support becomes more plausible', 'Inflation risk softens selectively', 'Agri-linked cash flows improve in probability', 'Power demand and hydro generation remain secondary watches'],
    },
  ];
}

function buildSectorImpact(context) {
  const oil = oilDirection(context.commodities);
  return {
    beneficiaries: oil === 'Firming'
      ? [
        { name: 'Energy producers', why: 'Higher oil supports pricing power and cash-flow expectations for upstream energy.' },
        { name: 'Banks (selectively)', why: 'If policy stays restrictive for longer, net interest margins can remain supported even as credit demand slows.' },
      ]
      : [
        { name: 'Rate-sensitive demand', why: 'A softer commodity impulse improves the odds that financial conditions do not tighten further.' },
        { name: 'Consumer and auto-linked demand', why: 'Lower input-cost pressure reduces the risk of margin and demand compression.' },
      ],
    challenged: oil === 'Firming'
      ? [
        { name: 'Autos', why: 'Higher fuel and input costs can delay purchases and pressure volumes.' },
        { name: 'Airlines / logistics', why: 'Fuel is a major cost line; firm oil compresses margins unless fares fully reprice.' },
        { name: 'Discretionary consumption', why: 'Stickier inflation and tighter financial conditions weigh on real purchasing power.' },
      ]
      : [
        { name: 'Energy producers', why: 'Softer oil reduces near-term pricing power even if structural demand remains intact.' },
        { name: 'Defensive hedges', why: 'Lower macro stress can reduce the relative appeal of pure defensive positioning.' },
      ],
  };
}

function buildChiefEconomistBrief(context) {
  const oil = oilDirection(context.commodities);
  const gold = goldDirection(context.commodities);
  const india = context.countries.find((c) => c.name === 'India');
  const us = context.countries.find((c) => c.name === 'United States');
  const weather = context.weather || {};
  const sourcesCount = context.sourcesUsed?.length || 0;

  const outlook = oil === 'Firming' || weather.rainfallOutlook === 'Dry' ? 'Cautious' : 'Constructive but data-dependent';
  const confidence = Math.max(42, Math.min(78, 48 + sourcesCount * 4 - (context.missingSources?.length || 0) * 3));

  const whyReached = [
    {
      title: 'Energy and inflation transmission',
      explanation: `AGI places energy at the centre of today’s macro read because oil is ${String(oil).toLowerCase()}. For India, oil is not merely a commodity print — it feeds transportation costs, inflation persistence and the room available for policy easing.`,
    },
    {
      title: 'Domestic growth–inflation balance',
      explanation: india?.why || 'India’s policy constraint remains the balance between growth durability and inflation control.',
    },
    {
      title: 'Global financial conditions',
      explanation: us?.why || 'US policy continues to set the global liquidity backdrop that affects EM risk appetite, the dollar and capital flows.',
    },
    {
      title: 'Weather and food-price channel',
      explanation: weather.implication || 'Monsoon and heat conditions remain relevant for food inflation and rural demand.',
    },
    gold !== 'Stable' ? {
      title: 'Uncertainty hedge signal',
      explanation: `Gold is ${String(gold).toLowerCase()}, which AGI reads as a supporting signal of residual macro or geopolitical uncertainty rather than as a trading recommendation.`,
    } : null,
  ].filter(Boolean).slice(0, 5);

  const executiveThesis = [
    `AGI’s Chief Economist Desk currently characterises the macro backdrop as ${String(outlook).toLowerCase()} because energy, domestic inflation constraints and global financial conditions are not sending a clean one-way signal.`,
    `The central issue for institutions is transmission: whether oil, currency and weather conditions keep inflation sticky enough to delay policy relief, or whether growth durability remains strong enough to absorb that pressure.`,
    `India remains relatively better placed than many peers on growth, but the investment implication is selective rather than blanket risk-on. Rate-sensitive and fuel-intensive sectors remain more exposed when oil firms, while energy and balance-sheet quality matter more when policy stays cautious.`,
    `AGI therefore keeps a conditional stance: constructive on India’s medium-term demand story, cautious on near-term inflation and policy sequencing, and focused on catalysts that can invalidate either side of the debate.`,
  ].join(' ');

  return {
    title: 'AGI Chief Economist Brief',
    subtitle: 'Daily institutional macroeconomic strategy note',
    outlook,
    confidence,
    confidenceRationale: `Confidence is ${confidence}% because ${sourcesCount} evidence categories are available, while ${context.missingSources?.length || 0} configured external feeds are still missing. Cross-signal disagreement between energy, growth and weather keeps conviction measured rather than absolute.`,
    executiveThesis,
    whyReached,
    evidence: {
      inflation: {
        trend: oil === 'Firming' || weather.rainfallOutlook === 'Dry' ? 'Sticky upside risks' : 'Data-dependent',
        evidence: 'Oil and weather remain the fastest inflation transmission channels in the current evidence set.',
        marketImpact: 'Stickier inflation reduces the probability of aggressive policy easing and can keep financial conditions tighter for longer.',
      },
      interestRates: {
        policy: 'Cautious / data-dependent',
        expectedDirection: oil === 'Firming' ? 'Later easing bias' : 'Conditional easing room',
        evidence: us?.why || 'Global rate settings and domestic inflation will jointly determine India’s policy path.',
        marketImpact: 'A delayed easing cycle usually supports bank margins selectively while challenging real estate, autos and other duration-sensitive demand.',
      },
      currency: {
        trend: context.fx?.[0]?.direction || 'Stable',
        evidence: context.fx?.[0]?.implication,
        marketImpact: 'Dollar strength raises imported inflation and EM financial-condition risk; dollar softness can ease both.',
      },
      commodities: {
        oil,
        gold,
        evidence: (context.commodities || []).slice(0, 4).map((item) => `${item.name}: ${item.direction}`).join('; ') || 'Limited commodity evidence',
        marketImpact: 'Commodity direction is being read through inflation, margins and sector leadership — not as a price board.',
      },
      bonds: {
        india10Y: 'Monitored',
        us10Y: context.fred.find((item) => /10y/i.test(item.label))?.direction || 'Monitored',
        evidence: 'Bond yields matter because they price growth, inflation and policy expectations simultaneously.',
        marketImpact: 'Higher yields tighten financial conditions; softer yields reopen duration and rate-sensitive demand.',
      },
      global: {
        evidence: (context.countries || []).map((c) => `${c.name}: ${c.condition}`).join('; '),
        marketImpact: 'Global growth and policy divergence continue to determine capital flows, commodity demand and India’s external constraint.',
      },
    },
    transmissionMaps: buildTransmissionMaps(context),
    sectorImpact: buildSectorImpact(context),
    debate: {
      bullishFactors: [
        'India’s growth backdrop remains comparatively resilient versus many developed markets.',
        oil === 'Easing' ? 'Softer oil improves the inflation and policy outlook.' : 'Selective domestic demand and formal-sector strength can still offset parts of the external shock.',
        'If monsoon outcomes stay supportive, food-inflation risk can ease at the margin.',
      ],
      bearishFactors: [
        oil === 'Firming' ? 'Firm oil reopens inflation and current-account pressure.' : 'A renewed oil spike would quickly reopen inflation risk.',
        'US financial conditions can tighten EM risk appetite even when domestic growth is stable.',
        weather.rainfallOutlook === 'Dry' ? 'Weak rainfall raises food-price and rural-demand uncertainty.' : 'Weather remains a non-linear inflation risk.',
      ],
      neutralFactors: [
        'Several premium market feeds are not yet configured, so AGI avoids over-claiming precision on global index and realtime rate prints.',
        'Policy reaction functions remain data-dependent rather than pre-committed.',
      ],
      verdict: `AGI’s current verdict is ${String(outlook).toLowerCase()} because the bearish transmission channels (energy, imported inflation, policy caution) are material, but India’s growth resilience prevents a fully defensive macro conclusion.`,
    },
    keyRisks: [
      { label: 'Oil / geopolitics', level: oil === 'Firming' ? 'High' : 'Medium', why: 'Energy shocks transmit quickly into inflation, deficits and sector margins.', affected: ['Airlines', 'Autos', 'Chemicals'], watch: 'Middle East supply and OPEC communication' },
      { label: 'Inflation persistence', level: 'Medium', why: 'If inflation stays sticky, RBI policy room narrows and rate-sensitive assets stay under pressure.', affected: ['Real Estate', 'Consumer Durables'], watch: 'CPI and food-price prints' },
      { label: 'Global financial conditions', level: 'Medium', why: 'US yields and the dollar can tighten EM liquidity independently of India’s domestic cycle.', affected: ['Financials', 'Export-linked equities'], watch: 'Fed communication and US labour/inflation data' },
      { label: 'Monsoon / food prices', level: weather.rainfallOutlook === 'Dry' ? 'High' : 'Medium', why: 'Weather anomalies affect food inflation and rural demand with a lag.', affected: ['FMCG', 'Agri inputs', 'Power'], watch: 'Rainfall anomalies and reservoir conditions' },
    ],
    opportunities: [
      { label: 'Domestic quality compounders', why: 'If growth remains durable while policy stays orderly, balance-sheet strength and pricing power matter more than beta.' },
      { label: 'Energy transition & efficiency themes', why: 'Firm energy costs increase the strategic relevance of efficiency, domestic energy and import substitution.' },
    ],
    whatWouldChange: [
      'A sustained move in oil that clearly changes the inflation path',
      'An RBI communication shift on the growth–inflation trade-off',
      'US policy or yields that reprice global financial conditions',
      'Monsoon outcomes that alter food-inflation expectations',
      'A material turn in domestic growth or credit impulse',
    ],
    institutionalQuestions: [
      'Can inflation remain above comfort levels even if growth stays resilient?',
      'Will RBI delay easing if oil and food prices stay firm?',
      'Is oil becoming a structural inflation risk or a temporary geopolitical shock?',
      'Can domestic demand offset weaker exports if global growth softens?',
      'Will US policy keep EM financial conditions tighter for longer?',
    ],
    historicalComparison: {
      title: 'Partial analogue: post-shock inflation vigilance',
      similarities: 'Energy sensitivity, imported inflation risk and cautious policy sequencing remain familiar.',
      differences: 'India’s current growth and formalisation backdrop is stronger than in several prior inflation scare episodes, so AGI does not force a full historical replay.',
    },
    reliability: {
      level: sourcesCount >= 4 ? 'High' : sourcesCount >= 2 ? 'Moderate' : 'Limited',
      explanation: `Reliability is ${sourcesCount >= 4 ? 'high' : sourcesCount >= 2 ? 'moderate' : 'limited'} because today’s note draws on ${sourcesCount} AGI-cached source families (reference APIs, not live pipes).`,
      inputsUsed: context.sourcesUsed || [],
      missingInputs: context.missingSources || [],
    },
  };
}

function buildCalendar() {
  const base = new Date();
  const addDays = (n) => {
    const d = new Date(base);
    d.setDate(d.getDate() + n);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
  };
  return [
    { event: 'India CPI', date: addDays(3), importance: 'High', sectors: ['Banks', 'Autos', 'FMCG'], note: 'Inflation prints shape RBI room and rate-sensitive demand.' },
    { event: 'RBI policy decision', date: addDays(12), importance: 'High', sectors: ['Banks', 'Real Estate', 'NBFCs'], note: 'Policy language matters as much as the action for financial conditions.' },
    { event: 'US Core PCE / Fed communication', date: addDays(5), importance: 'High', sectors: ['IT', 'Financials', 'Metals'], note: 'Global yields and the dollar transmit into Indian risk appetite.' },
    { event: 'India GDP / PMI', date: addDays(8), importance: 'Medium', sectors: ['Industrials', 'Banks', 'Consumption'], note: 'Growth confirmation supports domestic cyclicals if inflation stays contained.' },
    { event: 'US Employment', date: addDays(10), importance: 'High', sectors: ['IT', 'Banks', 'Metals'], note: 'US labour data can reprice global financial conditions quickly.' },
    { event: 'OPEC / oil supply updates', date: addDays(14), importance: 'High', sectors: ['Energy', 'Airlines', 'Chemicals'], note: 'Oil remains the fastest macro shock channel for India.' },
  ];
}

function formatPct(value, digits = 1) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return `${n.toFixed(digits)}%`;
}

function formatNum(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n.toFixed(digits);
}

function sparkFromHistory(history = [], direction = 'Stable') {
  if (Array.isArray(history) && history.length >= 2) return history.map(Number).filter(Number.isFinite);
  if (/firm|up|high/i.test(direction)) return [3, 3.2, 3.1, 3.4, 3.6, 3.5, 3.8, 4];
  if (/eas|down|low|improv/i.test(direction)) return [4, 3.9, 3.7, 3.6, 3.4, 3.3, 3.2, 3.1];
  return [3.4, 3.45, 3.4, 3.5, 3.48, 3.52, 3.5, 3.51];
}

function buildIndicators(context) {
  const indiaGdp = (context.worldBank || []).find((item) => /gdp growth/i.test(item.label));
  const indiaCpi = (context.worldBank || []).find((item) => /cpi inflation/i.test(item.label));
  const fed = (context.fred || []).find((item) => /federal funds/i.test(item.label));
  const us10y = (context.fred || []).find((item) => /10y/i.test(item.label));
  const oil = (context.commodities || []).find((item) => /oil|crude|brent|wti/i.test(item.name));
  const fx = context.fx?.[0];

  return [
    {
      id: 'india-gdp',
      label: 'India GDP Growth',
      value: indiaGdp ? formatPct(indiaGdp.value) : '—',
      status: indiaGdp?.direction === 'Firming' ? 'Improving' : indiaGdp?.direction === 'Easing' ? 'Softening' : 'Stable',
      tone: indiaGdp?.direction === 'Firming' ? 'positive' : indiaGdp?.direction === 'Easing' ? 'negative' : 'neutral',
      sparkline: sparkFromHistory([], indiaGdp?.direction),
      source: indiaGdp?.source || 'World Bank',
      asOf: indiaGdp?.year || null,
    },
    {
      id: 'india-cpi',
      label: 'India Inflation (CPI)',
      value: indiaCpi ? formatPct(indiaCpi.value) : '—',
      status: indiaCpi?.direction === 'Easing' ? 'Moderating' : indiaCpi?.direction === 'Firming' ? 'Elevated' : 'Stable',
      tone: indiaCpi?.direction === 'Easing' ? 'positive' : indiaCpi?.direction === 'Firming' ? 'negative' : 'neutral',
      sparkline: sparkFromHistory([], indiaCpi?.direction),
      source: indiaCpi?.source || 'World Bank',
      asOf: indiaCpi?.year || null,
    },
    {
      id: 'us-policy',
      label: 'US Policy Rate',
      value: fed ? formatPct(fed.value, 2) : '—',
      status: fed?.direction === 'Easing' ? 'Easing' : fed?.direction === 'Firming' ? 'Restrictive' : 'Neutral',
      tone: fed?.direction === 'Easing' ? 'positive' : fed?.direction === 'Firming' ? 'negative' : 'neutral',
      sparkline: sparkFromHistory(fed?.history, fed?.direction),
      source: fed?.source || 'FRED',
      asOf: fed?.date || null,
    },
    {
      id: 'us-10y',
      label: 'US 10Y Yield',
      value: us10y ? formatPct(us10y.value, 2) : '—',
      status: Number(us10y?.value) >= 4.3 ? 'High' : Number(us10y?.value) <= 3.5 ? 'Low' : 'Moderate',
      tone: Number(us10y?.value) >= 4.3 ? 'negative' : 'neutral',
      sparkline: sparkFromHistory(us10y?.history, us10y?.direction),
      source: us10y?.source || 'FRED',
      asOf: us10y?.date || null,
    },
    {
      id: 'crude',
      label: 'Crude Oil',
      value: oil?.direction || 'Monitored',
      status: oil?.direction === 'Firming' ? 'High' : oil?.direction === 'Easing' ? 'Easing' : 'Stable',
      tone: oil?.direction === 'Firming' ? 'negative' : oil?.direction === 'Easing' ? 'positive' : 'neutral',
      sparkline: sparkFromHistory([], oil?.direction),
      source: oil?.source || 'AGI cache',
      asOf: oil?.asOf || null,
      note: 'Direction from AGI commodity repository (price prints withheld when not cached).',
    },
    {
      id: 'usdinr',
      label: 'USD/INR',
      value: fx?.value != null ? formatNum(fx.value, 2) : '—',
      status: fx?.direction || 'Stable',
      tone: fx?.direction === 'Firming' ? 'negative' : fx?.direction === 'Easing' ? 'positive' : 'neutral',
      sparkline: sparkFromHistory([], fx?.direction),
      source: 'Frankfurter/ECB',
      asOf: fx?.asOf || null,
    },
  ];
}

function buildWhatChanged(context, brief) {
  const oil = oilDirection(context.commodities);
  const us10y = (context.fred || []).find((item) => /10y/i.test(item.label));
  const weather = context.weather || {};
  return [
    {
      id: 'oil',
      title: 'Crude Oil',
      move: oil === 'Firming' ? 'Rising' : oil === 'Easing' ? 'Easing' : 'Unchanged',
      why: oil === 'Firming' ? 'Supply and geopolitics keep energy as an inflation risk.' : oil === 'Easing' ? 'Softer energy impulse reduces near-term inflation pressure.' : 'No decisive energy impulse in the latest AGI cache.',
      impact: oil === 'Firming' ? 'Inflation risk' : oil === 'Easing' ? 'Policy room improves' : 'Neutral',
      tone: oil === 'Firming' ? 'negative' : oil === 'Easing' ? 'positive' : 'neutral',
    },
    {
      id: 'us10y',
      title: 'US 10Y Yield',
      move: us10y ? `${formatPct(us10y.value, 2)} · ${us10y.direction}` : 'Monitored',
      why: us10y?.direction === 'Firming' ? 'Stronger US data / policy expectations lift global yields.' : us10y?.direction === 'Easing' ? 'Yield relief can ease EM financial conditions.' : 'Yields remain a key EM liquidity transmission channel.',
      impact: 'EM liquidity',
      tone: us10y?.direction === 'Firming' ? 'negative' : us10y?.direction === 'Easing' ? 'positive' : 'neutral',
    },
    {
      id: 'rbi',
      title: 'RBI Inflation Outlook',
      move: 'Unchanged',
      why: 'Policy remains data-dependent around the growth–inflation trade-off.',
      impact: 'Neutral for now',
      tone: 'neutral',
    },
    {
      id: 'monsoon',
      title: 'Monsoon Update',
      move: weather.rainfallOutlook || 'Mixed',
      why: weather.implication || 'Weather remains a food-inflation and rural-demand variable.',
      impact: weather.rainfallOutlook === 'Dry' ? 'Food inflation risk' : weather.rainfallOutlook === 'Wet' ? 'Food inflation relief' : 'Watch food prices',
      tone: weather.rainfallOutlook === 'Dry' ? 'negative' : weather.rainfallOutlook === 'Wet' ? 'positive' : 'neutral',
    },
    {
      id: 'regime',
      title: 'AGI Macro Regime',
      move: brief.outlook,
      why: brief.debate?.verdict || brief.confidenceRationale,
      impact: 'Portfolio stance',
      tone: /cautious|bear/i.test(brief.outlook) ? 'negative' : /construct/i.test(brief.outlook) ? 'positive' : 'neutral',
    },
  ];
}

function buildTransmissionGraph(context) {
  const oil = oilDirection(context.commodities);
  const fx = context.fx?.[0]?.direction || 'Stable';
  const weather = context.weather?.rainfallOutlook || 'Mixed';
  return {
    title: 'Macro Transmission Map',
    subtitle: 'How macro drivers transmit into inflation, policy and sector outcomes',
    drivers: [
      { id: 'oil', label: oil === 'Firming' ? 'Rising Oil Prices' : oil === 'Easing' ? 'Softer Oil Prices' : 'Stable Oil Prices', active: true },
      { id: 'dollar', label: fx === 'Firming' ? 'Stronger US Dollar' : 'Dollar Conditions Mixed', active: true },
      { id: 'rates', label: 'Global Rates Elevated', active: true },
      { id: 'china', label: 'Weak China Demand', active: true },
      { id: 'monsoon', label: weather === 'Dry' ? 'Weak Monsoon Risk' : weather === 'Wet' ? 'Supportive Monsoon' : 'Variable Monsoon', active: true },
    ],
    transmissions: [
      { id: 'costs', label: 'Higher Input Costs', from: ['oil'] },
      { id: 'imported', label: 'Imported Inflation', from: ['dollar', 'oil'] },
      { id: 'policy', label: 'Policy Caution', from: ['rates', 'imported'] },
      { id: 'growth', label: 'Growth Moderation Risk', from: ['china', 'policy'] },
      { id: 'food', label: 'Food-Price Channel', from: ['monsoon'] },
    ],
    outcomes: [
      { id: 'inflation', label: oil === 'Firming' || weather === 'Dry' ? 'Inflation Risk ↑' : 'Inflation Data-Dependent', tone: oil === 'Firming' || weather === 'Dry' ? 'negative' : 'neutral' },
      { id: 'rbi', label: oil === 'Firming' ? 'RBI Easing Delayed' : 'RBI Remains Conditional', tone: oil === 'Firming' ? 'negative' : 'neutral' },
      { id: 'credit', label: 'Credit Growth Impact', tone: 'neutral' },
      { id: 'sectors', label: 'Sector Divergence', tone: 'neutral' },
      { id: 'food-out', label: weather === 'Dry' ? 'Food Inflation Risk' : 'Rural Demand Watch', tone: weather === 'Dry' ? 'negative' : 'neutral' },
    ],
    maps: buildTransmissionMaps(context),
  };
}

function buildRegime(brief, context) {
  const oil = oilDirection(context.commodities);
  return {
    macroRegime: /cautious/i.test(brief.outlook) ? 'Cautious' : 'Constructive',
    confidence: brief.confidence,
    cycle: (context.countries || []).find((c) => c.name === 'India')?.condition === 'Improving' ? 'Expansion' : 'Late cycle watch',
    inflation: oil === 'Firming' || context.weather?.rainfallOutlook === 'Dry' ? 'Sticky risks' : 'Moderating',
    policy: brief.evidence?.interestRates?.policy || 'Neutral / data-dependent',
    volatility: 'Moderate',
    liquidity: (context.fred || []).find((i) => /10y/i.test(i.label))?.direction === 'Firming' ? 'Tightening' : 'Balanced',
    riskEnvironment: /cautious/i.test(brief.outlook) ? 'Selective risk-off' : 'Selective risk-on',
    macroTrend: (context.countries || []).find((c) => c.name === 'India')?.condition || 'Stable',
  };
}

function buildConfidenceBreakdown(brief, context) {
  const supports = [];
  const challenges = [];
  const indiaGdp = (context.worldBank || []).find((item) => /gdp growth/i.test(item.label));
  const indiaCpi = (context.worldBank || []).find((item) => /cpi inflation/i.test(item.label));
  if (indiaGdp?.direction === 'Firming') supports.push('Growth');
  else challenges.push('Growth');
  if (indiaCpi?.direction === 'Easing') supports.push('Inflation');
  else challenges.push('Inflation');
  supports.push('Policy visibility');
  if (oilDirection(context.commodities) === 'Firming') challenges.push('Oil');
  else supports.push('Energy');
  challenges.push('Global yields');
  challenges.push('China demand');
  return {
    score: brief.confidence,
    rationale: brief.confidenceRationale,
    supports,
    challenges,
    summary: 'Several indicators disagree. Therefore confidence is moderate rather than high.',
  };
}

function buildWorkspace(context, brief) {
  return {
    regime: buildRegime(brief, context),
    indicators: buildIndicators(context),
    whatChanged: buildWhatChanged(context, brief),
    transmission: buildTransmissionGraph(context),
    confidenceBreakdown: buildConfidenceBreakdown(brief, context),
    askPrompts: [
      'How will higher US rates affect Indian banks?',
      'Will RBI cut rates if oil stays firm?',
      'What does a stronger dollar mean for India inflation?',
      'Which sectors benefit if monsoon stays supportive?',
    ],
  };
}

function buildBriefing(context) {
  const brief = buildChiefEconomistBrief(context);
  const now = new Date();
  return {
    updatedAt: now.toISOString(),
    refreshesAt: new Date(now.getTime() + CACHE_MS).toISOString(),
    aiGenerated: false,
    stale: Boolean(context.stale),
    repository: {
      policy: 'Official API → Backend → Cache → Database → AGI AI Analysis → Frontend',
      cachePolicy: context.cachePolicy || MACRO_REFRESH_MS,
      datasetStatus: context.datasetStatus || [],
      lastSuccessfulFetches: context.lastSuccessfulFetches || [],
      note: 'Free APIs are reference sources. AGI serves from its own repository; refresh only when underlying data is likely to change.',
    },
    chiefEconomistBrief: brief,
    workspace: buildWorkspace(context, brief),
    snapshot: {
      countries: context.countries,
      themes: buildThemes(context),
      commodities: context.commodities,
      fx: context.fx,
      rates: context.fred,
      worldBank: context.worldBank,
      weather: context.weather,
      calendar: buildCalendar(),
      policyTracker: buildPolicyTracker(),
      risks: brief.keyRisks,
      headlines: (context.headlines || []).slice(0, 6),
    },
    sourcesUsed: context.sourcesUsed,
    missingSources: context.missingSources,
    disclaimer: 'AGI Macro Intelligence is an institutional research view for information only. It is not investment advice, a forecast guarantee, or a recommendation to buy or sell any security.',
  };
}

function buildPolicyTracker() {
  return [
    { body: 'RBI', whatChanged: 'Policy remains data-dependent around the growth–inflation trade-off.', whyItMatters: 'RBI sets the domestic financial-conditions anchor for credit, duration and currency stability.', whoAffected: 'Banks, NBFCs, real estate, autos' },
    { body: 'Finance Ministry / Budget', whatChanged: 'Fiscal impulse and capex orientation remain structural drivers of domestic demand.', whyItMatters: 'Fiscal quality influences growth durability and bond supply.', whoAffected: 'Infrastructure, capital goods, industrials' },
    { body: 'Trade / energy policy', whatChanged: 'Import dependence on energy keeps external vulnerability live.', whyItMatters: 'Trade and energy choices affect inflation and the current account.', whoAffected: 'Energy, chemicals, exporters' },
    { body: 'SEBI / market structure', whatChanged: 'Market-structure and disclosure standards continue shaping institutional participation quality.', whyItMatters: 'Trust and liquidity conditions affect how macro shocks are priced.', whoAffected: 'Financial markets, intermediaries' },
  ];
}

function buildThemes(context) {
  return [
    { id: 'inflation', title: 'Inflation', summary: 'Oil, food and currency remain the dominant price channels.', condition: oilDirection(context.commodities) === 'Firming' ? 'Watch' : 'Stable' },
    { id: 'rbi-policy', title: 'RBI Policy', summary: 'Policy room depends on whether inflation cools without damaging growth.', condition: 'Watch' },
    { id: 'oil', title: 'Oil', summary: 'Energy is the fastest transmission into inflation, deficits and sector margins.', condition: oilDirection(context.commodities) },
    { id: 'global-growth', title: 'Global Growth', summary: 'US, China and Europe jointly set external demand and commodity pricing.', condition: 'Stable' },
    { id: 'monsoon', title: 'Monsoon / Rural Demand', summary: context.weather?.implication || 'Weather remains a food-inflation and rural-income variable.', condition: context.weather?.rainfallOutlook || 'Mixed' },
    { id: 'dollar', title: 'Dollar & EM Liquidity', summary: context.fx?.[0]?.implication || 'Dollar direction alters imported inflation and financial conditions.', condition: context.fx?.[0]?.direction || 'Stable' },
  ];
}

async function enrichWithLlm(briefing) {
  const brief = briefing.chiefEconomistBrief;
  const source = {
    outlook: brief.outlook,
    evidence: brief.evidence,
    risks: brief.keyRisks,
    debate: brief.debate,
    countries: briefing.snapshot.countries,
    commodities: briefing.snapshot.commodities,
    weather: briefing.snapshot.weather,
    fx: briefing.snapshot.fx,
  };
  try {
    const { completeJson } = await import('./llmClient.js');
    const generated = await completeJson({
      system:
        'You are the Chief Economist of Agarwal Global Investments. Write ONE institutional macro strategy brief. No raw prices or percentage quotes. Every important claim must answer “because what?”. Ban vague phrases like “markets remained cautious” or “conditions remained mixed”. Never give buy/sell recommendations. Return JSON with: executiveThesis (200-300 words), outlook, confidenceRationale, whyReached (array of {title, explanation}), debateVerdict, institutionalQuestions (string array).',
      user: source,
      temperature: 0.25,
    });
    if (!generated) return briefing;
    return {
      ...briefing,
      aiGenerated: true,
      chiefEconomistBrief: {
        ...brief,
        executiveThesis: typeof generated.executiveThesis === 'string' ? generated.executiveThesis : brief.executiveThesis,
        outlook: typeof generated.outlook === 'string' ? generated.outlook : brief.outlook,
        confidenceRationale: typeof generated.confidenceRationale === 'string' ? generated.confidenceRationale : brief.confidenceRationale,
        whyReached: Array.isArray(generated.whyReached) && generated.whyReached.length
          ? generated.whyReached.slice(0, 5).map((item) => ({
            title: String(item.title || 'Driver'),
            explanation: String(item.explanation || ''),
          }))
          : brief.whyReached,
        debate: {
          ...brief.debate,
          verdict: typeof generated.debateVerdict === 'string' ? generated.debateVerdict : brief.debate.verdict,
        },
        institutionalQuestions: Array.isArray(generated.institutionalQuestions) && generated.institutionalQuestions.length
          ? generated.institutionalQuestions.map(String).slice(0, 6)
          : brief.institutionalQuestions,
      },
    };
  } catch (error) {
    console.warn('[macro-briefing] AI narrative fallback:', error.message);
    return briefing;
  }
}

export async function getMacroBriefing({ force = false } = {}) {
  if (!force && memory?.workspace && isFresh({ expiresAt: memory.refreshesAt })) {
    return { ...memory, fromCache: true };
  }

  if (inflight) return inflight;

  inflight = (async () => {
    const persisted = force ? null : await getBriefingCache();
    // Rebuild when workspace schema is missing (UI redesign) or cache expired.
    if (persisted?.payload && isFresh(persisted) && persisted.payload.workspace) {
      memory = {
        ...persisted.payload,
        fromCache: true,
        stale: Boolean(persisted.payload.stale),
        repository: {
          ...(persisted.payload.repository || {}),
          servedFrom: 'agi-repository',
          cacheFetchedAt: persisted.fetchedAt,
        },
      };
      return memory;
    }

    // Stale-while-revalidate: serve last good briefing immediately if rebuild fails later.
    const staleFallback = memory?.chiefEconomistBrief
      ? memory
      : persisted?.payload
        ? {
          ...persisted.payload,
          stale: true,
          fromCache: true,
          repository: {
            ...(persisted.payload.repository || {}),
            servedFrom: 'stale-fallback',
            cacheFetchedAt: persisted.fetchedAt,
          },
        }
        : null;

    try {
      const context = await getMacroContext({ force });
      const briefing = await enrichWithLlm(buildBriefing(context));
      const saved = await saveBriefingCache(briefing, {
        ttlMs: CACHE_MS,
        aiGenerated: Boolean(briefing.aiGenerated),
      });
      memory = {
        ...briefing,
        fromCache: false,
        refreshesAt: saved.expiresAt,
        repository: {
          ...briefing.repository,
          servedFrom: 'fresh-build',
          cacheFetchedAt: saved.fetchedAt,
        },
      };
      return memory;
    } catch (error) {
      if (staleFallback) {
        console.warn('[macro-briefing] rebuild failed; serving stale repository cache:', error.message);
        memory = {
          ...staleFallback,
          stale: true,
          fromCache: true,
          repository: {
            ...(staleFallback.repository || {}),
            servedFrom: 'stale-fallback',
            upstreamError: error.message,
          },
        };
        return memory;
      }
      throw error;
    }
  })().finally(() => {
    inflight = null;
  });

  return inflight;
}

/**
 * Answer a desk question using the current macro briefing + optional OpenAI.
 * Always returns a structured answer (deterministic fallback if OpenAI is unset/fails).
 */
export async function askMacroEconomist(query) {
  const q = String(query || '').trim();
  if (!q) {
    const err = new Error('Question is required');
    err.status = 400;
    throw err;
  }

  const briefing = await getMacroBriefing();
  const brief = briefing?.chiefEconomistBrief || {};
  const workspace = briefing?.workspace || {};
  const snapshot = briefing?.snapshot || {};

  const deterministic = {
    query: q,
    response: brief.executiveThesis || 'Macro briefing is still warming up. Refresh in a moment.',
    evidence: Array.isArray(brief.whyReached) ? brief.whyReached.slice(0, 4) : [],
    implications: brief.sectorImpact || null,
    related: Array.isArray(brief.institutionalQuestions) ? brief.institutionalQuestions.slice(0, 4) : [],
    outlook: brief.outlook || 'Data-dependent',
    source: 'deterministic-desk',
    updatedAt: briefing?.updatedAt || null,
  };

  const lower = q.toLowerCase();
  if (/bank|rate|fed|yield|rbi|monetary/i.test(lower)) {
    deterministic.evidence = [
      { title: 'Rates transmission', explanation: brief.evidence?.interestRates?.evidence || brief.debate?.verdict },
      { title: 'Market impact', explanation: brief.evidence?.interestRates?.marketImpact },
    ].filter((item) => item.explanation);
    deterministic.response = [
      'Higher US yields tighten global financial conditions for India through the dollar, foreign flows and the cost of capital.',
      'The immediate transmission is usually pressure on INR and imported inflation; that can reduce RBI’s room to ease even when domestic growth remains firm.',
      'Banks and NBFCs should be judged through funding costs, deposit growth and credit quality; rate-sensitive sectors such as real estate and autos are more exposed if domestic policy stays cautious.',
      brief.evidence?.interestRates?.marketImpact || 'AGI therefore treats the impact as selective rather than a blanket risk-off signal.',
    ].filter(Boolean).join(' ');
  } else if (/oil|inflat|cpi|commodity/i.test(lower)) {
    deterministic.evidence = [
      { title: 'Inflation channel', explanation: brief.evidence?.inflation?.evidence },
      { title: 'Commodities', explanation: brief.evidence?.commodities?.evidence },
    ].filter((item) => item.explanation);
    deterministic.response = [
      'For India, oil, food and the rupee are the fastest channels from global macro conditions into inflation and policy expectations.',
      'Higher oil can pressure the current account, fuel costs and margins for airlines, chemicals and transport; easing oil improves the inflation backdrop and supports rate-sensitive demand.',
      'The key question is whether the move is persistent enough to change RBI’s policy room rather than a short-lived commodity fluctuation.',
      snapshot.weather?.implication,
    ].filter(Boolean).join(' ');
  } else if (/monsoon|food|rural|weather/i.test(lower)) {
    deterministic.evidence = [
      { title: 'Weather channel', explanation: snapshot.weather?.implication },
    ].filter((item) => item.explanation);
    deterministic.response = [
      'Monsoon conditions affect India primarily through food inflation, rural incomes and agricultural output.',
      snapshot.weather?.implication,
      'A supportive season can improve rural-demand visibility and give policymakers more confidence on food inflation; local anomalies can still create category-specific pressure.',
    ].filter(Boolean).join(' ');
  }

  const apiKey = (process.env.OPENAI_API_KEY || '').trim();
  if (!apiKey) return deterministic;

  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(25_000),
      body: JSON.stringify({
        model: process.env.OPENAI_MARKET_BRIEFING_MODEL || 'gpt-4.1-mini',
        response_format: { type: 'json_object' },
        messages: [
          {
            role: 'system',
            content:
              'You are the Chief Economist of Agarwal Global Investments. Answer one institutional macro question using only the supplied briefing evidence. No buy/sell calls. No fabricated data. Return JSON: { response (120-220 words), outlook, evidence:[{title, explanation}], related:[string] }.',
          },
          {
            role: 'user',
            content: JSON.stringify({
              question: q,
              brief: {
                outlook: brief.outlook,
                thesis: brief.executiveThesis,
                evidence: brief.evidence,
                whyReached: brief.whyReached,
                risks: brief.keyRisks,
                questions: brief.institutionalQuestions,
                regime: workspace.regime,
                fx: snapshot.fx,
                commodities: snapshot.commodities,
                weather: snapshot.weather,
              },
            }),
          },
        ],
        temperature: 0.2,
      }),
    });
    if (!response.ok) throw new Error(`OpenAI macro-ask failed (${response.status})`);
    const generated = JSON.parse((await response.json())?.choices?.[0]?.message?.content || '{}');
    return {
      query: q,
      response: typeof generated.response === 'string' && generated.response.trim()
        ? generated.response.trim()
        : deterministic.response,
      outlook: typeof generated.outlook === 'string' ? generated.outlook : deterministic.outlook,
      evidence: Array.isArray(generated.evidence) && generated.evidence.length
        ? generated.evidence.slice(0, 5).map((item) => ({
          title: String(item.title || 'Evidence'),
          explanation: String(item.explanation || ''),
        }))
        : deterministic.evidence,
      implications: deterministic.implications,
      related: Array.isArray(generated.related) && generated.related.length
        ? generated.related.map(String).slice(0, 4)
        : deterministic.related,
      source: 'openai',
      updatedAt: briefing?.updatedAt || null,
    };
  } catch (error) {
    console.warn('[macro-ask] OpenAI failed; using deterministic desk:', error.message);
    return { ...deterministic, source: 'deterministic-fallback', upstreamError: error.message };
  }
}

export function startMacroBriefingScheduler() {
  if (scheduler) return;
  const refresh = () => {
    // Only rebuild when cache is expired — never hammer free APIs.
    getMacroBriefing().catch((error) => console.warn('[macro-briefing] scheduled refresh failed:', error.message));
  };
  refresh();
  scheduler = setInterval(refresh, CACHE_MS);
  scheduler.unref?.();
}
