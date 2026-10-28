/**
 * AGI multi-layer index confluence model.
 *
 * Based on the supplied strategy: three timeframes (Daily / 1h / 15m) and
 * six weighted analytical layers. Scores are internal only; callers should
 * publish derived labels and confidence, never the source OHLCV observations.
 */

const LAYER_WEIGHTS = {
  trend: 0.25,
  momentum: 0.25,
  volatility: 0.15,
  strength: 0.15,
  volume: 0.1,
  structure: 0.1,
};

const TIMEFRAME_WEIGHTS = { long: 0.5, medium: 0.3, short: 0.2 };

const isNumber = (value) => Number.isFinite(value);
const clamp = (value, low = 0, high = 1) => Math.max(low, Math.min(high, value));
const average = (values) => (values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null);

function ema(values, period) {
  if (!values.length) return [];
  const alpha = 2 / (period + 1);
  return values.reduce((series, value, index) => {
    series.push(index ? value * alpha + series[index - 1] * (1 - alpha) : value);
    return series;
  }, []);
}

function wilder(values, period) {
  if (!values.length) return [];
  const alpha = 1 / period;
  return values.reduce((series, value, index) => {
    series.push(index ? value * alpha + series[index - 1] * (1 - alpha) : value);
    return series;
  }, []);
}

function lastSma(values, period) {
  const sample = values.slice(-period);
  return sample.length === period ? average(sample) : null;
}

function lastRsi(closes, period = 14) {
  if (closes.length < period + 1) return null;
  const gains = [0];
  const losses = [0];
  for (let index = 1; index < closes.length; index++) {
    const delta = closes[index] - closes[index - 1];
    gains.push(Math.max(delta, 0));
    losses.push(Math.max(-delta, 0));
  }
  const averageGain = wilder(gains, period).at(-1);
  const averageLoss = wilder(losses, period).at(-1);
  if (!averageLoss) return 100;
  return 100 - 100 / (1 + averageGain / averageLoss);
}

function lastMacd(closes) {
  if (closes.length < 35) return null;
  const fast = ema(closes, 12);
  const slow = ema(closes, 26);
  const line = fast.map((value, index) => value - slow[index]);
  const signal = ema(line, 9);
  const macd = line.at(-1);
  const signalValue = signal.at(-1);
  return { macd, signal: signalValue, histogram: macd - signalValue };
}

function lastStochastic(candles, period = 14) {
  const sample = candles.slice(-period);
  if (sample.length < period) return null;
  const high = Math.max(...sample.map((candle) => candle.high));
  const low = Math.min(...sample.map((candle) => candle.low));
  const range = high - low;
  if (!range) return null;
  const rawK = 100 * (sample.at(-1).close - low) / range;
  const kValues = [];
  for (let index = Math.max(period - 1, 0); index < candles.length; index++) {
    const window = candles.slice(index - period + 1, index + 1);
    const windowHigh = Math.max(...window.map((candle) => candle.high));
    const windowLow = Math.min(...window.map((candle) => candle.low));
    kValues.push(windowHigh === windowLow ? 50 : 100 * (window.at(-1).close - windowLow) / (windowHigh - windowLow));
  }
  const k = average(kValues.slice(-3)) ?? rawK;
  const d = average(kValues.slice(-5, -2)) ?? k;
  return { k, d };
}

function lastBollinger(closes, period = 20) {
  const sample = closes.slice(-period);
  if (sample.length < period) return null;
  const middle = average(sample);
  const std = Math.sqrt(average(sample.map((value) => (value - middle) ** 2)));
  const upper = middle + 2 * std;
  const lower = middle - 2 * std;
  return { pctB: upper === lower ? 0.5 : (closes.at(-1) - lower) / (upper - lower) };
}

function lastAdx(candles, period = 14) {
  if (candles.length < period + 2) return null;
  const tr = [0];
  const plusDm = [0];
  const minusDm = [0];
  for (let index = 1; index < candles.length; index++) {
    const current = candles[index];
    const previous = candles[index - 1];
    const up = current.high - previous.high;
    const down = previous.low - current.low;
    plusDm.push(up > down && up > 0 ? up : 0);
    minusDm.push(down > up && down > 0 ? down : 0);
    tr.push(Math.max(current.high - current.low, Math.abs(current.high - previous.close), Math.abs(current.low - previous.close)));
  }
  const atr = wilder(tr, period);
  const plus = wilder(plusDm, period);
  const minus = wilder(minusDm, period);
  const plusDiSeries = atr.map((value, index) => value ? 100 * plus[index] / value : null);
  const minusDiSeries = atr.map((value, index) => value ? 100 * minus[index] / value : null);
  const dxSeries = plusDiSeries.map((value, index) => {
    const other = minusDiSeries[index];
    return isNumber(value) && isNumber(other) ? 100 * Math.abs(value - other) / (value + other || 1) : 0;
  });
  const plusDi = plusDiSeries.at(-1);
  const minusDi = minusDiSeries.at(-1);
  if (!isNumber(plusDi) || !isNumber(minusDi)) return null;
  const adx = wilder(dxSeries, period).at(-1);
  return { adx, plusDi, minusDi, atrNow: atr.at(-1), atrPrevious: atr.at(-2) };
}

