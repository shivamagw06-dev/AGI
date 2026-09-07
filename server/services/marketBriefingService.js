import { getAgiIntelligence } from './intelligenceService.js';
import { getMarketContext } from './marketContextService.js';
import { getMarketSessionFacts } from './marketSessionFactsService.js';

const CACHE_MS = 10 * 60 * 1000;
const MAX_ARTICLES = 16;
let cache = null;
let expiresAt = 0;
let inflight = null;
let scheduler = null;

const CATEGORY_RULES = [
  ['Policy', /\brbi\b|policy|regulation|sebi|budget|government|gst/i],
  ['Results', /results?|earnings|profit|revenue|margin|quarter|q[1-4]/i],
  ['Banking', /bank|nbfc|lender|deposit|credit/i],
  ['Commodities', /crude|oil|gold|silver|commodity|metal/i],
  ['Companies', /reliance|infosys|tata|adani|hdfc|icici|larsen|bharti/i],
  ['Global', /global|us |fed|china|europe|wall street|tariff/i],
  ['IPO', /\bipo\b|listing|public issue/i],
];

function classify(title = '') {
  const category = CATEGORY_RULES.find(([, rule]) => rule.test(title))?.[0] || 'Markets';
  const importance = /rbi|policy|budget|results?|earnings|profit|crude|oil|fed|tariff|merger|acquisition/i.test(title)
    ? 'High impact'
    : /bank|revenue|margin|gold|commodity|announcement/i.test(title)
      ? 'Medium impact'
      : 'Low impact';
  return { category, importance };
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function moodFrom(outlook = {}) {
  const mood = outlook.outlook || 'Neutral';
  return {
    label: mood,
    confidence: outlook.confidence || 50,
    rationale: `${outlook.marketBreadth || 'Neutral'} participation, ${outlook.momentum || 'moderate'} momentum and ${String(outlook.risk || 'medium').toLowerCase()} model risk define the current AGI market read.`,
  };
}

function buildArticles(headlines) {
  return headlines.slice(0, MAX_ARTICLES).map((headline) => {
    const { category, importance } = classify(headline.title);
    return {
      ...headline,
      category,
      importance,
      summary: category === 'Results'
        ? 'Reported earnings context may influence company and sector expectations; verify the original filing or release.'
        : category === 'Policy'
          ? 'Policy developments can affect market expectations through rates, liquidity, regulation or fiscal transmission.'
          : 'This item is included for source discovery and should be read with its original publisher context.',
    };
  });
}

function buildThemes(articles, intelligence) {
  const fromNews = articles.map((article) => article.category);
  const fromModel = [intelligence.topSector, intelligence.weakestSector].filter(Boolean);
  return unique([...fromNews, ...fromModel]).filter((theme) => !['Markets', 'Companies'].includes(theme)).slice(0, 7);
}

function buildSectorImpact(intelligence, newsCategories = []) {
  const sectors = intelligence.sectors || [];
  return sectors.slice(0, 6).map((sector) => ({
    name: sector.name,
    direction: /↓|weak/i.test(`${sector.direction} ${sector.strength}`) ? 'Negative' : /↑|strong|leading/i.test(`${sector.direction} ${sector.strength}`) ? 'Positive' : 'Neutral',
    explanation: `${sector.strength || 'Mixed'} AGI trend and participation conditions.`,
    confidence: /strong|leading/i.test(`${sector.direction} ${sector.strength}`) ? 82 : /weak/i.test(`${sector.direction} ${sector.strength}`) ? 74 : 62,
    timeHorizon: 'Near term',
    supportingEvidence: [
      `Sector model condition: ${sector.strength || 'Mixed'}.`,
      `Market breadth: ${intelligence.outlook?.marketBreadth || 'Neutral'}.`,
      ...(newsCategories.length ? [`Relevant news context: ${newsCategories.slice(0, 2).join(' and ')}.`] : []),
    ],
    contradictingEvidence: [
      `The overall model risk level remains ${String(intelligence.outlook?.risk || 'medium').toLowerCase()}.`,
      'Company-specific fundamental evidence is not included in this sector-level view.',
    ],
    risks: ['A deterioration in sector participation or broader market breadth would weaken this view.'],
    evidenceUsed: ['Technical', 'Sector Rotation', 'Market Breadth', ...(newsCategories.length ? ['News Context'] : [])],
  }));
}

function buildCompanyImpact(intelligence) {
  return (intelligence.stocksInFocus || []).slice(0, 6).map((stock) => ({
    symbol: stock.symbol,
    name: stock.name || stock.symbol,
    direction: /bearish|weak/i.test(`${stock.trend} ${stock.category}`) ? 'Negative' : /bullish|strong/i.test(`${stock.trend} ${stock.category}`) ? 'Positive' : 'Neutral',
    explanation: `${stock.trend || 'Neutral'} trend with ${String(stock.momentum || 'moderate').toLowerCase()} momentum in the AGI model.`,
    confidence: Math.max(45, Math.min(95, Number(stock.agiScore) || 60)),
    timeHorizon: 'Near term',
    supportingEvidence: [
      `Technical trend: ${stock.trend || 'Neutral'}.`,
      `Momentum condition: ${stock.momentum || 'Moderate'}.`,
      `AGI research score: ${stock.agiScore ?? 'not available'}.`,
    ],
    contradictingEvidence: ['Company-specific earnings, filings and corporate-action evidence is not included in this aggregate market view.'],
    risks: ['A reversal in relative momentum or a weakening of broader participation could alter the view.'],
    evidenceUsed: ['Technical', 'Market Breadth', 'Sector Rotation'],
  }));
}

function buildKeyDrivers(intelligence, commodities, newsCategories) {
  const outlook = intelligence.outlook || {};
  const strongestSector = outlook.topSector || intelligence.sectors?.[0]?.name;
  const weakestSector = outlook.weakestSector;
  const crude = commodities.find((item) => /crude|oil/i.test(item.name));
  return [
    {
      title: 'Market participation',
      conclusion: outlook.marketBreadth || 'Neutral',
      explanation: `Breadth is currently assessed as ${String(outlook.marketBreadth || 'neutral').toLowerCase()}, which informs how widely current market conditions are participating.`,
      importance: 'High',
      evidenceUsed: ['Market Breadth', 'Technical'],
    },
    {
      title: 'Sector leadership',
      conclusion: strongestSector || 'Mixed',
      explanation: strongestSector ? `${strongestSector} is the leading sector in the current AGI model.` : 'Sector leadership is still being established by the model.',
      importance: 'High',
      evidenceUsed: ['Sector Rotation', 'Technical'],
    },
    {
      title: 'Momentum and trend',
      conclusion: outlook.momentum || 'Moderate',
      explanation: `The market model records ${String(outlook.momentum || 'moderate').toLowerCase()} momentum alongside a ${String(outlook.outlook || 'neutral').toLowerCase()} overall outlook.`,
      importance: 'High',
      evidenceUsed: ['Technical', 'Market Breadth'],
    },
    {
      title: 'Macro and energy context',
      conclusion: crude?.trend || 'Limited data',
      explanation: crude ? `${crude.name} is ${String(crude.trend).toLowerCase()} in the latest commodity context.` : 'Commodity context is currently limited.',
      importance: 'Medium',
      evidenceUsed: ['Commodities'],
    },
    {
      title: 'Information flow',
      conclusion: newsCategories.length ? 'Active' : 'Limited',
      explanation: newsCategories.length ? `Current source categories include ${newsCategories.slice(0, 3).join(', ')}.` : 'No additional categorized information flow is available in this briefing.',
      importance: 'Medium',
      evidenceUsed: newsCategories.length ? ['News Context'] : ['Evidence gap'],
    },
    ...(weakestSector ? [{
      title: 'Relative weakness',
      conclusion: weakestSector,
      explanation: `${weakestSector} is the weakest sector in the current AGI model and is a counterweight to broader leadership.`,
      importance: 'Medium',
      evidenceUsed: ['Sector Rotation', 'Technical'],
    }] : []),
  ].slice(0, 6);
}

function buildReasoning(intelligence, mood, drivers, sectors, risks, events) {
  const positiveDrivers = drivers.filter((driver) => /positive|strong|leading|firming|active|moderate/i.test(`${driver.conclusion} ${driver.explanation}`)).slice(0, 3);
  const negativeDrivers = drivers.filter((driver) => /weak|easing|limited/i.test(`${driver.conclusion} ${driver.explanation}`)).slice(0, 2);
  const weakest = sectors.find((sector) => sector.direction === 'Negative');
  const strongest = sectors.find((sector) => sector.direction === 'Positive');
  const confidenceRationale = `Confidence is ${mood.confidence >= 75 ? 'high' : mood.confidence >= 55 ? 'moderate' : 'limited'} because ${String(intelligence.outlook?.marketBreadth || 'neutral').toLowerCase()} breadth and ${String(intelligence.outlook?.momentum || 'moderate').toLowerCase()} momentum ${mood.confidence >= 55 ? 'provide some alignment' : 'do not yet provide strong alignment'}, while model risk remains ${String(intelligence.outlook?.risk || 'medium').toLowerCase()}.`;
  return {
    marketView: {
      conclusion: mood.label,
      confidence: mood.confidence,
      why: drivers.slice(0, 4).map((driver) => driver.title),
      confidenceRationale,
      supportingEvidence: unique(drivers.flatMap((driver) => driver.evidenceUsed || [])),
      contradictingEvidence: [
        ...(weakest ? [`Relative weakness remains in ${weakest.name}.`] : []),
        ...risks.slice(0, 2).map((risk) => `${risk.label}: ${risk.detail}`),
      ],
      whatNext: events.slice(0, 3).map((event) => event.event),
    },
    sectorRotation: strongest && weakest ? {
      from: [weakest.name],
      to: [strongest.name],
      explanation: `The current model shows relative leadership in ${strongest.name} while ${weakest.name} is weaker. This is a descriptive relative-strength observation, not evidence of capital flows.`,
      confidence: Math.min(strongest.confidence, 80),
    } : {
      from: [],
      to: [],
      explanation: 'Evidence is insufficient to identify a verified sector rotation in the current model.',
      confidence: 40,
    },
    debate: {
      bullishFactors: positiveDrivers.map((driver) => driver.explanation),
      bearishFactors: unique([
        ...negativeDrivers.map((driver) => driver.explanation),
        ...(weakest ? [`${weakest.name} remains a relative area of weakness.`] : []),
        ...risks.filter((risk) => /high|medium/i.test(risk.level)).slice(0, 2).map((risk) => risk.detail),
      ]).slice(0, 4),
      neutralFactors: [
        'Company-specific earnings, filings and corporate actions are assessed on individual research pages rather than inferred at market level.',
        'Current conclusions remain conditional on the next breadth and sector-leadership update.',
      ],
      conclusion: `AGI’s current ${String(mood.label).toLowerCase()} view reflects the balance of available technical, breadth, sector and macro evidence. ${confidenceRationale}`,
    },
  };
}

function buildRisks(intelligence, commodities) {
  const crude = commodities.find((item) => /crude|oil/i.test(item.name));
  return [
    { label: 'Market volatility', level: intelligence.volatility || 'Medium', detail: 'Derived from the AGI market model.' },
    { label: 'Macro conditions', level: intelligence.risk || 'Medium', detail: 'Policy, growth and inflation sensitivity remain under review.' },
    { label: 'Energy inputs', level: crude?.trend === 'Firming' ? 'Medium' : 'Low', detail: crude ? `${crude.name} is currently ${crude.trend.toLowerCase()}.` : 'Commodity feed context is limited.' },
    { label: 'Global markets', level: 'Medium', detail: 'International developments can affect risk appetite and sector leadership.' },
  ];
}

function buildEvents(articles) {
  const categories = unique(articles.map((article) => article.category));
  return [
    ...(categories.includes('Results') ? [{ timing: 'Today', event: 'Quarterly results and company updates', detail: 'Monitor official company releases and post-result commentary.' }] : []),
    ...(categories.includes('Policy') ? [{ timing: 'This week', event: 'Policy and regulatory communication', detail: 'Watch for measures affecting liquidity, rates or sector regulation.' }] : []),
    { timing: 'Next session', event: 'Market participation and sector leadership', detail: 'Track whether current breadth and leadership persist through the next market window.' },
  ];
}

function istMinutesNow(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date);
  const hour = Number(parts.find((part) => part.type === 'hour')?.value || 0);
  const minute = Number(parts.find((part) => part.type === 'minute')?.value || 0);
  return hour * 60 + minute;
}

