/**
 * AGI Market Intelligence Engine
 * Deterministic scoring from licensed inputs — outputs proprietary analytics only.
 * Raw exchange prices never leave this layer to the public API.
 */

import {
  lastEma,
  rsi,
  macd,
  atr,
  adx,
  roc,
  closesFromCandles,
} from '../lib/indicators.js';

const AGI_SCORE_BANDS = [
  { min: 81, label: 'Strong Bullish', key: 'strong_bullish' },
  { min: 61, label: 'Bullish', key: 'bullish' },
  { min: 41, label: 'Neutral', key: 'neutral' },
  { min: 21, label: 'Bearish', key: 'bearish' },
  { min: 0, label: 'Strong Bearish', key: 'strong_bearish' },
];

function band(score) {
  for (const b of AGI_SCORE_BANDS) {
    if (score >= b.min) return b;
  }
  return AGI_SCORE_BANDS[AGI_SCORE_BANDS.length - 1];
}

function clamp(n, lo = 0, hi = 100) {
  return Math.max(lo, Math.min(hi, Math.round(n)));
}

function simpleMovingAverage(values, period) {
  if (values.length < period) return null;
  return values.slice(-period).reduce((sum, value) => sum + value, 0) / period;
}

function bollingerBands(values, period = 20, standardDeviations = 2) {
  const window = values.slice(-period);
  if (window.length < period) return null;
  const middle = window.reduce((sum, value) => sum + value, 0) / period;
  const variance = window.reduce((sum, value) => sum + (value - middle) ** 2, 0) / period;
  const deviation = Math.sqrt(variance);
  return { upper: middle + standardDeviations * deviation, middle, lower: middle - standardDeviations * deviation };
}

function scoreRsi(value) {
  if (!Number.isFinite(value)) return 0.5;
  if (value >= 70) return 0.65;
  if (value >= 60) return 1;
  if (value >= 50) return 0.75;
  if (value >= 40) return 0.4;
  if (value >= 30) return 0.25;
  return 0.1;
}

function scoreMacd(value) {
  if (!value || !Number.isFinite(value.macd) || !Number.isFinite(value.signal)) return 0.5;
  let score = 0.5;
  score += value.macd > value.signal ? 0.25 : -0.25;
  score += value.macd > 0 ? 0.15 : -0.15;
  score += value.histogram > 0 ? 0.1 : -0.1;
  return Math.max(0, Math.min(1, score));
}

function scoreSma(close, shortSma, longSma) {
  if (![close, shortSma, longSma].every(Number.isFinite)) return 0.5;
  if (close > shortSma && shortSma > longSma) return 1;
  if (close > longSma && shortSma > longSma) return 0.8;
  if (close > longSma) return 0.6;
  if (close < shortSma && shortSma < longSma) return 0;
  if (close < longSma) return 0.25;
  return 0.5;
}

function scoreEma(shortEma, longEma) {
  if (![shortEma, longEma].every(Number.isFinite) || longEma === 0) return 0.5;
  if (shortEma > longEma) return Math.min(1, 0.65 + ((shortEma - longEma) / longEma) * 5);
  return Math.max(0, 0.35 - ((longEma - shortEma) / longEma) * 5);
}

function scoreBollinger(close, bands) {
  if (!bands || !Number.isFinite(close)) return 0.5;
  const width = bands.upper - bands.lower;
  return width ? Math.max(0, Math.min(1, (close - bands.lower) / width)) : 0.5;
}

function scoreAdx(value) {
  if (!Number.isFinite(value)) return 0.5;
  if (value >= 40) return 1;
  if (value >= 25) return 0.75;
  if (value >= 20) return 0.55;
  return 0.3;
}

function scorePriceVsSma200(close, sma200) {
  if (![close, sma200].every(Number.isFinite) || sma200 === 0) return 0.5;
  const percent = ((close - sma200) / sma200) * 100;
  if (percent >= 5) return 1;
  if (percent >= 2) return 0.85;
  if (percent >= 0) return 0.65;
  if (percent >= -2) return 0.35;
  if (percent >= -5) return 0.2;
  return 0.05;
}

