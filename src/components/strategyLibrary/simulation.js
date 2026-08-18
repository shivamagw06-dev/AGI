/**
 * Deterministic simulation primitives for the Strategy Research Library.
 *
 * Every widget on the page is driven from a seeded generator so a re-render
 * never reshuffles the picture underneath the reader. All output is synthetic
 * and labelled as such at the point of display — none of it is, or is derived
 * from, a real track record.
 */

/** mulberry32 — small, fast, deterministic. */
export function rng(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Box–Muller: standard normal from a uniform generator. */
export function gaussian(next) {
  let u = 0;
  let v = 0;
  while (u === 0) u = next();
  while (v === 0) v = next();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Pre-draw n standard normals so sliders re-use the same shocks. */
export function normals(seed, n) {
  const next = rng(seed);
  return Array.from({ length: n }, () => gaussian(next));
}

export const mean = (xs) => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : 0);

export function stdev(xs) {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  return Math.sqrt(xs.reduce((s, x) => s + (x - m) ** 2, 0) / (xs.length - 1));
}

export function skewness(xs) {
  const n = xs.length;
  if (n < 3) return 0;
  const m = mean(xs);
  const s = stdev(xs);
  if (s === 0) return 0;
  return (n / ((n - 1) * (n - 2))) * xs.reduce((acc, x) => acc + ((x - m) / s) ** 3, 0);
}

export function correlation(a, b) {
  const n = Math.min(a.length, b.length);
  if (n < 2) return 0;
  const ma = mean(a);
  const mb = mean(b);
  let num = 0;
  let da = 0;
  let db = 0;
  for (let i = 0; i < n; i += 1) {
    const x = a[i] - ma;
    const y = b[i] - mb;
    num += x * y;
    da += x * x;
    db += y * y;
  }
  return da > 0 && db > 0 ? num / Math.sqrt(da * db) : 0;
}

/** Compound a return series into an index starting at `base`. */
export function toIndex(returns, base = 100) {
  const out = [base];
  returns.forEach((r) => out.push(out[out.length - 1] * (1 + r)));
  return out;
}

export function maxDrawdown(index) {
  let peak = index[0];
  let worst = 0;
  index.forEach((v) => {
    if (v > peak) peak = v;
    const dd = v / peak - 1;
    if (dd < worst) worst = dd;
  });
  return worst;
}

/** Standard normal pdf. */
export const phi = (x) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

/**
 * Black–Scholes gamma. Used by the volatility-arbitrage widget to weight the
 * variance spread by dollar gamma rather than assuming it constant.
 */
export function bsGamma(S, K, sigma, T, r = 0) {
  if (T <= 0 || sigma <= 0 || S <= 0) return 0;
  const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
  return phi(d1) / (S * sigma * Math.sqrt(T));
}

/** Build an SVG polyline `points` string, mapping data into a viewBox. */
export function points(series, { width, height, pad = 0, min, max }) {
  const lo = min ?? Math.min(...series);
  const hi = max ?? Math.max(...series);
  const span = hi - lo || 1;
  const innerH = height - pad * 2;
  return series
    .map((v, i) => {
      const x = (i / Math.max(1, series.length - 1)) * width;
      const y = pad + innerH - ((v - lo) / span) * innerH;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');
}

/** Map a single value to a y coordinate on the same scale as `points`. */
export function scaleY(v, { height, pad = 0, min, max }) {
  const span = (max - min) || 1;
  const innerH = height - pad * 2;
  return pad + innerH - ((v - min) / span) * innerH;
}

export const pct = (x, dp = 1) => `${(x * 100).toFixed(dp)}%`;
export const fixed = (x, dp = 2) => (Number.isFinite(x) ? x.toFixed(dp) : '—');