function activeSessionKey(date = new Date()) {
  const mins = istMinutesNow(date);
  if (mins < 12 * 60) return 'preMarket';
  if (mins < 15 * 60 + 30) return 'midDay';
  return 'postMarket';
}

function toSentiment(value) {
  const text = String(value || '').toLowerCase();
  if (/bull|up|positive|strong|firm|lead|gain/i.test(text)) return 'Bullish';
  if (/bear|down|negative|weak|eas|los/i.test(text)) return 'Bearish';
  return 'Neutral';
}

function directionalContext(intelligence, context, facts, mood, sectors) {
  const outlook = intelligence.outlook || {};
  const topSector = sectors.find((sector) => sector.direction === 'Positive')?.name || outlook.topSector;
  const weakSector = sectors.find((sector) => sector.direction === 'Negative')?.name || outlook.weakestSector;
  const crude = (context.commodities || []).find((item) => /crude|oil/i.test(item.name));
  const weakerBenchmarks = (facts.indices || [])
    .filter((index) => Number(index.percentChange) < 0)
    .map((index) => index.name);
  const strongerBenchmarks = (facts.indices || [])
    .filter((index) => Number(index.percentChange) > 0)
    .map((index) => index.name);
  const volatilityRising = (facts.indices || []).some((item) => /vix/i.test(item.name) && Number(item.percentChange) > 0);
  const strongerNames = (facts.gainers || []).slice(0, 4).map((item) => item.name || item.symbol);
  const weakerNames = (facts.losers || []).slice(0, 4).map((item) => item.name || item.symbol);
  return {
    outlook,
    topSector,
    weakSector,
    crude,
    weakerBenchmarks,
    strongerBenchmarks,
    volatilityRising,
    strongerNames,
    weakerNames,
    breadth: outlook.marketBreadth || 'Neutral',
    momentum: outlook.momentum || 'Moderate',
    risk: outlook.risk || 'Medium',
    moodLabel: mood.label || 'Neutral',
    confidence: mood.confidence || 50,
  };
}

