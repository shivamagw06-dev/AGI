/**
 * IPO Intelligence soft enrichment.
 * Treats CMS IPO articles + live IPO records as structured knowledge assets.
 * Heuristic pipeline only — soft-fails when AI providers are unavailable.
 */

export const ARTICLE_TAGS = [
  'Valuation',
  'Industry',
  'Financial Results',
  'Management',
  'ESG',
  'Risks',
  'Litigation',
  'Competition',
  'Regulation',
  'Anchor Investors',
  'Subscription',
  'Grey Market Premium',
  'Listing Outlook',
];

export const SOURCE_CREDIBILITY = {
  SEBI: 100,
  'Company RHP': 100,
  RHP: 100,
  DRHP: 98,
  Bloomberg: 98,
  Reuters: 97,
  'Economic Times': 93,
  Mint: 92,
  'Business Standard': 91,
  Moneycontrol: 90,
  'Company Presentation': 88,
  'AGIB Research': 94,
  'Broker Reports': 80,
  Media: 75,
};

const PUBLISHER_PATTERNS = [
  [/bloomberg/i, 'Bloomberg'],
  [/reuters/i, 'Reuters'],
  [/economic\s*times|\bet\b/i, 'Economic Times'],
  [/\bmint\b/i, 'Mint'],
  [/business\s*standard|\bbs\b/i, 'Business Standard'],
  [/moneycontrol/i, 'Moneycontrol'],
  [/\brhp\b|red\s*herring/i, 'Company RHP'],
  [/\bdrhp\b|draft\s*red/i, 'DRHP'],
  [/presentation|investor\s*deck/i, 'Company Presentation'],
  [/sebi/i, 'SEBI'],
  [/agib|agarwal\s*global/i, 'AGIB Research'],
  [/broker|research\s*note|icici|hdfc\s*sec|motilal|kotak/i, 'Broker Reports'],
];

const TAG_PATTERNS = [
  [/valuat|ev\/ebitda|p\/e|price\s*band|fair\s*value/i, 'Valuation'],
  [/industry|sector|renewable|solar|wind|pharma|fintech/i, 'Industry'],
  [/result|revenue|ebitda|profit|margin|eps/i, 'Financial Results'],
  [/management|promoter|ceo|cfo|founder/i, 'Management'],
  [/\besg\b|sustainab|carbon|green/i, 'ESG'],
  [/risk|delay|volatil|litigation|lawsuit/i, 'Risks'],
  [/litigation|lawsuit|court|dispute/i, 'Litigation'],
  [/compet|peer|rival|adani|tata|ntpc/i, 'Competition'],
  [/regulat|sebi|policy|compliance/i, 'Regulation'],
  [/anchor/i, 'Anchor Investors'],
  [/subscri|oversubscri|qib|nii|retail/i, 'Subscription'],
  [/gmp|grey\s*market|gray\s*market/i, 'Grey Market Premium'],
  [/listing|list\s*gain|debut/i, 'Listing Outlook'],
];

const BULLISH = /\b(bullish|strong demand|oversubscri|attractive|tailwind|outperform|positive|robust|fully subscribed|institutional demand)\b/i;
const BEARISH = /\b(bearish|weak|concern|risk|delay|overvalued|caution|negative|litigation|volatility|underwhelm)\b/i;
const OPPORTUNITY = /\b(opportunity|expand|visibility|tailwind|order book|ppa|capacity|growth|low-cost)\b/i;
const RISK_WORD = /\b(risk|delay|volatil|regulatory|leverage|execution|litigation|competition)\b/i;

function stripHtml(html = '') {
  return String(html)
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function splitAuthoredPoints(value = '') {
  return String(value)
    .split(/\n|•/)
    .map((item) => item.replace(/^[-*\d.)\s]+/, '').trim())
    .filter(Boolean);
}

function readingTimeMinutes(text = '') {
  const words = String(text).split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 220));
}

export function detectPublisher(article = {}) {
  const hay = `${article.title || ''} ${article.excerpt || ''} ${(article.tags || []).join(' ')} ${article.section || ''}`;
  for (const [pattern, name] of PUBLISHER_PATTERNS) {
    if (pattern.test(hay)) return name;
  }
  if (/research/i.test(article.section || '')) return 'AGIB Research';
  return 'Media';
}

