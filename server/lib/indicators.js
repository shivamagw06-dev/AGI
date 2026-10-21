/** Pure-math technical indicators — deterministic, no AI */

export function emaSeries(values, period) {
  if (!values?.length || period < 1) return [];
  const k = 2 / (period + 1);
  const out = [values[0]];
  for (let i = 1; i < values.length; i++) {
    out.push(values[i] * k + out[i - 1] * (1 - k));
  }
  return out;
}

export function lastEma(values, period) {
  const s = emaSeries(values, period);
  return s.length ? s[s.length - 1] : null;
}

export function rsi(closes, period = 14) {
  if (!closes || closes.length < period + 1) return null;
  let gains = 0;
  let losses = 0;
  for (let i = closes.length - period; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }
  const avgGain = gains / period;
  const avgLoss = losses / period;
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function macd(closes, fast = 12, slow = 26, signal = 9) {
  if (!closes || closes.length < slow + signal) return null;
  const emaFast = emaSeries(closes, fast);
  const emaSlow = emaSeries(closes, slow);
  const macdLine = emaFast.map((v, i) => v - emaSlow[i]);
  const signalLine = emaSeries(macdLine.slice(slow - 1), signal);
  const macdVal = macdLine[macdLine.length - 1];
  const signalVal = signalLine[signalLine.length - 1];
  return {
    macd: macdVal,
    signal: signalVal,
    histogram: macdVal - signalVal,
    bullish: macdVal > signalVal,
  };
}

export function atr(candles, period = 14) {
  if (!candles || candles.length < period + 1) return null;
  const trs = [];
  for (let i = 1; i < candles.length; i++) {
    const h = candles[i].high;
    const l = candles[i].low;
    const pc = candles[i - 1].close;
    trs.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
  }
  const slice = trs.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / slice.length;
}

/** Simplified ADX approximation from ATR and directional movement */
export function adx(candles, period = 14) {
  if (!candles || candles.length < period + 2) return null;
  let plusDm = 0;
  let minusDm = 0;
  for (let i = candles.length - period; i < candles.length; i++) {
    const up = candles[i].high - candles[i - 1].high;
    const down = candles[i - 1].low - candles[i].low;
    plusDm += up > down && up > 0 ? up : 0;
    minusDm += down > up && down > 0 ? down : 0;
  }
  const a = atr(candles, period);
  if (!a) return null;
  const plusDi = (100 * plusDm) / (period * a);
  const minusDi = (100 * minusDm) / (period * a);
  const dx = (100 * Math.abs(plusDi - minusDi)) / (plusDi + minusDi || 1);
  return dx;
}

export function roc(closes, period = 10) {
  if (!closes || closes.length <= period) return null;
  const curr = closes[closes.length - 1];
  const prev = closes[closes.length - 1 - period];
  if (!prev) return null;
  return ((curr - prev) / prev) * 100;
}

/** Normalize Groww candle arrays [ts, o, h, l, c, v] */
export function normalizeCandles(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((c) => {
      if (Array.isArray(c)) {
        return { open: c[1], high: c[2], low: c[3], close: c[4], volume: c[5] || 0 };
      }
      return {
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: c.volume || 0,
      };
    })
    .filter((c) => Number.isFinite(c.close));
}

export function closesFromCandles(candles) {
  return candles.map((c) => c.close);
}