function buildSessionNotes(intelligence, context, facts, mood, sectors) {
  const d = directionalContext(intelligence, context, facts, mood, sectors);
  const why = [
    d.weakerBenchmarks.length
      ? `Benchmark tone is softer because ${d.weakerBenchmarks.join(' and ')} are weaker on the session.`
      : null,
    d.strongerBenchmarks.length
      ? `Selective support remains because ${d.strongerBenchmarks.join(' and ')} are comparatively firmer.`
      : null,
    d.volatilityRising
      ? 'Uncertainty is elevated because volatility conditions are rising.'
      : 'Volatility is not the dominant stress signal in the current model.',
    `Participation is assessed as ${String(d.breadth).toLowerCase()}, which ${/positive|strong/i.test(d.breadth) ? 'limits how negative the market read can become' : 'keeps the market conclusion conditional'}.`,
    d.topSector
      ? `${d.topSector} is leading relative participation and remains the clearest area of leadership.`
      : 'Sector leadership is still mixed.',
    d.weakSector
      ? `${d.weakSector} remains a relative area of weakness and caps conviction.`
      : null,
    d.crude
      ? `${d.crude.name} conditions are ${String(d.crude.trend).toLowerCase()}, which matters for energy-sensitive sentiment.`
      : null,
  ].filter(Boolean).slice(0, 5);

  const watch = [
    'Whether breadth continues to confirm or diverge from benchmark direction.',
    d.topSector ? `Whether ${d.topSector} leadership broadens into adjacent sectors.` : 'Which sector establishes clearer leadership next.',
    d.volatilityRising ? 'Whether the rise in volatility proves temporary or structural.' : 'Whether volatility stays contained into the next window.',
    'Whether upcoming disclosures reinforce or invalidate today’s conditional view.',
  ];

  const sharedLead = `AGI classifies the market as ${String(d.moodLabel).toLowerCase()} because breadth, momentum, volatility and sector leadership are not fully aligned.`;

  const preMarket = {
    id: 'preMarket',
    label: 'Pre-Market',
    title: 'Pre-Market Brief',
    subtitle: 'What matters before the open',
    outlook: d.moodLabel,
    confidence: d.confidence,
    lead: sharedLead,
    body: [
      `Into the open, AGI’s working stance is ${String(d.moodLabel).toLowerCase()} because model breadth is ${String(d.breadth).toLowerCase()} while momentum is ${String(d.momentum).toLowerCase()} and model risk remains ${String(d.risk).toLowerCase()}.`,
      d.topSector
        ? `Investors should watch whether ${d.topSector} can extend relative leadership early, because that would support a more constructive opening tone.`
        : 'Sector leadership is still unresolved, so the opening session needs confirmation from participation rather than from a single headline.',
      d.crude
        ? `Macro sensitivity remains live because ${d.crude.name} is ${String(d.crude.trend).toLowerCase()}.`
        : 'Macro confirmation is still thin, so AGI keeps the pre-open view conditional.',
    ].join(' '),
    why,
    watch,
  };

  const midDay = {
    id: 'midDay',
    label: '12 PM',
    title: '12 PM Market Note',
    subtitle: 'Mid-session institutional read',
    outlook: d.moodLabel,
    confidence: d.confidence,
    lead: sharedLead,
    body: [
      `By mid-session, AGI keeps a ${String(d.moodLabel).toLowerCase()} classification because the balance of evidence still depends on breadth versus benchmark direction.`,
      d.weakerBenchmarks.length && d.strongerNames.length
        ? `Softness in ${d.weakerBenchmarks.slice(0, 2).join(' and ')} is being offset by selective strength in names such as ${d.strongerNames.slice(0, 3).join(', ')}, which prevents a one-sided conclusion.`
        : `The mid-day tape remains ${String(d.moodLabel).toLowerCase()} because leadership and participation are still being tested.`,
      d.weakSector
        ? `Relative pressure in ${d.weakSector} remains the main internal drag, while ${d.topSector || 'leading sectors'} continue to define the constructive side of the debate.`
        : `Leadership quality will decide whether the ${String(d.moodLabel).toLowerCase()} stance hardens or fades into the afternoon.`,
    ].join(' '),
    why,
    watch,
  };

  const postMarket = {
    id: 'postMarket',
    label: 'Market Close',
    title: 'Market Close Strategy Note',
    subtitle: 'End-of-day institutional wrap',
    outlook: d.moodLabel,
    confidence: d.confidence,
    lead: sharedLead,
    body: [
      `AGI closes the day ${String(d.moodLabel).toLowerCase()} because the session did not produce clean alignment between benchmarks, breadth and sector leadership.`,
      d.volatilityRising
        ? 'Rising volatility reduced conviction into the close, so the final read stays conditional rather than emphatic.'
        : 'Volatility did not dominate the close, but cross-signal disagreement still kept confidence measured.',
      d.strongerNames.length || d.weakerNames.length
        ? `The close was shaped by selective leadership${d.strongerNames.length ? ` in ${d.strongerNames.slice(0, 3).join(', ')}` : ''}${d.weakerNames.length ? ` and relative pressure in ${d.weakerNames.slice(0, 3).join(', ')}` : ''}.`
        : 'The close leaves investors with a conditional stance rather than a clean directional verdict.',
      'Into the next session, AGI will look for confirmation from breadth durability, leadership quality and whether volatility remains contained.',
    ].join(' '),
    why,
    watch,
  };

  return {
    active: activeSessionKey(),
    preMarket,
    midDay,
    postMarket,
  };
}