function lastObv(candles) {
  if (!candles.length || !candles.some((candle) => candle.volume > 0)) return null;
  const values = [0];
  for (let index = 1; index < candles.length; index++) {
    const direction = Math.sign(candles[index].close - candles[index - 1].close);
    values.push(values[index - 1] + direction * candles[index].volume);
  }
  return { value: values.at(-1), ema: ema(values, 20).at(-1) };
}

function scoreTrend({ close, sma20, sma50, sma200, ema9, ema21, higherHighs, higherLows }) {
  const scores = [];
  if ([close, sma20, sma50].every(isNumber)) {
    scores.push(close > sma20 && sma20 > sma50 ? 1 : sma20 > sma50 ? 0.75 : close > sma50 ? 0.55 : close > sma20 ? 0.45 : sma20 < sma50 && close < sma20 ? 0 : 0.25);
  }
  if ([close, sma200].every(isNumber) && sma200) {
    const pct = (close - sma200) / sma200 * 100;
    scores.push(pct >= 5 ? 1 : pct >= 2 ? 0.8 : pct >= 0 ? 0.62 : pct >= -2 ? 0.38 : pct >= -5 ? 0.2 : 0);
  }
  if ([ema9, ema21].every(isNumber) && ema21) {
    const gap = (ema9 - ema21) / ema21 * 100;
    scores.push(gap > 0 ? Math.min(1, 0.6 + gap * 0.04) : Math.max(0, 0.4 + gap * 0.04));
  }
  scores.push(higherHighs && higherLows ? 1 : higherHighs || higherLows ? 0.65 : 0.15);
  return average(scores) ?? 0.5;
}

function scoreMomentum({ rsi, macd, roc, stochastic }) {
  const scores = [];
  if (isNumber(rsi)) scores.push(rsi >= 70 ? 0.65 : rsi >= 60 ? 1 : rsi >= 50 ? 0.75 : rsi >= 40 ? 0.4 : rsi >= 30 ? 0.2 : 0.05);
  if (macd && [macd.macd, macd.signal, macd.histogram].every(isNumber)) {
    scores.push(clamp(0.5 + (macd.macd > macd.signal ? 0.25 : -0.25) + (macd.macd > 0 ? 0.15 : -0.15) + (macd.histogram > 0 ? 0.1 : -0.1)));
  }
  if (isNumber(roc)) scores.push(roc >= 3 ? 1 : roc >= 1 ? 0.75 : roc >= 0 ? 0.55 : roc >= -1 ? 0.35 : roc >= -3 ? 0.2 : 0);
  if (stochastic && [stochastic.k, stochastic.d].every(isNumber)) {
    scores.push(stochastic.k > stochastic.d && stochastic.k > 50 ? 1 : stochastic.k > stochastic.d ? 0.65 : stochastic.k > 50 ? 0.55 : stochastic.k < stochastic.d && stochastic.k < 50 ? 0 : 0.35);
  }
  return average(scores) ?? 0.5;
}

function scoreVolatility({ bollinger, adxData, close, sma200 }) {
  const scores = [];
  if (bollinger && isNumber(bollinger.pctB)) scores.push(bollinger.pctB >= 0.8 ? 0.7 : bollinger.pctB >= 0.5 ? 1 : bollinger.pctB >= 0.2 ? 0.35 : 0.1);
  if (adxData && [adxData.atrNow, adxData.atrPrevious, close, sma200].every(isNumber)) {
    const uptrend = close > sma200;
    scores.push(adxData.atrNow > adxData.atrPrevious && uptrend ? 1 : adxData.atrNow <= adxData.atrPrevious && uptrend ? 0.65 : adxData.atrNow > adxData.atrPrevious ? 0.2 : 0.4);
  }
  return average(scores) ?? 0.5;
}

function scoreStrength(adxData) {
  if (!adxData) return 0.5;
  const scores = [];
  if (isNumber(adxData.adx)) scores.push(adxData.adx >= 40 ? 1 : adxData.adx >= 25 ? 0.75 : adxData.adx >= 20 ? 0.55 : 0.25);
  if ([adxData.plusDi, adxData.minusDi].every(isNumber)) {
    const gap = adxData.plusDi - adxData.minusDi;
    scores.push(gap >= 10 ? 1 : gap >= 5 ? 0.8 : gap >= 0 ? 0.6 : gap >= -5 ? 0.35 : gap >= -10 ? 0.2 : 0);
  }
  return average(scores) ?? 0.5;
}

