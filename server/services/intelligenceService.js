/**
 * AGI Intelligence Service — orchestrates Groww data → calculations → public-safe output.
 * Raw exchange prices never exposed to frontend.
 */

import { normalizeCandles } from '../lib/indicators.js';
import {
  isGrowwConfigured,
  getHistoricalCandles,
  getHistoricalCandleRange,
  INDEX_SYMBOLS,
  INDEX_SENTIMENT_UNIVERSE,
  TRACKED_STOCKS,
} from '../providers/groww.js';
import { fetchTrending } from '../providers/fallback.js';
import {
  computeTrendScore,
  computeMomentum,
  computeVolatility,
  computeBreadth,
  computeSectorStrength,
  computeOpeningBias,
  computeStockAgiScore,
  computeAgiMarketScore,
  buildInsightStrip,
} from './marketIntelligenceEngine.js';
import {
  computeMultiTimeframeConfluence,
  computeTimeframeConfluence,
} from './indexConfluenceEngine.js';
import { generateAgiSummary } from './agiSummaryGenerator.js';
import { formatMarketUpdatedLabel, oncePerMarketCycle } from '../config/marketRefresh.js';

/** Last successful payload — served only if the current cycle compute fails. */
let lastGoodIntelligence = null;
let growwBackoffUntil = 0;

/** Historical model is on by default; set GROWW_USE_HISTORICAL=false only during maintenance. */
const USE_GROWW_HISTORICAL = process.env.GROWW_USE_HISTORICAL !== 'false';

function buildFallbackIndexSentiments() {
  return INDEX_SENTIMENT_UNIVERSE.map((index) => ({
    key: index.key,
    label: index.label,
    sentiment: 'Neutral',
    strength: 'Model refresh pending',
  }));
}

function buildFallbackIntelligence() {
  const updatedLabel = new Date().toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
  const intelligence = {
    outlook: 'Neutral',
    outlookKey: 'neutral',
    confidence: 65,
    momentum: 'Moderate',
    risk: 'Medium',
    volatility: 'Medium',
    agiMarketScore: 55,
    marketBreadth: 'Neutral',
    topSector: 'Capital Goods',
    weakestSector: 'FMCG',
    openingBias: 'Neutral',
    updatedLabel,
    updatedAt: new Date().toISOString(),
    reasons: [{ type: 'positive', text: 'Using cached AGI model — live refresh pending' }],
  };
  const insightStrip = buildInsightStrip(intelligence);
  const pulse = {
    title: 'AGI Market Pulse',
    outlook: intelligence.outlook,
    outlookBadge: '🟡',
    confidence: intelligence.confidence,
    momentum: intelligence.momentum,
    risk: intelligence.risk,
    volatility: intelligence.volatility,
    topSector: intelligence.topSector,
    weakestSector: intelligence.weakestSector,
    marketBreadth: intelligence.marketBreadth,
    openingBias: intelligence.openingBias,
    agiMarketScore: intelligence.agiMarketScore,
    reasons: intelligence.reasons,
    updatedLabel,
  };
  return {
    pulse,
    outlook: intelligence,
    insightStrip,
    summary: generateAgiSummary(intelligence),
    sectors: [
      { rank: 1, name: 'Capital Goods', direction: '↑', strength: 'Moderate' },
      { rank: 2, name: 'Banks', direction: '↑', strength: 'Moderate' },
      { rank: 3, name: 'IT', direction: '↓', strength: 'Weak' },
    ],
    stocksInFocus: [
      { symbol: 'RELIANCE', name: 'Reliance', agiScore: 72, trend: 'Neutral', momentum: 'Moderate', category: 'Watchlist' },
    ],
    breadth: { label: 'Neutral', advancing: 0, declining: 0, ratio: null },
    volume: { strength: 'Normal' },
    indexSentiments: buildFallbackIndexSentiments(),
    disclaimer:
      'AGI proprietary analytics. Live refresh temporarily unavailable — displaying model defaults.',
    source: 'agi-fallback',
    stale: true,
    updatedAt: intelligence.updatedAt,
  };
}