function buildStrategyDesk(intelligence, context, facts, mood, sectors) {
  const outlook = intelligence.outlook || {};
  const topSector = sectors.find((sector) => sector.direction === 'Positive')?.name || outlook.topSector;
  const weakSector = sectors.find((sector) => sector.direction === 'Negative')?.name || outlook.weakestSector;
  const crude = (context.commodities || []).find((item) => /crude|oil/i.test(item.name));
  const posts = facts.companyPosts || [];
  const indexDirections = (facts.indices || []).map((index) => ({
    name: index.name,
    direction: index.percentChange == null ? 'stable' : index.percentChange > 0 ? 'stronger' : index.percentChange < 0 ? 'weaker' : 'stable',
  }));
  const weakerBenchmarks = indexDirections.filter((item) => item.direction === 'weaker').map((item) => item.name);
  const strongerBenchmarks = indexDirections.filter((item) => item.direction === 'stronger').map((item) => item.name);
  const volatilityRising = (facts.indices || []).some((item) => /vix/i.test(item.name) && Number(item.percentChange) > 0);
  const gainerNames = (facts.gainers || []).slice(0, 3).map((item) => item.name || item.symbol);
  const loserNames = (facts.losers || []).slice(0, 3).map((item) => item.name || item.symbol);

  const whyReached = [
    weakerBenchmarks.length ? {
      title: 'Benchmark weakness',
      explanation: `AGI classifies benchmarks as comparatively weak because ${weakerBenchmarks.join(' and ')} underperformed during the session. That weakens the overall market thesis even when selective leadership persists.`,
    } : null,
    volatilityRising ? {
      title: 'Rising volatility',
      explanation: 'India VIX moved higher, indicating increased uncertainty. Higher volatility reduces conviction in any single directional conclusion.',
    } : null,
    topSector ? {
      title: `${topSector} leadership`,
      explanation: `${topSector} continues to lead relative participation. That leadership limited how far AGI could push a stronger negative assessment.`,
    } : null,
    {
      title: 'Market breadth',
      explanation: `Breadth is assessed as ${String(outlook.marketBreadth || 'neutral').toLowerCase()}. Breadth remains an important counterweight to index-level weakness when participation stays constructive.`,
    },
    crude ? {
      title: 'Commodity transmission',
      explanation: `${crude.name} conditions are ${String(crude.trend).toLowerCase()}, which remains relevant for energy-sensitive and industrial sector sentiment.`,
    } : null,
    posts.length ? {
      title: 'Disclosure flow',
      explanation: `Recent company disclosures among active names remain part of the evidence set. AGI treats them as informational context rather than directional recommendations.`,
    } : null,
  ].filter(Boolean).slice(0, 5);

  const evidenceFor = {
    technical: [
      `Overall model outlook: ${mood.label}.`,
      `Momentum condition: ${outlook.momentum || 'Moderate'}.`,
      `Volatility condition: ${outlook.volatility || 'Medium'}.`,
    ],
    marketBreadth: [
      `Breadth label: ${outlook.marketBreadth || 'Neutral'}.`,
      weakerBenchmarks.length && strongerBenchmarks.length
        ? 'Index leadership and participation are not fully aligned.'
        : 'Breadth remains an important validator of the current conclusion.',
    ],
    sectorRotation: [
      topSector ? `Relative leadership: ${topSector}.` : 'Sector leadership remains mixed.',
      weakSector ? `Relative weakness: ${weakSector}.` : 'No clear lagging sector is dominant.',
    ],
    corporateEarnings: posts.some((post) => /result|earning|q[1-4]/i.test(post.title))
      ? ['Results-related disclosures are present among monitored names.']
      : ['Evidence is insufficient for a broad earnings conclusion at the market level.'],
    announcements: posts.length
      ? [`${posts.length} recent company posts were available among active names.`]
      : ['Announcement evidence is limited for this session.'],
    macro: [
      crude ? `${crude.name} trend: ${crude.trend}.` : 'Commodity evidence is limited.',
      `Model risk level: ${outlook.risk || 'Medium'}.`,
    ],
    globalMarkets: ['Global risk remains a monitored input; AGI does not invent unsupplied global price conclusions.'],
  };

  const evidenceAgainst = [
    outlook.marketBreadth && /positive|strong/i.test(outlook.marketBreadth)
      ? 'Positive breadth argues against a strongly negative conclusion.'
      : null,
    strongerBenchmarks.length
      ? `${strongerBenchmarks.join(' and ')} outperformed, preventing a one-sided bearish read.`
      : null,
    topSector
      ? `${topSector} leadership shows selective strength inside an otherwise softer session.`
      : null,
    gainerNames.length
      ? `Selective winners such as ${gainerNames.join(', ')} show that participation was not uniformly weak.`
      : null,
  ].filter(Boolean);

  const executiveThesis = `AGI currently classifies the market as ${String(mood.label).toLowerCase()} because benchmark conditions, volatility, breadth and sector leadership are not fully aligned. The conclusion reflects the balance of those inputs rather than any single headline.`;

  const netAssessment = [
    executiveThesis,
    whyReached[0] ? whyReached[0].explanation : null,
    evidenceAgainst[0] ? `Counter-evidence remains material: ${evidenceAgainst[0]}` : null,
    'AGI therefore maintains a conditional conclusion and waits for confirmation from breadth durability, sector leadership and upcoming catalysts.',
  ].filter(Boolean).join(' ');

  const confidenceRationale = `Confidence is ${mood.confidence}% because ${String(outlook.marketBreadth || 'neutral').toLowerCase()} breadth and ${String(outlook.momentum || 'moderate').toLowerCase()} momentum ${mood.confidence >= 60 ? 'provide partial alignment' : 'do not yet provide strong alignment'}, while ${volatilityRising ? 'rising volatility and ' : ''}model risk remain ${String(outlook.risk || 'medium').toLowerCase()}. Disagreement across indicators reduces certainty.`;

  const availableInputs = [
    'Technical indicators',
    'Market breadth',
    facts.indices?.length ? 'Index direction' : null,
    facts.gainers?.length || facts.losers?.length ? 'Session movers' : null,
    posts.length ? 'Company announcements' : null,
    crude ? 'Commodities' : null,
    'Sector rotation',
    context.headlines?.length ? 'Market news context' : null,
  ].filter(Boolean);

  return {
    title: 'AGI Strategy Desk',
    subtitle: 'Chief Investment Strategist Daily Note',
    executiveThesis,
    whyReached,
    evidenceFor,
    evidenceAgainst,
    netAssessment,
    confidence: mood.confidence,
    confidenceRationale,
    whatWouldChange: [
      'A sustained improvement or deterioration in market breadth.',
      'A change in sector leadership away from or toward current leaders.',
      'Material policy communication or earnings surprises among active names.',
      crude ? `A shift in ${crude.name} conditions.` : 'A clearer commodity impulse.',
      'A durable change in volatility regime.',
    ],
    keyRisks: [
      { label: 'Volatility', level: outlook.volatility || 'Medium', why: volatilityRising ? 'Volatility increased during the session, raising uncertainty around near-term conclusions.' : 'Volatility remains a monitored constraint on conviction.' },
      { label: 'Macro / energy', level: crude?.trend === 'Firming' ? 'Medium' : 'Low', why: crude ? `${crude.name} is ${String(crude.trend).toLowerCase()}, which can transmit into inflation and earnings expectations.` : 'Commodity evidence is currently limited.' },
      { label: 'Leadership concentration', level: topSector ? 'Medium' : 'Low', why: topSector ? `Leadership remains concentrated in ${topSector}, so broader confirmation is still required.` : 'Leadership is not clearly concentrated.' },
      { label: 'Global spillover', level: 'Medium', why: 'External developments can quickly alter risk appetite even when domestic participation remains constructive.' },
    ],
    institutionalQuestions: [
      'Will constructive breadth persist if benchmarks remain soft?',
      topSector ? `Can ${topSector} leadership broaden into adjacent sectors?` : 'Which sector will establish clearer leadership next?',
      weakSector ? `Is weakness in ${weakSector} temporary or becoming structural?` : 'Which lagging areas are becoming more material?',
      'Will upcoming disclosures reinforce or invalidate today’s conditional conclusion?',
      'Is the current volatility rise temporary or the start of a broader uncertainty regime?',
    ],
    historicalComparison: {
      title: 'Historical comparison unavailable',
      explanation: 'Evidence is insufficient to assert a verified historical analogue. AGI will only publish period comparisons once similar verified model snapshots are available.',
    },
    reliability: {
      level: availableInputs.length >= 6 ? 'High' : availableInputs.length >= 4 ? 'Moderate' : 'Limited',
      explanation: `Reliability is ${availableInputs.length >= 6 ? 'high' : availableInputs.length >= 4 ? 'moderate' : 'limited'} because today's note incorporates ${availableInputs.length} evidence categories.`,
      inputsUsed: availableInputs,
      missingInputs: [
        !posts.length ? 'Company announcements' : null,
        !crude ? 'Commodities' : null,
        !facts.indices?.length ? 'Index direction' : null,
      ].filter(Boolean),
    },
    watchPoints: [
      ...(loserNames.length ? [`Monitor whether weakness among names such as ${loserNames.join(', ')} broadens.`] : []),
      'Watch whether breadth continues to diverge from benchmark direction.',
      'Track leadership durability in currently stronger sectors.',
      'Assess whether upcoming disclosures change the balance of evidence.',
    ].slice(0, 5),
  };
}