export function credibilityFor(publisher) {
  if (SOURCE_CREDIBILITY[publisher] != null) return SOURCE_CREDIBILITY[publisher];
  return 78;
}

export function classifyTags(article = {}) {
  const hay = `${article.title || ''} ${article.excerpt || ''} ${(article.tags || []).join(' ')}`;
  const found = new Set();
  for (const [pattern, tag] of TAG_PATTERNS) {
    if (pattern.test(hay)) found.add(tag);
  }
  for (const tag of article.tags || []) {
    const match = ARTICLE_TAGS.find((item) => item.toLowerCase() === String(tag).toLowerCase());
    if (match) found.add(match);
  }
  if (!found.size) found.add('Industry');
  return [...found];
}

export function detectSentiment(text = '') {
  const bull = (text.match(BULLISH) || []).length;
  const bear = (text.match(BEARISH) || []).length;
  if (bull > bear + 1) return { label: 'Bullish', impact: 'Positive', score: Math.min(95, 58 + bull * 8) };
  if (bear > bull + 1) return { label: 'Bearish', impact: 'Negative', score: Math.max(12, 42 - bear * 8) };
  if (bull > bear) return { label: 'Mildly Bullish', impact: 'Positive', score: 62 };
  if (bear > bull) return { label: 'Mildly Bearish', impact: 'Negative', score: 38 };
  return { label: 'Neutral', impact: 'Neutral', score: 50 };
}

function extractBullets(text, pattern, limit = 3) {
  const sentences = String(text)
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 28 && s.length < 220);
  const matched = sentences.filter((s) => pattern.test(s));
  const pool = matched.length ? matched : sentences;
  return pool.slice(0, limit);
}

export function buildAiSummary(article = {}, previousArticles = []) {
  const meta = article.researchMeta || {};
  const text = `${article.title || ''}. ${article.excerpt || ''} ${article.analysisText || ''}`;
  const sentiment = article.sentimentScore != null
    ? { label: article.sentiment, impact: article.sentimentImpact, score: article.sentimentScore }
    : detectSentiment(text);
  const thesis = splitAuthoredPoints(meta.thesis);
  const authoredStrengths = splitAuthoredPoints(meta.strengths);
  const authoredRisks = splitAuthoredPoints(meta.risks);
  const takeaways = [...thesis, ...authoredStrengths, ...extractBullets(text, /./, 3)].slice(0, 3);
  const opportunities = [...authoredStrengths, ...extractBullets(text, OPPORTUNITY, 3)].slice(0, 3);
  const risks = [...authoredRisks, ...extractBullets(text, RISK_WORD, 3)].slice(0, 3);
  const prevText = previousArticles.map((a) => `${a.title} ${a.excerpt}`).join(' ');
  const changes = [];
  if (previousArticles.length) {
    if (BULLISH.test(text) && BEARISH.test(prevText)) {
      changes.push('Tone shifted more constructive versus earlier coverage.');
    } else if (BEARISH.test(text) && BULLISH.test(prevText)) {
      changes.push('Tone became more cautious versus earlier coverage.');
    } else {
      changes.push('Incremental update relative to prior articles in this dossier.');
    }
  } else {
    changes.push('First classified research asset for this issuer in the hub.');
  }

  const confidence = Math.min(
    96,
    Math.round((article.credibility || 80) * 0.55 + (takeaways.length ? 20 : 8) + (sentiment.score > 55 || sentiment.score < 45 ? 12 : 6))
  );

  return {
    executiveSummary: takeaways,
    keyTakeaways: takeaways,
    opportunities: opportunities.length ? opportunities : ['No explicit opportunity language detected in excerpt.'],
    risks: risks.length ? risks : ['No explicit risk language detected in excerpt.'],
    newInformation: takeaways.slice(0, 2),
    changesVsPrevious: changes,
    impact: sentiment.impact,
    confidence,
  };
}