export function indexSentimentLabel(score) {
  if (score >= 80) return 'Strongly Bullish';
  if (score >= 65) return 'Bullish';
  if (score >= 50) return 'Mildly Bullish';
  if (score >= 35) return 'Mildly Bearish';
  if (score >= 20) return 'Bearish';
  return 'Strongly Bearish';
}

/**
 * Seven-factor index model supplied by AGI: RSI, MACD, SMA/EMA alignment,
 * Bollinger position, ADX and price-vs-SMA200. The returned score stays server-side;
 * public clients receive only its derived label and strength.
 */
export function computeIndexBullishness(candles) {
  const closes = closesFromCandles(candles);
  if (closes.length < 200) return null;

  const close = closes[closes.length - 1];
  const macdValue = macd(closes);
  const weightedScore =
    scoreRsi(rsi(closes, 14)) * 0.2 +
    scoreMacd(macdValue) * 0.2 +
    scoreSma(close, simpleMovingAverage(closes, 20), simpleMovingAverage(closes, 50)) * 0.15 +
    scoreEma(lastEma(closes, 9), lastEma(closes, 21)) * 0.15 +
    scoreBollinger(close, bollingerBands(closes)) * 0.1 +
    scoreAdx(adx(candles, 14)) * 0.1 +
    scorePriceVsSma200(close, simpleMovingAverage(closes, 200)) * 0.1;
  const score = clamp(weightedScore * 100);

  return {
    label: indexSentimentLabel(score),
    strength: score >= 65 || score < 35 ? 'High conviction' : 'Developing',
  };
}

/** Trend score 0–100 from EMA alignment rules */
export function computeTrendScore(candles) {
  const closes = closesFromCandles(candles);
  if (closes.length < 50) return { score: 50, label: 'Neutral', signals: [] };

  const price = closes[closes.length - 1];
  const ema20 = lastEma(closes, 20);
  const ema50 = lastEma(closes, 50);
  const ema200 = closes.length >= 200 ? lastEma(closes, 200) : lastEma(closes, Math.min(closes.length, 100));

  let points = 0;
  const signals = [];
  if (price > ema20) { points += 1; signals.push('Above EMA20'); }
  if (price > ema50) { points += 1; signals.push('Above EMA50'); }
  if (price > ema200) { points += 2; signals.push('Above EMA200'); }
  if (ema20 > ema50) { points += 1; signals.push('EMA20 > EMA50'); }
  if (ema50 > ema200) { points += 1; signals.push('EMA50 > EMA200'); }

  let label = 'Neutral';
  if (points <= 2) label = 'Bearish';
  else if (points >= 5) label = 'Bullish';

  const score = clamp((points / 6) * 100);
  return { score, label, signals, ema20, ema50, ema200 };
}

/** Momentum score from RSI + MACD + ADX */
export function computeMomentum(candles) {
  const closes = closesFromCandles(candles);
  if (closes.length < 30) return { score: 50, label: 'Moderate', rsi: null, macd: null, adx: null };

  const rsiVal = rsi(closes);
  const macdVal = macd(closes);
  const adxVal = adx(candles);
  const rocVal = roc(closes);

  let score = 50;
  if (rsiVal != null) {
    if (rsiVal > 60) score += 15;
    else if (rsiVal > 50) score += 8;
    else if (rsiVal < 40) score -= 15;
    else if (rsiVal < 50) score -= 5;
  }
  if (macdVal?.bullish) score += 12;
  else if (macdVal) score -= 8;
  if (adxVal != null && adxVal > 25) score += 8;
  if (rocVal != null && rocVal > 1) score += 5;
  else if (rocVal != null && rocVal < -1) score -= 5;

  score = clamp(score);
  let label = 'Moderate';
  if (score >= 70) label = 'Strong';
  else if (score >= 55) label = 'Moderate';
  else if (score < 45) label = 'Weak';
  else label = 'Moderate';

  return { score, label, rsi: rsiVal, macd: macdVal, adx: adxVal, roc: rocVal };
}