function buildBriefing(intelligence, context, facts = {}) {
  const articles = buildArticles(context.headlines || []);
  const mood = moodFrom(intelligence.outlook || intelligence.pulse || {});
  const themes = buildThemes(articles, intelligence.outlook || {});
  const newsCategories = unique(articles.map((article) => article.category)).filter((category) => category !== 'Markets');
  const sectors = buildSectorImpact(intelligence, newsCategories);
  const companies = buildCompanyImpact(intelligence);
  const strategyDesk = buildStrategyDesk(intelligence, context, facts, mood, sectors);
  const sessionNotes = buildSessionNotes(intelligence, context, facts, mood, sectors);
  const events = buildEvents(articles);
  const risks = buildRisks(intelligence.outlook || {}, context.commodities || []);
  const keyDrivers = strategyDesk.whyReached.map((item, index) => ({
    title: item.title,
    conclusion: item.title,
    explanation: item.explanation,
    importance: index < 2 ? 'High' : 'Medium',
    evidenceUsed: ['Technical', 'Market Breadth', 'Sector Rotation'],
  }));
  const reasoning = buildReasoning(intelligence, mood, keyDrivers, sectors, risks, events);
  const activeNote = sessionNotes[sessionNotes.active] || sessionNotes.postMarket;
  const snapshotIndices = (facts.indices || []).length
    ? facts.indices.slice(0, 4).map((index) => {
      const rising = Number(index.percentChange) > 0;
      const falling = Number(index.percentChange) < 0;
      const isVix = /vix/i.test(index.name);
      const direction = index.percentChange == null
        ? 'Neutral'
        : isVix
          ? (rising ? 'Bearish' : falling ? 'Bullish' : 'Neutral')
          : (rising ? 'Bullish' : falling ? 'Bearish' : 'Neutral');
      return {
        name: index.name,
        direction,
        detail: direction,
      };
    })
    : (intelligence.indexSentiments || []).slice(0, 3).map((index) => ({
      name: index.label,
      direction: toSentiment(index.sentiment),
      detail: index.strength || toSentiment(index.sentiment),
    }));

  const movers = {
    stronger: (facts.gainers || []).slice(0, 5).map((item) => ({
      symbol: item.symbol,
      name: item.name || item.symbol,
      direction: 'Bullish',
      reasoning: 'Relative session strength versus peers in the current tape.',
    })),
    weaker: (facts.losers || []).slice(0, 5).map((item) => ({
      symbol: item.symbol,
      name: item.name || item.symbol,
      direction: 'Bearish',
      reasoning: 'Relative session weakness versus peers in the current tape.',
    })),
  };

  return {
    updatedAt: new Date().toISOString(),
    refreshesAt: new Date(Date.now() + CACHE_MS).toISOString(),
    live: !intelligence.stale,
    aiGenerated: false,
    facts,
    snapshot: {
      marketMood: mood,
      indices: snapshotIndices,
      commodities: (context.commodities || []).slice(0, 5).map((item) => ({
        name: item.name,
        trend: toSentiment(item.trend),
        direction: toSentiment(item.trend),
      })),
      movers,
      breadth: intelligence.breadth ? { label: toSentiment(intelligence.breadth.label || intelligence.breadth) } : { label: toSentiment(mood.label) },
    },
    ticker: articles.slice(0, 8),
    articles,
    intelligence: {
      strategyDesk,
      sessionNotes,
      activeSessionNote: activeNote,
      executiveSummary: activeNote.lead,
      marketStory: activeNote.body,
      marketExplained: activeNote.body,
      consultingDesk: activeNote.body,
      consultantNote: activeNote.body,
      explainedDrivers: (activeNote.why || []).map((item, index) => ({
        rank: index + 1,
        title: `Reason ${index + 1}`,
        explanation: item,
        evidence: [],
        confidence: mood.confidence,
      })),
      keyDrivers,
      mood,
      ...reasoning,
      themes,
      sectorImpact: sectors,
      companyImpact: companies,
      companyPosts: facts.companyPosts || [],
      macro: (context.commodities || []).slice(0, 6).map((item) => ({
        name: item.name,
        trend: toSentiment(item.trend),
      })),
      risks: strategyDesk.keyRisks,
      opportunities: sectors.filter((sector) => sector.direction === 'Positive').map((sector) => ({
        name: sector.name,
        detail: 'Constructive relative conditions in the current AGI model; this is thematic context, not a security recommendation.',
      })).slice(0, 5),
      events,
      tomorrowFocus: (activeNote.watch || []).map((item) => ({ title: item, explanation: item, timing: 'Next session' })),
      historicalContext: strategyDesk.historicalComparison,
    },
    disclaimer: 'AGI session notes interpret market structure in Bullish / Bearish / Neutral terms. Content is informational only and is not investment advice.',
  };
}