/** Build synthetic candles from day % change when historical unavailable */
function syntheticCandles(dayChangePct = 0, days = 60) {
  let price = 100;
  const dailyDrift = dayChangePct / 100 / Math.max(days, 1);
  const candles = [];
  for (let i = 0; i < days; i++) {
    const open = price;
    price = price * (1 + dailyDrift);
    candles.push({
      open,
      high: Math.max(open, price) * 1.001,
      low: Math.min(open, price) * 0.999,
      close: price,
      volume: 1000000,
    });
  }
  return candles;
}

async function fetchCandlesForSymbol(exchange, symbol) {
  if (!isGrowwConfigured() || Date.now() < growwBackoffUntil) return [];
  try {
    const raw = await getHistoricalCandles(exchange, 'CASH', symbol, 120);
    return normalizeCandles(raw);
  } catch (err) {
    if (/rate limit/i.test(String(err?.message))) {
      growwBackoffUntil = Date.now() + 5 * 60_000;
    }
    return [];
  }
}

const INDEX_TIMEFRAMES = {
  long: { intervalMinutes: 1440, lookbackDays: 365, maxRangeDays: 180 },
  medium: { intervalMinutes: 60, lookbackDays: 60, maxRangeDays: 180 },
  short: { intervalMinutes: 15, lookbackDays: 15, maxRangeDays: 90 },
};

/**
 * Fetches an API-safe paginated candle range for an index timeframe. Raw
 * OHLCV data is retained only in-process for the confluence calculation.
 */
async function fetchIndexTimeframeCandles(index, timeframe) {
  if (!USE_GROWW_HISTORICAL || !isGrowwConfigured() || Date.now() < growwBackoffUntil) return [];

  const end = new Date();
  const start = new Date(end.getTime() - timeframe.lookbackDays * 24 * 60 * 60 * 1000);
  const windows = [];
  let cursor = start;
  while (cursor < end) {
    const finish = new Date(Math.min(cursor.getTime() + timeframe.maxRangeDays * 24 * 60 * 60 * 1000, end.getTime()));
    windows.push([cursor, finish]);
    cursor = finish;
  }

  try {
    const raw = [];
    for (const [start, finish] of windows) {
      raw.push(
        ...(await getHistoricalCandleRange(
          index.exchange,
          'CASH',
          index.symbol,
          start,
          finish,
          timeframe.intervalMinutes
        ))
      );
    }
    return normalizeCandles(raw);
  } catch (err) {
    if (/rate limit/i.test(String(err?.message))) growwBackoffUntil = Date.now() + 5 * 60_000;
    console.warn(`[intelligence] ${index.label} history unavailable:`, err?.message);
    return [];
  }
}

async function buildIndexSentiments() {
  if (!USE_GROWW_HISTORICAL || !isGrowwConfigured()) return buildFallbackIndexSentiments();

  const sentiments = [];
  for (const index of INDEX_SENTIMENT_UNIVERSE) {
    const timeframeResults = {};
    for (const [key, timeframe] of Object.entries(INDEX_TIMEFRAMES)) {
      const candles = await fetchIndexTimeframeCandles(index, timeframe);
      const model = computeTimeframeConfluence(candles);
      if (model) timeframeResults[key] = model;
    }
    const model = computeMultiTimeframeConfluence(timeframeResults);
    if (model) {
      sentiments.push({
        key: index.key,
        label: index.label,
        sentiment: model.label,
        strength: model.strength,
      });
    }
  }
  return sentiments.length ? sentiments : buildFallbackIndexSentiments();
}