function scoreVolume({ candles, close, sma200, obv }) {
  const scores = [];
  const volume = candles.at(-1)?.volume;
  const volumeAverage = average(candles.slice(-20).map((candle) => candle.volume));
  if ([volume, volumeAverage, close, sma200].every(isNumber) && volumeAverage > 0) {
    const ratio = volume / volumeAverage;
    const uptrend = close > sma200;
    scores.push(ratio >= 1.5 && uptrend ? 1 : ratio >= 1.2 && uptrend ? 0.8 : ratio >= 1 && uptrend ? 0.65 : ratio >= 1.5 ? 0 : ratio >= 1.2 ? 0.2 : 0.4);
  }
  if (obv && [obv.value, obv.ema].every(isNumber)) {
    const gap = (obv.value - obv.ema) / Math.max(Math.abs(obv.ema), 1) * 100;
    scores.push(obv.value > obv.ema ? Math.min(1, 0.6 + gap * 0.02) : Math.max(0, 0.4 + gap * 0.02));
  }
  return average(scores) ?? 0.5;
}

function scoreStructure({ candles, close }) {
  const scores = [];
  const annual = candles.slice(-252);
  if (annual.length && isNumber(close)) {
    const high = Math.max(...annual.map((candle) => candle.high));
    const low = Math.min(...annual.map((candle) => candle.low));
    const position = high === low ? 0.5 : (close - low) / (high - low);
    scores.push(position >= 0.85 ? 1 : position >= 0.65 ? 0.8 : position >= 0.5 ? 0.62 : position >= 0.35 ? 0.4 : position >= 0.15 ? 0.22 : 0.05);
  }
  const prior = candles.slice(-21, -1);
  if (prior.length && isNumber(close)) {
    const high = Math.max(...prior.map((candle) => candle.high));
    const low = Math.min(...prior.map((candle) => candle.low));
    scores.push(close > high ? 1 : close > (high + low) / 2 ? 0.7 : close > low ? 0.4 : 0.05);
  }
  return average(scores) ?? 0.5;
}

export function confluenceLabel(score) {
  if (score >= 80) return 'Strongly Bullish';
  if (score >= 65) return 'Bullish';
  if (score >= 50) return 'Mildly Bullish';
  if (score >= 35) return 'Mildly Bearish';
  if (score >= 20) return 'Bearish';
  return 'Strongly Bearish';
}

export function computeTimeframeConfluence(candles) {
  const clean = candles.filter((candle) => [candle.open, candle.high, candle.low, candle.close].every(isNumber));
  if (clean.length < 60) return null;
  const closes = clean.map((candle) => candle.close);
  const close = closes.at(-1);
  const firstHalf = clean.slice(-20, -10);
  const finalHalf = clean.slice(-10);
  const data = {
    candles: clean,
    close,
    sma20: lastSma(closes, 20),
    sma50: lastSma(closes, 50),
    sma200: lastSma(closes, Math.min(200, closes.length)),
    ema9: ema(closes, 9).at(-1),
    ema21: ema(closes, 21).at(-1),
    higherHighs: finalHalf.length > 0 && firstHalf.length > 0 && Math.max(...finalHalf.map((candle) => candle.high)) > Math.max(...firstHalf.map((candle) => candle.high)),
    higherLows: finalHalf.length > 0 && firstHalf.length > 0 && Math.min(...finalHalf.map((candle) => candle.low)) > Math.min(...firstHalf.map((candle) => candle.low)),
    rsi: lastRsi(closes),
    macd: lastMacd(closes),
    roc: closes.length > 10 ? (close - closes.at(-11)) / closes.at(-11) * 100 : null,
    stochastic: lastStochastic(clean),
    bollinger: lastBollinger(closes),
    adxData: lastAdx(clean),
    obv: lastObv(clean),
  };
  const layers = {
    trend: scoreTrend(data),
    momentum: scoreMomentum(data),
    volatility: scoreVolatility(data),
    strength: scoreStrength(data.adxData),
    volume: scoreVolume(data),
    structure: scoreStructure(data),
  };
  const score = Object.entries(LAYER_WEIGHTS).reduce((sum, [name, weight]) => sum + layers[name] * weight, 0) * 100;
  return { score, label: confluenceLabel(score), layers };
}

/** Combines Daily, 1-hour and 15-minute model outputs into one derived index signal. */
export function computeMultiTimeframeConfluence(timeframes) {
  const entries = Object.entries(timeframes).filter(([, result]) => result?.score != null);
  if (!entries.length) return null;
  const totalWeight = entries.reduce((sum, [key]) => sum + (TIMEFRAME_WEIGHTS[key] || 0), 0);
  const score = entries.reduce((sum, [key, result]) => sum + result.score * (TIMEFRAME_WEIGHTS[key] || 0), 0) / (totalWeight || 1);
  const directions = entries.map(([, result]) => result.score >= 50 ? 'bullish' : 'bearish');
  const agreement = Math.max(directions.filter((direction) => direction === 'bullish').length, directions.filter((direction) => direction === 'bearish').length);
  return {
    label: confluenceLabel(score),
    strength: agreement === 3 ? 'High confidence' : agreement === 2 ? 'Medium confidence' : 'Low confidence',
    score,
  };
}