async function enrichWithLlm(briefing) {
  const notes = briefing.intelligence.sessionNotes;
  const source = {
    sessionNotes: notes,
    directionalFacts: {
      indices: (briefing.snapshot?.indices || []).map((item) => ({ name: item.name, direction: item.direction })),
      strongerNames: (briefing.snapshot?.movers?.stronger || []).map((item) => item.name),
      weakerNames: (briefing.snapshot?.movers?.weaker || []).map((item) => item.name),
      commodities: (briefing.snapshot.commodities || []).map((item) => ({ name: item.name, trend: item.trend })),
      breadth: briefing.snapshot.breadth,
      sectors: briefing.intelligence.sectorImpact,
      mood: briefing.snapshot.marketMood,
    },
  };
  try {
    const { completeJson } = await import('./llmClient.js');
    const generated = await completeJson({
      system:
        'You are the Chief Investment Strategist of Agarwal Global Investments writing Mint-style institutional market notes. Produce three notes: preMarket, midDay, postMarket. Each must include outlook (Bullish/Neutral/Bearish), lead (1 sentence), body (2-3 short paragraphs), why (string array), watch (string array). Never display prices, index levels, or percentage changes. Use directional language only. Ban generic phrases like “markets remained cautious” or “sentiment remained mixed”. Every important claim must answer “because what?”. Never invent facts. Never give buy/sell/hold recommendations. Return JSON only.',
      user: source,
      temperature: 0.25,
    });
    if (!generated) return briefing;
    const mergeNote = (base, next) => {
      if (!next || typeof next !== 'object') return base;
      return {
        ...base,
        outlook: ['Bullish', 'Neutral', 'Bearish'].includes(next.outlook) ? next.outlook : base.outlook,
        lead: typeof next.lead === 'string' ? next.lead : base.lead,
        body: typeof next.body === 'string' ? next.body : base.body,
        why: Array.isArray(next.why) && next.why.length ? next.why.map(String).slice(0, 5) : base.why,
        watch: Array.isArray(next.watch) && next.watch.length ? next.watch.map(String).slice(0, 5) : base.watch,
      };
    };
    const nextNotes = {
      ...notes,
      preMarket: mergeNote(notes.preMarket, generated.preMarket),
      midDay: mergeNote(notes.midDay, generated.midDay),
      postMarket: mergeNote(notes.postMarket, generated.postMarket),
    };
    const activeNote = nextNotes[nextNotes.active] || nextNotes.postMarket;
    return {
      ...briefing,
      aiGenerated: true,
      intelligence: {
        ...briefing.intelligence,
        sessionNotes: nextNotes,
        activeSessionNote: activeNote,
        executiveSummary: activeNote.lead,
        marketStory: activeNote.body,
        marketExplained: activeNote.body,
        consultingDesk: activeNote.body,
        consultantNote: activeNote.body,
        mood: {
          ...briefing.intelligence.mood,
          label: activeNote.outlook || briefing.intelligence.mood?.label,
        },
        explainedDrivers: (activeNote.why || []).map((item, index) => ({
          rank: index + 1,
          title: `Reason ${index + 1}`,
          explanation: item,
          evidence: [],
          confidence: activeNote.confidence,
        })),
        tomorrowFocus: (activeNote.watch || []).map((item) => ({ title: item, explanation: item, timing: 'Next session' })),
      },
    };
  } catch (error) {
    console.warn('[market-briefing] AI narrative fallback:', error.message);
    return briefing;
  }
}

export async function getMarketBriefing() {
  if (cache && expiresAt > Date.now()) return cache;
  if (inflight) return inflight;
  inflight = (async () => {
    const [intelligence, context, facts] = await Promise.all([
      getAgiIntelligence(),
      getMarketContext(),
      getMarketSessionFacts(),
    ]);
    const briefing = await enrichWithLlm(buildBriefing(intelligence, context, facts));
    cache = briefing;
    expiresAt = Date.now() + CACHE_MS;
    return briefing;
  })().finally(() => {
    inflight = null;
  });
  return inflight;
}

export function startMarketBriefingScheduler() {
  if (scheduler) return;
  const refresh = () => {
    getMarketBriefing().catch((error) => console.warn('[market-briefing] scheduled refresh failed:', error.message));
  };
  refresh();
  scheduler = setInterval(refresh, CACHE_MS);
  scheduler.unref?.();
}