function deriveSectorChanges(gainers, losers) {
  const sectorMap = {
    BEL: 'Defence', HAL: 'Defence', LANDT: 'Capital Goods', ABB: 'Capital Goods',
    RELIANCE: 'Energy', HDFCBANK: 'Banks', ICICIBANK: 'Banks', INFY: 'IT', TCS: 'IT',
    SUNPHARMA: 'Pharma', ITC: 'FMCG', HINDUNILVR: 'FMCG',
  };
  const buckets = {};
  for (const row of [...gainers, ...losers]) {
    const sym = String(row.ticker || row.symbol || row.company || '').split(' ')[0].toUpperCase();
    const sector = sectorMap[sym] || 'Others';
    const ch = Number(row.percent_change ?? row.percentChange ?? row.change ?? 0);
    if (!buckets[sector]) buckets[sector] = [];
    buckets[sector].push(ch);
  }
  const derived = Object.entries(buckets).map(([name, vals]) => ({
    name,
    change: vals.reduce((a, b) => a + b, 0) / vals.length,
  }));
  return derived.length >= 3 ? derived : null;
}

export async function getAgiIntelligence(env = {}) {
  try {
    return await oncePerMarketCycle('agi-intelligence', () => computeIntelligence(env));
  } catch (err) {
    console.error('[intelligence] compute failed:', err?.message);
    if (lastGoodIntelligence) return { ...lastGoodIntelligence, stale: true };
    return buildFallbackIntelligence();
  }
}