export function enrichArticle(raw = {}, previousArticles = []) {
  const analysisText = stripHtml(raw.content_md || raw.content || '');
  const excerpt = stripHtml(raw.excerpt || analysisText);
  const publisher = detectPublisher({ ...raw, excerpt });
  const credibility = credibilityFor(publisher);
  const topics = classifyTags({ ...raw, excerpt });
  const explicitStance = String(raw.equity_research?.stance || '').toLowerCase();
  const stanceMap = {
    bullish: { label: 'Bullish', impact: 'Positive', score: 70 },
    neutral: { label: 'Neutral', impact: 'Neutral', score: 50 },
    bearish: { label: 'Bearish', impact: 'Negative', score: 30 },
  };
  const sentiment = stanceMap[explicitStance] || detectSentiment(`${raw.title || ''} ${excerpt} ${analysisText}`);
  const article = {
    id: raw.id,
    title: raw.title || 'Untitled',
    slug: raw.slug,
    excerpt,
    analysisText,
    coverUrl: raw.cover_url || null,
    section: raw.section || 'IPOs',
    tags: raw.tags || [],
    publishedAt: raw.published_at || null,
    author: raw.author_name || raw.author || 'AGIB Desk',
    publisher,
    credibility,
    topics,
    sentiment: sentiment.label,
    sentimentImpact: sentiment.impact,
    sentimentScore: sentiment.score,
    readingTime: readingTimeMinutes(`${raw.title || ''} ${excerpt}`),
    researchMeta: raw.equity_research && typeof raw.equity_research === 'object' ? raw.equity_research : null,
  };
  article.ai = buildAiSummary(article, previousArticles);
  return article;
}

export function matchArticlesToIpo(articles = [], ipo = {}) {
  if (!ipo?.name && !ipo?.symbol) return articles;
  const tokens = [
    ipo.symbol,
    ...(String(ipo.name || '')
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((t) => t.length > 3)),
  ]
    .filter(Boolean)
    .map((t) => String(t).toLowerCase());

  const scored = articles
    .map((article) => {
      const hay = `${article.title} ${article.excerpt} ${(article.topics || []).join(' ')}`.toLowerCase();
      const hits = tokens.filter((token) => hay.includes(token)).length;
      return { article, hits };
    })
    .filter((row) => row.hits > 0)
    .sort((a, b) => b.hits - a.hits || String(b.article.publishedAt || '').localeCompare(String(a.article.publishedAt || '')));

  return scored.length ? scored.map((row) => row.article) : [];
}