/** Volatility from ATR % and optional VIX level */
export function computeVolatility(candles, vixLevel = null) {
  const closes = closesFromCandles(candles);
  const atrVal = atr(candles);
  const price = closes[closes.length - 1] || 1;
  const atrPct = atrVal ? (atrVal / price) * 100 : null;

  let score = 50;
  if (atrPct != null) {
    if (atrPct < 1) score = 85;
    else if (atrPct < 1.5) score = 70;
    else if (atrPct < 2.5) score = 50;
    else score = 25;
  }
  if (vixLevel != null && Number.isFinite(vixLevel)) {
    if (vixLevel < 13) score = Math.max(score, 80);
    else if (vixLevel < 18) score = Math.min(score, 55);
    else score = Math.min(score, 30);
  }

  let label = 'Medium';
  if (score >= 70) label = 'Low';
  else if (score >= 45) label = 'Medium';
  else label = 'High';

  return { score, label, atrPct, vixLevel };
}

/** Market breadth from advancing/declining counts */
export function computeBreadth(advancing, declining) {
  const adv = Number(advancing) || 0;
  const dec = Number(declining) || 0;
  if (adv === 0 && dec === 0) return { score: 50, label: 'Neutral', ratio: null };

  const ratio = dec > 0 ? adv / dec : adv;
  let label = 'Neutral';
  let score = 50;
  if (ratio > 1.5) { label = 'Very Positive'; score = 85; }
  else if (ratio > 1.2) { label = 'Positive'; score = 72; }
  else if (ratio >= 0.9) { label = 'Neutral'; score = 50; }
  else if (ratio >= 0.7) { label = 'Negative'; score = 35; }
  else { label = 'Very Negative'; score = 20; }

  return { score, label, ratio, advancing: adv, declining: dec };
}

/** Sector rankings from average % change */
export function computeSectorStrength(sectorChanges = []) {
  const sorted = [...sectorChanges]
    .filter((s) => s.name && Number.isFinite(Number(s.change)))
    .sort((a, b) => Number(b.change) - Number(a.change));

  return {
    rankings: sorted.map((s, i) => ({
      rank: i + 1,
      name: s.name,
      direction: Number(s.change) >= 0 ? '↑' : '↓',
      strength: Number(s.change) >= 1.5 ? 'Strong' : Number(s.change) >= 0 ? 'Moderate' : 'Weak',
    })),
    topSector: sorted[0]?.name || 'Capital Goods',
    weakestSector: sorted[sorted.length - 1]?.name || 'FMCG',
    rotation: sorted.length >= 2 && sorted[0].change - sorted[sorted.length - 1].change > 2
      ? `Rotation into ${sorted[0].name}`
      : 'Stable leadership',
  };
}

/** Opening bias from global cues (derived labels only) */
export function computeOpeningBias(cues = {}) {
  let score = 50;
  const signals = [];
  if (cues.giftNiftyPositive) { score += 15; signals.push('Gift Nifty positive'); }
  if (cues.globalPositive) { score += 10; signals.push('Global markets firm'); }
  if (cues.usdInrWeak) { score -= 8; signals.push('Rupee under pressure'); }
  if (cues.crudeRising) { score -= 6; signals.push('Crude oil elevated'); }
  if (cues.goldRising) { score -= 3; signals.push('Safe-haven demand'); }

  score = clamp(score);
  let label = 'Neutral';
  if (score >= 65) label = 'Positive';
  else if (score < 40) label = 'Negative';

  return { score, label, signals };
}

/** AGI Score for a single stock 0–100 */
export function computeStockAgiScore(candles) {
  const trend = computeTrendScore(candles);
  const momentum = computeMomentum(candles);
  const vol = computeVolatility(candles);
  const score = clamp(trend.score * 0.4 + momentum.score * 0.45 + vol.score * 0.15);

  let trendLabel = 'Neutral';
  if (score >= 65) trendLabel = 'Bullish';
  else if (score < 40) trendLabel = 'Bearish';

  return { agiScore: score, trend: trendLabel, momentum: momentum.label };
}