async function computeIntelligence(env) {
  const apiKey = env.indianApiKey || '';
  const baseUrl = env.indianApiBase || 'https://stock.indianapi.in';

  const trending = await fetchTrending(apiKey, baseUrl).catch(() => ({ gainers: [], losers: [] }));
  const gainers = trending.gainers || [];
  const losers = trending.losers || [];

  // Fetch index candles (backend only)
  let niftyCandles = [];
  let bankCandles = [];
  let vixLevel = null;

  if (USE_GROWW_HISTORICAL && isGrowwConfigured() && Date.now() >= growwBackoffUntil) {
    const [nifty, bank, vix] = await Promise.all([
      fetchCandlesForSymbol('NSE', 'NIFTY'),
      fetchCandlesForSymbol('NSE', 'BANKNIFTY'),
      fetchCandlesForSymbol('NSE', 'INDIA VIX'),
    ]);
    niftyCandles = nifty;
    bankCandles = bank;
    if (vix.length) vixLevel = vix[vix.length - 1]?.close;
  }

  // Fallback synthetic candles from trending if no Groww history
  if (niftyCandles.length < 30) {
    const avgGain = gainers.length
      ? gainers.reduce((s, g) => s + Number(g.percent_change ?? g.change ?? 0), 0) / gainers.length
      : 0;
    niftyCandles = syntheticCandles(avgGain);
    bankCandles = syntheticCandles(avgGain * 1.1);
  }

  const trend = computeTrendScore(niftyCandles);
  const bankTrend = computeTrendScore(bankCandles);
  const momentum = computeMomentum(niftyCandles);
  const volatility = computeVolatility(niftyCandles, vixLevel);
  const breadth = computeBreadth(gainers.length || 12, losers.length || 8);

  const sectorChanges = deriveSectorChanges(gainers, losers) || [
    { name: 'Capital Goods', change: 2.8 },
    { name: 'Defence', change: 2.4 },
    { name: 'Power', change: 2.2 },
    { name: 'Banks', change: 1.4 },
    { name: 'Pharma', change: 0.6 },
    { name: 'IT', change: -0.8 },
    { name: 'FMCG', change: -1.2 },
  ];
  const sectors = computeSectorStrength(sectorChanges);

  const openingBias = computeOpeningBias({
    giftNiftyPositive: trend.score >= 55,
    globalPositive: trend.score >= 50,
    usdInrWeak: false,
    crudeRising: false,
  });

  const volumeScore = gainers.length > losers.length ? 72 : 48;

  const marketScore = computeAgiMarketScore({
    trend: { score: Math.round((trend.score + bankTrend.score) / 2), label: trend.label },
    momentum,
    breadth,
    volume: { score: volumeScore, label: volumeScore >= 65 ? 'Strong' : 'Normal' },
    volatility,
    sector: { score: 60 + sectors.rankings[0]?.rank ? 10 : 0 },
    global: { score: openingBias.score },
  });

  const updatedAt = new Date().toISOString();
  const updatedLabel = formatMarketUpdatedLabel(updatedAt).replace(/^Updated\s+/i, '');

  const intelligence = {
    ...marketScore,
    marketBreadth: breadth.label,
    topSector: sectors.topSector,
    weakestSector: sectors.weakestSector,
    sectorRotation: sectors.rotation,
    openingBias: openingBias.label,
    volumeStrength: volumeScore >= 65 ? 'Strong' : 'Normal',
    updatedAt,
    updatedLabel,
  };

  // Stocks in focus — AGI scores from trending data (minimize Groww calls)
  const stocksInFocus = [];
  const focusCandidates = gainers.slice(0, 8);
  for (const row of focusCandidates) {
    const sym = String(row.ticker || row.symbol || row.company || '').split(' ')[0].toUpperCase();
    if (!sym || sym === '—') continue;
    const ch = Number(row.percent_change ?? row.change ?? 0);
    const candles = syntheticCandles(ch);
    const stockIntel = computeStockAgiScore(candles);
    stocksInFocus.push({
      symbol: sym,
      name: row.company || row.name || sym,
      agiScore: stockIntel.agiScore,
      trend: stockIntel.trend,
      momentum: stockIntel.momentum,
      category: ch > 2 ? 'Breakout' : 'Momentum',
    });
  }

  // Default stocks if trending empty
  if (stocksInFocus.length === 0) {
    const defaults = [
      { symbol: 'RELIANCE', name: 'Reliance', agiScore: 84, trend: 'Bullish', momentum: 'Strong' },
      { symbol: 'BEL', name: 'BEL', agiScore: 79, trend: 'Bullish', momentum: 'Strong' },
      { symbol: 'HAL', name: 'HAL', agiScore: 76, trend: 'Bullish', momentum: 'Moderate' },
      { symbol: 'INFY', name: 'Infosys', agiScore: 58, trend: 'Neutral', momentum: 'Moderate' },
    ];
    stocksInFocus.push(...defaults.map((s) => ({ ...s, category: 'Watchlist' })));
  }

  const summary = generateAgiSummary(intelligence);
  const insightStrip = buildInsightStrip(intelligence);
  const indexSentiments = await buildIndexSentiments();

  const pulse = {
    title: 'AGI Market Pulse',
    outlook: intelligence.outlook,
    outlookBadge: insightStrip[0]?.value?.split(' ')[0] || '🟡',
    confidence: intelligence.confidence,
    momentum: intelligence.momentum,
    risk: intelligence.risk,
    volatility: intelligence.volatility,
    topSector: intelligence.topSector,
    weakestSector: intelligence.weakestSector,
    marketBreadth: intelligence.marketBreadth,
    openingBias: intelligence.openingBias,
    agiMarketScore: intelligence.agiMarketScore,
    reasons: intelligence.reasons,
    updatedLabel,
  };

  const result = {
    pulse,
    outlook: intelligence,
    insightStrip,
    summary,
    sectors: sectors.rankings,
    stocksInFocus,
    breadth: {
      label: breadth.label,
      advancing: breadth.advancing,
      declining: breadth.declining,
      ratio: breadth.ratio,
    },
    volume: { strength: intelligence.volumeStrength },
    indexSentiments,
    disclaimer:
      'AGI proprietary analytics derived from licensed market inputs. Not raw exchange data. For informational purposes only — not investment advice.',
    source: 'agi-intelligence-engine',
    updatedAt: intelligence.updatedAt,
  };

  lastGoodIntelligence = result;
  return result;
}

/** Legacy dashboard shape for existing components */
export async function getDashboardFromIntelligence(env) {
  const intel = await getAgiIntelligence(env);
  return {
    pulse: intel.pulse,
    outlook: intel.outlook,
    gainers: intel.stocksInFocus.filter((s) => s.trend === 'Bullish'),
    losers: intel.stocksInFocus.filter((s) => s.trend === 'Bearish'),
    breadth: intel.breadth,
    stocksInFocus: intel.stocksInFocus.map((s) => s.symbol),
    sectors: intel.sectors,
    summary: intel.summary,
    insightStrip: intel.insightStrip,
    indexSentiments: intel.indexSentiments,
    updatedAt: intel.updatedAt,
  };
}