export function buildTimeline(ipo = {}, articles = []) {
  const events = [];
  const push = (date, label, detail) => {
    if (!date) return;
    events.push({ date, label, detail: detail || null });
  };
  push(ipo.biddingStartDate, 'IPO Opens', 'Bidding window opens');
  push(ipo.biddingEndDate, 'IPO Closes', 'Bidding window closes');
  push(ipo.allotmentDate, 'Allotment', 'Allotment expected');
  push(ipo.listingDate, 'Listing', 'Expected listing');
  for (const article of articles) {
    if (article.publishedAt) {
      push(article.publishedAt.slice(0, 10), article.publisher || 'Coverage', article.title);
    }
  }
  return events.sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

const ENTITY_HINTS = [
  'Renewable Energy',
  'Solar',
  'Wind',
  'Power Purchase Agreements',
  'NTPC',
  'Adani Green',
  'Tata Power',
  'SECI',
  'SEBI',
  'QIB',
  'Anchor Investors',
  'Grey Market',
  'Mainboard',
  'SME',
];

export function buildKnowledgeGraph(ipo = {}, articles = []) {
  const root = ipo.name || 'IPO Issuer';
  const nodes = new Set();
  if (ipo.isSme) nodes.add('SME');
  else nodes.add('Mainboard');
  const hay = [ipo.detail, ...articles.map((a) => `${a.title} ${a.excerpt} ${(a.topics || []).join(' ')}`)].join(' ');
  for (const hint of ENTITY_HINTS) {
    if (new RegExp(hint.replace(/\s+/g, '\\s+'), 'i').test(hay)) nodes.add(hint);
  }
  for (const article of articles) {
    for (const topic of article.topics || []) nodes.add(topic);
  }
  if (nodes.size < 3) {
    ['Subscription', 'Valuation', 'Listing Outlook', 'Regulation'].forEach((n) => nodes.add(n));
  }
  return { root, nodes: [...nodes].slice(0, 14) };
}

export function compareSources(articles = []) {
  const rows = {};
  for (const article of articles) {
    const key = article.publisher || 'Media';
    if (!rows[key]) rows[key] = { source: key, Bullish: false, Neutral: false, Bearish: false, credibility: article.credibility };
    const label = String(article.sentiment || '').toLowerCase();
    if (label.includes('bull')) rows[key].Bullish = true;
    else if (label.includes('bear')) rows[key].Bearish = true;
    else rows[key].Neutral = true;
  }
  return Object.values(rows).sort((a, b) => (b.credibility || 0) - (a.credibility || 0));
}

export function detectContradictions(articles = []) {
  const bull = articles.filter((a) => /bull/i.test(a.sentiment || ''));
  const bear = articles.filter((a) => /bear/i.test(a.sentiment || ''));
  if (!bull.length || !bear.length) return [];
  const a = bull[0];
  const b = bear[0];
  return [
    {
      left: { source: a.publisher, claim: a.ai?.keyTakeaways?.[0] || a.title },
      right: { source: b.publisher, claim: b.ai?.keyTakeaways?.[0] || b.title },
      confidence: Math.min(94, Math.round(((a.credibility || 80) + (b.credibility || 80)) / 2)),
      reason:
        'Coverage tone diverges across publishers. Weight higher-credibility filings (RHP/SEBI) and primary subscription data over secondary media.',
    },
  ];
}

export function aggregateInsights(articles = []) {
  const opportunities = [];
  const risks = [];
  for (const article of articles) {
    for (const item of article.ai?.opportunities || []) {
      if (!/no explicit/i.test(item)) opportunities.push(item);
    }
    for (const item of article.ai?.risks || []) {
      if (!/no explicit/i.test(item)) risks.push(item);
    }
  }
  const uniq = (list) => [...new Set(list)].slice(0, 5);
  return {
    topOpportunities: uniq(opportunities).length
      ? uniq(opportunities)
      : ['Upload or publish IPO research to surface opportunity extraction.'],
    topRisks: uniq(risks).length ? uniq(risks) : ['Upload or publish IPO research to surface risk extraction.'],
  };
}

export function intelligencePanel(articles = [], documents = []) {
  const sentiments = articles.map((a) => a.sentimentScore || 50);
  const avg = sentiments.length ? sentiments.reduce((s, n) => s + n, 0) / sentiments.length : 50;
  const contradictions = detectContradictions(articles).length;
  let consensus = 'Neutral';
  if (avg >= 60) consensus = 'Bullish';
  else if (avg <= 40) consensus = 'Bearish';
  const riskScore = Math.max(8, Math.min(92, Math.round(100 - avg + contradictions * 6)));
  const confidence = articles.length
    ? Math.min(96, Math.round(articles.reduce((s, a) => s + (a.credibility || 80), 0) / articles.length))
    : 0;
  return {
    articlesAnalysed: articles.length,
    documents: documents.length,
    consensus,
    sentiment: Math.round(avg),
    riskScore,
    contradictions,
    confidence,
  };
}

export function answerIpoQuestion(question, articles = [], ipo = null) {
  const q = String(question || '').trim();
  if (!q) return null;
  const lower = q.toLowerCase();
  const evidence = articles.slice(0, 5);
  const insights = aggregateInsights(articles);
  const panel = intelligencePanel(articles);
  const reco = /\b(should i buy|buy or sell|worth buying|recommendation)\b/i.test(q);

  let primary = [];
  if (/institution|qib|anchor|bullish|why/i.test(lower)) {
    primary = insights.topOpportunities.slice(0, 4);
  } else if (/risk|bear|concern|caution/i.test(lower)) {
    primary = insights.topRisks.slice(0, 4);
  } else if (/subscri|gmp|retail/i.test(lower)) {
    primary = evidence
      .filter((a) => a.topics?.some((t) => /subscription|grey|listing/i.test(t)))
      .flatMap((a) => a.ai?.keyTakeaways || [])
      .slice(0, 4);
  } else {
    primary = evidence.flatMap((a) => a.ai?.keyTakeaways || []).slice(0, 4);
  }
  if (!primary.length) {
    primary = [
      ipo?.detail || 'Limited classified research is available for this issuer yet.',
      'Publish IPO-section articles in CMS to enrich answers with evidence.',
    ].filter(Boolean);
  }

  const reason = primary[0] || 'Evidence remains limited for an ownership call.';
  const risk = insights.topRisks[0] || primary[1] || 'Offer document and subscription data may still be incomplete.';
  const recommendation = articles.length ? panel.consensus : 'View withheld';

  const institutional = reco
    ? {
        recommendation,
        reason,
        risk,
        horizon: 'Medium Term',
        text:
          recommendation === 'View withheld'
            ? `Research view: Withheld\n\nEvidence is insufficient for an institutional IPO view${ipo?.name ? ` on ${ipo.name}` : ''}. ${reason}`
            : `Research view: ${recommendation}\n\n${reason} ${risk} Suitable for a medium term research horizon.`,
      }
    : null;

  return {
    question: q,
    basedOn: articles.length,
    primaryReasons: primary.slice(0, 3),
    evidence: evidence.map((a) => a.publisher),
    consensus: panel.consensus,
    confidence: panel.confidence || 55,
    institutional,
    askAgiHref: `/ask?q=${encodeURIComponent(ipo?.name ? `${ipo.name} IPO: ${q}` : `IPO: ${q}`)}`,
  };
}

export const LEARNING_MODULES = [
  {
    id: 'drhp-rhp',
    title: 'DRHP vs RHP',
    summary: 'How draft and final offer documents differ, and what changes between filing and issue.',
    topics: ['Regulation', 'Valuation'],
  },
  {
    id: 'anchor-book',
    title: 'Anchor book & QIBs',
    summary: 'Why institutional demand sets tone for subscription and listing expectations.',
    topics: ['Anchor Investors', 'Subscription'],
  },
  {
    id: 'gmp',
    title: 'Grey market premium',
    summary: 'What GMP signals — and why it is not a substitute for fundamental research.',
    topics: ['Grey Market Premium', 'Listing Outlook'],
  },
  {
    id: 'allotment',
    title: 'Allotment mechanics',
    summary: 'Retail lots, HNI categories, and how oversubscription affects probability.',
    topics: ['Subscription', 'Regulation'],
  },
  {
    id: 'listing-day',
    title: 'Listing-day framework',
    summary: 'Separate issue quality, valuation, and listing froth before forming a view.',
    topics: ['Listing Outlook', 'Valuation'],
  },
  {
    id: 'credibility',
    title: 'Source credibility',
    summary: 'Weight SEBI/RHP primary documents above secondary media in the research stack.',
    topics: ['Regulation', 'Risks'],
  },
];

export const LIBRARY_DOC_TYPES = [
  'DRHP',
  'RHP',
  'Prospectus',
  'Annual Reports',
  'Investor Presentations',
  'Credit Rating Reports',
  'Conference Call Transcripts',
  'Earnings Releases',
  'Media Coverage',
  'AGIB Research Notes',
];

export function classifyLibraryDocs(articles = [], ipo = null) {
  const buckets = Object.fromEntries(LIBRARY_DOC_TYPES.map((type) => [type, []]));
  for (const article of articles) {
    const hay = `${article.title} ${article.publisher} ${(article.topics || []).join(' ')}`;
    let type = 'Media Coverage';
    if (/drhp/i.test(hay)) type = 'DRHP';
    else if (/rhp|prospectus/i.test(hay)) type = 'RHP';
    else if (/annual\s*report/i.test(hay)) type = 'Annual Reports';
    else if (/presentation|deck/i.test(hay)) type = 'Investor Presentations';
    else if (/rating|crisil|icra|care/i.test(hay)) type = 'Credit Rating Reports';
    else if (/transcript|concall|conference/i.test(hay)) type = 'Conference Call Transcripts';
    else if (/earning|result/i.test(hay)) type = 'Earnings Releases';
    else if (/agib/i.test(hay)) type = 'AGIB Research Notes';
    else if (/prospectus/i.test(hay)) type = 'Prospectus';
    buckets[type].push(article);
  }
  if (ipo?.documentUrl) {
    buckets.RHP.unshift({
      id: `doc-${ipo.symbol}`,
      title: `${ipo.name} offer document`,
      publisher: 'Company RHP',
      externalUrl: ipo.documentUrl,
      credibility: 100,
    });
  }
  return buckets;
}