/** Weighted AGI Market Score 0–100 */
export function computeAgiMarketScore(factors) {
  const weights = {
    trend: 0.3,
    momentum: 0.2,
    breadth: 0.15,
    volume: 0.1,
    volatility: 0.1,
    sector: 0.1,
    global: 0.05,
  };

  const score = clamp(
    (factors.trend?.score ?? 50) * weights.trend +
      (factors.momentum?.score ?? 50) * weights.momentum +
      (factors.breadth?.score ?? 50) * weights.breadth +
      (factors.volume?.score ?? 50) * weights.volume +
      (factors.volatility?.score ?? 50) * weights.volatility +
      (factors.sector?.score ?? 50) * weights.sector +
      (factors.global?.score ?? 50) * weights.global
  );

  const b = band(score);
  const confidence = clamp(
    score * 0.7 +
      (factors.breadth?.score ?? 50) * 0.15 +
      (factors.momentum?.score ?? 50) * 0.15
  );

  let risk = 'Medium';
  const riskPoints =
    (factors.volatility?.label === 'High' ? 2 : 0) +
    (factors.breadth?.label?.includes('Negative') ? 2 : 0) +
    (factors.trend?.label === 'Bearish' ? 2 : 0);
  if (riskPoints >= 4) risk = 'High';
  else if (riskPoints <= 1) risk = 'Low';

  const reasons = [];
  if (factors.trend?.label === 'Bullish') reasons.push({ type: 'positive', text: 'Trend indicators aligned bullish' });
  if (factors.momentum?.label === 'Strong') reasons.push({ type: 'positive', text: 'Momentum remains strong' });
  if (factors.breadth?.label?.includes('Positive')) reasons.push({ type: 'positive', text: 'Market breadth supportive' });
  if (factors.volatility?.label === 'Low') reasons.push({ type: 'positive', text: 'Volatility contained' });
  if (factors.trend?.label === 'Bearish') reasons.push({ type: 'negative', text: 'Trend weakening' });
  if (factors.breadth?.label?.includes('Negative')) reasons.push({ type: 'negative', text: 'Breadth deteriorating' });
  if (factors.volatility?.label === 'High') reasons.push({ type: 'negative', text: 'Elevated volatility' });

  return {
    agiMarketScore: score,
    outlook: b.label,
    outlookKey: b.key,
    confidence,
    momentum: factors.momentum?.label || 'Moderate',
    risk,
    volatility: factors.volatility?.label || 'Medium',
    reasons: reasons.slice(0, 5),
  };
}

/** Build insight strip items — NO raw prices */
export function buildInsightStrip(intelligence) {
  const badge =
    intelligence.outlookKey === 'strong_bullish' || intelligence.outlookKey === 'bullish'
      ? '🟢'
      : intelligence.outlookKey === 'strong_bearish' || intelligence.outlookKey === 'bearish'
        ? '🔴'
        : '🟡';

  return [
    { id: 'outlook', label: 'Market Outlook', value: `${badge} ${intelligence.outlook}`, sub: `Updated ${intelligence.updatedLabel}` },
    { id: 'confidence', label: 'Confidence', value: `${intelligence.confidence}%` },
    { id: 'volatility', label: 'Volatility', value: intelligence.volatility },
    { id: 'opening', label: 'Opening Bias', value: intelligence.openingBias || 'Neutral' },
    { id: 'breadth', label: 'Market Breadth', value: intelligence.marketBreadth || 'Neutral' },
    { id: 'momentum', label: 'Momentum', value: intelligence.momentum },
    { id: 'sector', label: 'Top Sector', value: intelligence.topSector || '—' },
    { id: 'risk', label: 'Risk Level', value: intelligence.risk },
  ];
}
