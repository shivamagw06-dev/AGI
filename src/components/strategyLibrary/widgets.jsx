import { useMemo, useState, useRef, useCallback } from 'react';
import { Info } from 'lucide-react';
import {
  normals, stdev, skewness, correlation, toIndex, maxDrawdown,
  bsGamma, points, scaleY, pct, fixed, mean,
} from './simulation';

const W = 640;
const H = 190;

/** Illustrative-data notice. Required beneath anything that looks like performance. */
function Illustrative({ children }) {
  return (
    <p className="sl-illus">
      <Info size={11} style={{ verticalAlign: '-1px', marginRight: '0.35rem' }} />
      Illustrative / simulated data. {children}
    </p>
  );
}

function Frame({ children, label }) {
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={label}
         style={{ display: 'block', width: '100%', height: 'auto', overflow: 'visible' }}>
      {children}
    </svg>
  );
}

function Widget({ title, tag, children }) {
  return (
    <div className="sl-widget">
      <div className="sl-widget-head"><b>{title}</b><span>{tag}</span></div>
      {children}
    </div>
  );
}

function Slider({ label, value, display, min, max, step, onChange }) {
  return (
    <div className="sl-control">
      <label>{label} <b>{display}</b></label>
      <input className="sl-range" type="range" min={min} max={max} step={step}
             value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  );
}

/* ==========================================================================
   01 — Long/short beta
   ========================================================================== */
export function BetaWidget() {
  const [wLong, setWLong] = useState(1.0);
  const [wShort, setWShort] = useState(0.7);

  const BETA_L = 1.10;
  const BETA_S = 0.95;
  const N = 260;
  const shocks = useMemo(() => normals(20240517, N * 2), []);

  const model = useMemo(() => {
    const betaP = wLong * BETA_L - wShort * BETA_S;
    const mkt = [];
    const port = [];
    for (let i = 0; i < N; i += 1) {
      const rm = 0.0003 + 0.011 * shocks[i];
      // Idiosyncratic selection return, scaled by gross exposure.
      const alpha = (0.00028 + 0.0045 * shocks[N + i]) * (wLong + wShort) * 0.5;
      mkt.push(rm);
      port.push(alpha + betaP * rm);
    }
    const mIdx = toIndex(mkt);
    const pIdx = toIndex(port);
    return {
      betaP,
      gross: wLong + wShort,
      net: wLong - wShort,
      mIdx,
      pIdx,
      corr: correlation(mkt, port),
      volP: stdev(port) * Math.sqrt(252),
      ddP: maxDrawdown(pIdx),
    };
  }, [wLong, wShort, shocks]);

  const all = [...model.mIdx, ...model.pIdx];
  const scale = { width: W, height: H, pad: 10, min: Math.min(...all), max: Math.max(...all) };

  return (
    <Widget title="Book weights and residual market exposure" tag="Interactive">
      <div className="sl-controls">
        <Slider label="Long book weight" value={wLong} display={`${wLong.toFixed(2)}×`}
                min={0} max={1.5} step={0.05} onChange={setWLong} />
        <Slider label="Short book weight" value={wShort} display={`${wShort.toFixed(2)}×`}
                min={0} max={1.5} step={0.05} onChange={setWShort} />
      </div>

      <Frame label="Simulated portfolio index against the simulated market index">
        <polyline points={points(model.mIdx, scale)} fill="none"
                  stroke="var(--sl-slate)" strokeWidth="1.4" opacity="0.75" />
        <polyline points={points(model.pIdx, scale)} fill="none"
                  stroke="var(--sl-brass)" strokeWidth="1.8" />
      </Frame>
      <div className="sl-legend">
        <span><i style={{ background: 'var(--sl-brass)' }} />Portfolio</span>
        <span><i style={{ background: 'var(--sl-slate)' }} />Market</span>
      </div>

      <div className="sl-readout">
        <div>
          <b className={Math.abs(model.betaP) < 0.1 ? 'pos' : ''}>{fixed(model.betaP)}</b>
          <span>Portfolio β</span>
        </div>
        <div><b>{fixed(model.gross)}×</b><span>Gross</span></div>
        <div><b>{fixed(model.net)}×</b><span>Net</span></div>
        <div><b>{fixed(model.corr)}</b><span>Corr to mkt</span></div>
        <div><b>{pct(model.volP)}</b><span>Ann. vol</span></div>
        <div><b className="neg">{pct(model.ddP)}</b><span>Max DD</span></div>
      </div>

      <Illustrative>
        Betas are held fixed at {BETA_L} long and {BETA_S} short. Real books face beta drift,
        which is why a hedge that computes to zero rarely realises zero.
      </Illustrative>
    </Widget>
  );
}

/* ==========================================================================
   02 — Ornstein–Uhlenbeck spread
   ========================================================================== */
export function OUWidget() {
  const [theta, setTheta] = useState(0.06);
  const [entryZ, setEntryZ] = useState(2);

  const N = 300;
  const shocks = useMemo(() => normals(770311, N), []);

  const model = useMemo(() => {
    const mu = 0;
    const sigma = 0.05;
    const dt = 1;
    const s = [0.14];
    for (let i = 1; i < N; i += 1) {
      const prev = s[i - 1];
      s.push(prev + theta * (mu - prev) * dt + sigma * Math.sqrt(dt) * shocks[i]);
    }
    const sd = stdev(s) || 1;
    const z = s.map((v) => (v - mu) / sd);

    // Walk the z-series and record round trips: enter at |z| > entryZ, exit near 0.
    const trades = [];
    let open = null;
    z.forEach((v, i) => {
      if (!open && Math.abs(v) > entryZ) open = { i, side: v > 0 ? 'short' : 'long', z: v };
      else if (open && Math.abs(v) < 0.25) { trades.push({ ...open, exit: i }); open = null; }
    });

    return { z, sd, halfLife: Math.log(2) / theta, trades };
  }, [theta, entryZ, shocks]);

  const lim = Math.max(3.2, ...model.z.map(Math.abs));
  const scale = { width: W, height: H, pad: 8, min: -lim, max: lim };
  const yFor = (v) => scaleY(v, scale);

  return (
    <Widget title="Simulated cointegrated spread" tag="Interactive">
      <div className="sl-controls">
        <Slider label="Reversion speed θ" value={theta} display={`${theta.toFixed(3)}`}
                min={0.01} max={0.30} step={0.005} onChange={setTheta} />
        <Slider label="Entry threshold |z|" value={entryZ} display={`${entryZ.toFixed(1)}σ`}
                min={1} max={3} step={0.1} onChange={setEntryZ} />
      </div>

      <Frame label="Simulated Ornstein-Uhlenbeck spread in z-score space with entry and exit bands">
        {/* Entry bands */}
        <rect x="0" y={yFor(lim)} width={W} height={Math.max(0, yFor(entryZ) - yFor(lim))}
              fill="var(--sl-oxide)" opacity="0.10" />
        <rect x="0" y={yFor(-entryZ)} width={W} height={Math.max(0, yFor(-lim) - yFor(-entryZ))}
              fill="var(--sl-oxide)" opacity="0.10" />
        {/* Exit band */}
        <rect x="0" y={yFor(0.25)} width={W} height={Math.max(0, yFor(-0.25) - yFor(0.25))}
              fill="var(--sl-brass)" opacity="0.16" />
        <line x1="0" y1={yFor(0)} x2={W} y2={yFor(0)} stroke="var(--sl-line-strong)" strokeWidth="1" />
        <line x1="0" y1={yFor(entryZ)} x2={W} y2={yFor(entryZ)}
              stroke="var(--sl-oxide)" strokeWidth="1" strokeDasharray="3 3" opacity="0.8" />
        <line x1="0" y1={yFor(-entryZ)} x2={W} y2={yFor(-entryZ)}
              stroke="var(--sl-oxide)" strokeWidth="1" strokeDasharray="3 3" opacity="0.8" />
        <polyline points={points(model.z, scale)} fill="none" stroke="var(--sl-paper)" strokeWidth="1.3" />
        {model.trades.map((t) => (
          <g key={`${t.i}-${t.exit}`}>
            <circle cx={(t.i / (N - 1)) * W} cy={yFor(t.z)} r="3.2" fill="var(--sl-oxide)" />
            <circle cx={(t.exit / (N - 1)) * W} cy={yFor(model.z[t.exit])} r="3.2" fill="var(--sl-brass)" />
          </g>
        ))}
      </Frame>
      <div className="sl-legend">
        <span><i style={{ background: 'var(--sl-oxide)' }} />Entry |z| &gt; {entryZ.toFixed(1)}</span>
        <span><i style={{ background: 'var(--sl-brass)' }} />Exit z ≈ 0</span>
      </div>

      <div className="sl-readout">
        <div><b>{fixed(model.halfLife, 1)}</b><span>Half-life (days)</span></div>
        <div><b>{model.trades.length}</b><span>Round trips</span></div>
        <div><b>{fixed(theta, 3)}</b><span>θ</span></div>
      </div>

      <Illustrative>
        Raising θ shortens the half-life and produces more round trips — but each one earns a
        smaller spread while paying the same costs.
      </Illustrative>
    </Widget>
  );
}

/* ==========================================================================
   03 — Merger arbitrage calculator
   ========================================================================== */
export function MergerWidget() {
  const [K, setK] = useState(85);
  const [P, setP] = useState(81.4);
  const [D, setD] = useState(62);
  const [days, setDays] = useState(120);

  const r = useMemo(() => {
    const valid = K > 0 && P > 0 && days > 0 && K > D && P >= D && P <= K;
    if (!valid) return { valid: false };
    const spread = (K - P) / P;
    const ann = (K / P) ** (365 / days) - 1;
    const implied = (P - D) / (K - D);
    const downside = D / P - 1;
    // Breakeven probability at which expected value equals today's price.
    return { valid: true, spread, ann, implied, downside, ev: implied * K + (1 - implied) * D };
  }, [K, P, D, days]);

  const field = (label, value, onChange, step = 0.1) => (
    <div className="sl-field">
      <label htmlFor={`ma-${label}`}>{label}</label>
      <input id={`ma-${label}`} type="number" step={step} value={value}
             onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  );

  return (
    <Widget title="Deal calculator" tag="Interactive">
      <div className="sl-grid-2">
        {field('Offer price K', K, setK)}
        {field('Current price P', P, setP)}
        {field('Downside D', D, setD)}
        {field('Days to close', days, setDays, 1)}
      </div>

      {!r.valid ? (
        <p className="sl-agi-empty" style={{ marginTop: '1rem' }}>
          Requires D ≤ P ≤ K and days &gt; 0.
        </p>
      ) : (
        <div className="sl-readout">
          <div><b className="pos">{pct(r.spread, 2)}</b><span>Gross spread</span></div>
          <div><b className="pos">{pct(r.ann, 1)}</b><span>Annualised</span></div>
          <div><b>{pct(r.implied, 0)}</b><span>Implied p</span></div>
          <div><b className="neg">{pct(r.downside, 1)}</b><span>If it breaks</span></div>
        </div>
      )}

      <Illustrative>
        Implied probability inverts the two-point payoff and assumes risk neutrality and a
        known downside price. Both assumptions are convenient rather than true.
      </Illustrative>
    </Widget>
  );
}

/* ==========================================================================
   04 — Delta-hedged gamma P&L
   ========================================================================== */
export function GammaWidget() {
  const [regime, setRegime] = useState('rich'); // realised above or below implied

  const N = 180;
  const shocks = useMemo(() => normals(20180205, N), []);

  const model = useMemo(() => {
    const impliedVol = 0.20;
    const realisedVol = regime === 'rich' ? 0.30 : 0.12;
    const dt = 1 / 252;
    const K = 100;
    const T0 = N / 252;

    let S = 100;
    let cum = 0;
    const path = [S];
    const pnl = [0];

    for (let i = 0; i < N; i += 1) {
      const tau = Math.max(T0 - i * dt, 1 / 252);
      const gamma = bsGamma(S, K, impliedVol, tau);
      const dS = S * realisedVol * Math.sqrt(dt) * shocks[i];
      // Discrete form of ½Γ S²(σ²_real − σ²_imp) dt, using the actual squared move.
      cum += 0.5 * gamma * (dS * dS - impliedVol * impliedVol * S * S * dt);
      S += dS;
      path.push(S);
      pnl.push(cum);
    }
    return { path, pnl, realisedVol, impliedVol, final: cum };
  }, [regime, shocks]);

  const pScale = { width: W, height: 70, pad: 6, min: Math.min(...model.path), max: Math.max(...model.path) };
  const lo = Math.min(0, ...model.pnl);
  const hi = Math.max(0, ...model.pnl);
  const lScale = { width: W, height: 100, pad: 6, min: lo, max: hi };

  return (
    <Widget title="Delta-hedged position" tag="Interactive">
      <div className="sl-cta-row" style={{ marginTop: 0, marginBottom: '1.1rem' }}>
        <button type="button" className={`sl-btn ${regime === 'rich' ? 'sl-btn-primary' : ''}`}
                onClick={() => setRegime('rich')} aria-pressed={regime === 'rich'}>
          Realised &gt; implied
        </button>
        <button type="button" className={`sl-btn ${regime === 'cheap' ? 'sl-btn-primary' : ''}`}
                onClick={() => setRegime('cheap')} aria-pressed={regime === 'cheap'}>
          Realised &lt; implied
        </button>
      </div>

      <div style={{ fontFamily: 'var(--sl-mono)', fontSize: '0.63rem', letterSpacing: '0.09em',
                    textTransform: 'uppercase', color: 'var(--sl-dimmer)', marginBottom: '0.3rem' }}>
        Underlying
      </div>
      <svg viewBox={`0 0 ${W} 70`} width="100%"            role="img" aria-label="Simulated underlying price path" style={{ display: 'block', width: '100%', height: 'auto' }}>
        <polyline points={points(model.path, pScale)} fill="none" stroke="var(--sl-slate)" strokeWidth="1.3" />
      </svg>

      <div style={{ fontFamily: 'var(--sl-mono)', fontSize: '0.63rem', letterSpacing: '0.09em',
                    textTransform: 'uppercase', color: 'var(--sl-dimmer)', margin: '0.8rem 0 0.3rem' }}>
        Cumulative hedged P&amp;L
      </div>
      <svg viewBox={`0 0 ${W} 100`} width="100%"            role="img" aria-label="Cumulative delta-hedged profit and loss" style={{ display: 'block', width: '100%', height: 'auto' }}>
        <line x1="0" y1={scaleY(0, lScale)} x2={W} y2={scaleY(0, lScale)}
              stroke="var(--sl-line-strong)" strokeWidth="1" />
        <polyline points={points(model.pnl, lScale)} fill="none"
                  stroke={model.final >= 0 ? 'var(--sl-brass)' : 'var(--sl-oxide)'} strokeWidth="1.8" />
      </svg>

      <div className="sl-readout">
        <div><b>{pct(model.impliedVol, 0)}</b><span>Implied σ</span></div>
        <div><b>{pct(model.realisedVol, 0)}</b><span>Realised σ</span></div>
        <div>
          <b className={model.final >= 0 ? 'pos' : 'neg'}>{model.final >= 0 ? '+' : ''}{fixed(model.final, 1)}</b>
          <span>P&amp;L per unit γ</span>
        </div>
      </div>

      <Illustrative>
        Both paths use the same random shocks, scaled to different realised volatilities, so the
        difference you see is the variance spread and not a different draw.
      </Illustrative>
    </Widget>
  );
}

/* ==========================================================================
   05 — Yield curve butterfly
   ========================================================================== */
export function CurveWidget() {
  const [belly, setBelly] = useState(4.35);
  const [shift, setShift] = useState(0);

  const BASE = { 2: 4.10, 5: 4.35, 10: 4.62 };
  const DUR = { 2: 1.90, 5: 4.55, 10: 8.20 };

  const r = useMemo(() => {
    const y2 = BASE[2] + shift / 100;
    const y10 = BASE[10] + shift / 100;
    const y5 = belly + shift / 100;

    // Duration-neutral fly: long 1 unit of the belly, short wings split 50/50 by DV01.
    const w2 = (DUR[5] * 0.5) / DUR[2];
    const w10 = (DUR[5] * 0.5) / DUR[10];

    const dy2 = y2 - BASE[2];
    const dy5 = y5 - BASE[5];
    const dy10 = y10 - BASE[10];

    // δP/P ≈ −D·δy per leg; long belly, short wings.
    const pnl = (-DUR[5] * dy5 + w2 * DUR[2] * dy2 + w10 * DUR[10] * dy10) / 100;

    const flyBase = 2 * BASE[5] - BASE[2] - BASE[10];
    const flyNow = 2 * y5 - y2 - y10;

    return { y2, y5, y10, w2, w10, pnl, flyChange: (flyNow - flyBase) * 100 };
  }, [belly, shift]);

  const pts = [{ t: 2, y: r.y2 }, { t: 5, y: r.y5 }, { t: 10, y: r.y10 }];
  const yMin = 3.6;
  const yMax = 5.2;
  const cx = (t) => ((Math.log(t) - Math.log(2)) / (Math.log(10) - Math.log(2))) * (W - 60) + 30;
  const cy = (y) => 20 + (1 - (y - yMin) / (yMax - yMin)) * (H - 45);

  return (
    <Widget title="Duration-neutral butterfly" tag="Interactive">
      <div className="sl-controls">
        <Slider label="5-year yield (belly)" value={belly} display={`${belly.toFixed(2)}%`}
                min={3.9} max={4.9} step={0.01} onChange={setBelly} />
        <Slider label="Parallel shift (all tenors)" value={shift}
                display={`${shift > 0 ? '+' : ''}${shift} bp`}
                min={-50} max={50} step={1} onChange={setShift} />
      </div>

      <Frame label="Yield curve with draggable belly and resulting butterfly profit and loss">
        <polyline points={pts.map((p) => `${cx(p.t)},${cy(p.y)}`).join(' ')}
                  fill="none" stroke="var(--sl-brass)" strokeWidth="1.8" />
        <polyline points={[[2, BASE[2]], [5, BASE[5]], [10, BASE[10]]]
                    .map(([t, y]) => `${cx(t)},${cy(y + shift / 100)}`).join(' ')}
                  fill="none" stroke="var(--sl-slate)" strokeWidth="1.2"
                  strokeDasharray="4 4" opacity="0.7" />
        {pts.map((p) => (
          <g key={p.t}>
            <circle cx={cx(p.t)} cy={cy(p.y)} r={p.t === 5 ? 6 : 4.5}
                    fill={p.t === 5 ? 'var(--sl-brass)' : 'var(--sl-slate)'} />
            <text x={cx(p.t)} y={H - 6} textAnchor="middle"
                  fill="var(--sl-dimmer)" fontSize="11" fontFamily="var(--sl-mono)">{p.t}y</text>
            <text x={cx(p.t)} y={cy(p.y) - 13} textAnchor="middle"
                  fill="var(--sl-paper)" fontSize="11" fontFamily="var(--sl-mono)">{p.y.toFixed(2)}</text>
          </g>
        ))}
      </Frame>
      <div className="sl-legend">
        <span><i style={{ background: 'var(--sl-brass)' }} />Current curve</span>
        <span><i style={{ background: 'var(--sl-slate)' }} />Base (shifted)</span>
      </div>

      <div className="sl-readout">
        <div>
          <b className={r.pnl >= 0 ? 'pos' : 'neg'}>{r.pnl >= 0 ? '+' : ''}{pct(r.pnl, 2)}</b>
          <span>Fly P&amp;L</span>
        </div>
        <div><b>{r.flyChange >= 0 ? '+' : ''}{fixed(r.flyChange, 1)}</b><span>Fly Δ (bp)</span></div>
        <div><b>{fixed(r.w2)}×</b><span>2y weight</span></div>
        <div><b>{fixed(r.w10)}×</b><span>10y weight</span></div>
      </div>

      <Illustrative>
        Move the parallel shift alone and P&amp;L stays near zero — that is duration neutrality
        working. Move only the belly and the position pays, because curvature is the actual view.
      </Illustrative>
    </Widget>
  );
}

/* ==========================================================================
   06 — Trend following
   ========================================================================== */
export function TrendWidget() {
  const [lookback, setLookback] = useState(60);
  const [volTarget, setVolTarget] = useState(0.12);

  const N = 900;
  const shocks = useMemo(() => normals(20081015, N), []);

  const model = useMemo(() => {
    // Regime-switching drift: sustained trends punctuated by long choppy stretches.
    const drift = (i) => {
      const cycle = Math.floor(i / 150) % 4;
      if (cycle === 0) return 0.0009;
      if (cycle === 1) return -0.0011;
      if (cycle === 2) return 0.00005;
      return 0.0007;
    };

    const prices = [100];
    const rets = [];
    for (let i = 0; i < N; i += 1) {
      const r = drift(i) + 0.012 * shocks[i];
      rets.push(r);
      prices.push(prices[prices.length - 1] * (1 + r));
    }

    const stratRets = [];
    for (let i = lookback; i < N; i += 1) {
      const sig = Math.sign(prices[i] / prices[i - lookback] - 1);
      const window = rets.slice(Math.max(0, i - 60), i);
      const vol = stdev(window) * Math.sqrt(252) || 0.15;
      const w = Math.max(-3, Math.min(3, (sig * volTarget) / vol));
      stratRets.push(w * rets[i]);
    }

    const idx = toIndex(stratRets);
    const bh = toIndex(rets.slice(lookback));
    const monthly = [];
    for (let i = 0; i + 21 <= stratRets.length; i += 21) {
      monthly.push(stratRets.slice(i, i + 21).reduce((s, x) => s + x, 0));
    }
    return {
      idx, bh, monthly,
      skew: skewness(monthly),
      hit: monthly.filter((m) => m > 0).length / Math.max(1, monthly.length),
      dd: maxDrawdown(idx),
      vol: stdev(stratRets) * Math.sqrt(252),
    };
  }, [lookback, volTarget, shocks]);

  const all = [...model.idx, ...model.bh];
  const scale = { width: W, height: 130, pad: 8, min: Math.min(...all), max: Math.max(...all) };
  const mLo = Math.min(...model.monthly);
  const mHi = Math.max(...model.monthly);
  const mSpan = Math.max(Math.abs(mLo), Math.abs(mHi)) || 1;

  return (
    <Widget title="Vol-targeted trend model" tag="Interactive">
      <div className="sl-controls">
        <Slider label="Lookback window" value={lookback} display={`${lookback} sessions`}
                min={20} max={200} step={5} onChange={setLookback} />
        <Slider label="Volatility target" value={volTarget} display={pct(volTarget, 0)}
                min={0.05} max={0.25} step={0.01} onChange={setVolTarget} />
      </div>

      <svg viewBox={`0 0 ${W} 130`} width="100%"            role="img" aria-label="Simulated trend strategy against buy and hold" style={{ display: 'block', width: '100%', height: 'auto' }}>
        <polyline points={points(model.bh, scale)} fill="none" stroke="var(--sl-slate)"
                  strokeWidth="1.3" opacity="0.7" />
        <polyline points={points(model.idx, scale)} fill="none" stroke="var(--sl-brass)" strokeWidth="1.8" />
      </svg>
      <div className="sl-legend">
        <span><i style={{ background: 'var(--sl-brass)' }} />Trend model</span>
        <span><i style={{ background: 'var(--sl-slate)' }} />Underlying</span>
      </div>

      <div style={{ fontFamily: 'var(--sl-mono)', fontSize: '0.63rem', letterSpacing: '0.09em',
                    textTransform: 'uppercase', color: 'var(--sl-dimmer)', margin: '0.9rem 0 0.3rem' }}>
        Monthly returns — note the right tail
      </div>
      <svg viewBox={`0 0 ${W} 56`} width="100%"            role="img" aria-label="Distribution of simulated monthly returns" style={{ display: 'block', width: '100%', height: 'auto' }}>
        <line x1="0" y1="28" x2={W} y2="28" stroke="var(--sl-line-strong)" strokeWidth="1" />
        {model.monthly.map((m, i) => {
          const bw = W / Math.max(1, model.monthly.length);
          const h = (Math.abs(m) / mSpan) * 26;
          return (
            <rect key={i} x={i * bw + bw * 0.15} width={Math.max(1, bw * 0.7)}
                  y={m >= 0 ? 28 - h : 28} height={Math.max(1, h)}
                  fill={m >= 0 ? 'var(--sl-brass)' : 'var(--sl-oxide)'} opacity="0.85" />
          );
        })}
      </svg>

      <div className="sl-readout">
        <div><b className={model.skew >= 0 ? 'pos' : 'neg'}>{fixed(model.skew)}</b><span>Skew</span></div>
        <div><b>{pct(model.hit, 0)}</b><span>Hit rate</span></div>
        <div><b>{pct(model.vol, 0)}</b><span>Ann. vol</span></div>
        <div><b className="neg">{pct(model.dd)}</b><span>Max DD</span></div>
      </div>

      <Illustrative>
        A hit rate near or below half with positive skew is the signature of the style: many small
        losses funding a few large gains. It is not a defect to be optimised away.
      </Illustrative>
    </Widget>
  );
}

/* ==========================================================================
   07 — Capital structure waterfall
   ========================================================================== */
export function WaterfallWidget() {
  const [ev, setEv] = useState(620);

  const TRANCHES = [
    { name: 'Secured / revolver', face: 250, price: 0.97 },
    { name: 'Senior unsecured', face: 400, price: 0.72 },
    { name: 'Subordinated notes', face: 200, price: 0.28 },
    { name: 'Preferred equity', face: 120, price: 0.06 },
    { name: 'Common equity', face: 0, price: 0 },
  ];

  const rows = useMemo(() => {
    let remaining = ev;
    let fulcrumFound = false;
    return TRANCHES.map((t) => {
      if (t.face === 0) {
        const residual = Math.max(0, remaining);
        return { ...t, recovery: residual, ratio: null, residual: true, fulcrum: false };
      }
      const recovery = Math.max(0, Math.min(t.face, remaining));
      remaining -= recovery;
      const ratio = recovery / t.face;
      const isFulcrum = !fulcrumFound && ratio > 0 && ratio < 1;
      if (isFulcrum) fulcrumFound = true;
      return { ...t, recovery, ratio, residual: false, fulcrum: isFulcrum };
    });
  }, [ev]);

  const totalFace = TRANCHES.reduce((s, t) => s + t.face, 0);

  return (
    <Widget title="Recovery waterfall" tag="Interactive">
      <div className="sl-controls">
        <Slider label="Enterprise value at emergence" value={ev} display={`$${ev}m`}
                min={0} max={1100} step={10} onChange={setEv} />
      </div>

      <svg viewBox="0 0 640 230" width="100%" role="img"
           aria-label="Capital structure seniority waterfall showing recovery by tranche"
           style={{ display: 'block', width: '100%', height: 'auto' }}>
        {rows.map((t, i) => {
          const y = i * 44 + 4;
          const barW = t.residual ? (t.recovery / 400) * 380 : (t.face / totalFace) * 380 * 2.4;
          const fillW = t.residual ? barW : barW * (t.ratio ?? 0);
          return (
            <g key={t.name}>
              <text x="0" y={y + 20} fill="var(--sl-paper)" fontSize="12"
                    fontFamily="var(--sl-body)">{t.name}</text>
              <rect x="205" y={y + 6} width={Math.max(0, barW)} height="22"
                    fill="none" stroke="var(--sl-line-strong)" strokeWidth="1" />
              <rect x="205" y={y + 6} width={Math.max(0, fillW)} height="22"
                    fill={t.fulcrum ? 'var(--sl-brass)' : (t.ratio === 1 || t.residual ? 'var(--sl-slate)' : 'var(--sl-oxide)')}
                    opacity={t.recovery > 0 ? 0.85 : 0.25} />
              <text x="600" y={y + 21} textAnchor="end" fill="var(--sl-paper)"
                    fontSize="11.5" fontFamily="var(--sl-mono)">
                {t.residual ? `$${t.recovery.toFixed(0)}m` : `${(t.ratio * 100).toFixed(0)}%`}
              </text>
              {t.fulcrum ? (
                <text x="205" y={y + 41} fill="var(--sl-brass)" fontSize="9.5"
                      fontFamily="var(--sl-mono)" letterSpacing="0.1em">FULCRUM SECURITY</text>
              ) : null}
            </g>
          );
        })}
      </svg>

      <Illustrative>
        The fulcrum security — highlighted — is the tranche that breaks, and therefore the one
        that converts to equity and controls the reorganisation. Move enterprise value and watch
        it migrate up and down the structure.
      </Illustrative>
    </Widget>
  );
}

/* ==========================================================================
   08 — Platform diversification
   ========================================================================== */
export function PodsWidget() {
  const [n, setN] = useState(10);
  const [s, setS] = useState(0.5);
  const [rho, setRho] = useState(0.15);

  const N_DAYS = 500;
  const shocks = useMemo(() => normals(31415926, N_DAYS * 41), []);

  const model = useMemo(() => {
    const naive = s * Math.sqrt(n);
    const real = (s * Math.sqrt(n)) / Math.sqrt(1 + (n - 1) * rho);

    const dailyVol = 0.01;
    const drift = (sh) => (sh * dailyVol) / Math.sqrt(252);

    const platform = [];
    const single = [];
    for (let d = 0; d < N_DAYS; d += 1) {
      const common = shocks[d * 41];
      let agg = 0;
      for (let p = 0; p < n; p += 1) {
        const idio = shocks[d * 41 + 1 + (p % 40)];
        // Correlated pod return: shared component weighted by √ρ.
        const shock = Math.sqrt(rho) * common + Math.sqrt(Math.max(0, 1 - rho)) * idio;
        agg += drift(shock) + (s * dailyVol) / 252;
      }
      platform.push(agg / n);
      single.push(drift(shocks[d * 41 + 1]) + (s * dailyVol) / 252);
    }
    return {
      naive, real,
      pIdx: toIndex(platform), sIdx: toIndex(single),
      benefit: real / Math.max(s, 0.0001),
    };
  }, [n, s, rho, shocks]);

  const all = [...model.pIdx, ...model.sIdx];
  const scale = { width: W, height: 120, pad: 8, min: Math.min(...all), max: Math.max(...all) };

  return (
    <Widget title="Diversification arithmetic" tag="Interactive">
      <div className="sl-controls">
        <Slider label="Number of pods (N)" value={n} display={`${n}`}
                min={1} max={40} step={1} onChange={setN} />
        <Slider label="Per-pod Sharpe (S)" value={s} display={s.toFixed(2)}
                min={0.1} max={1.5} step={0.05} onChange={setS} />
        <Slider label="Average pairwise correlation (ρ)" value={rho} display={rho.toFixed(2)}
                min={0} max={0.6} step={0.01} onChange={setRho} />
      </div>

      <svg viewBox={`0 0 ${W} 120`} width="100%"            role="img" aria-label="Simulated platform equity curve against a single pod" style={{ display: 'block', width: '100%', height: 'auto' }}>
        <polyline points={points(model.sIdx, scale)} fill="none" stroke="var(--sl-slate)"
                  strokeWidth="1.3" opacity="0.75" />
        <polyline points={points(model.pIdx, scale)} fill="none" stroke="var(--sl-brass)" strokeWidth="1.8" />
      </svg>
      <div className="sl-legend">
        <span><i style={{ background: 'var(--sl-brass)' }} />Platform (N pods)</span>
        <span><i style={{ background: 'var(--sl-slate)' }} />Single pod</span>
      </div>

      <div className="sl-readout">
        <div><b>{fixed(model.naive)}</b><span>S√N (ρ=0)</span></div>
        <div><b className="pos">{fixed(model.real)}</b><span>Actual Sharpe</span></div>
        <div><b>{fixed(model.benefit)}×</b><span>vs one pod</span></div>
      </div>

      <Illustrative>
        Push ρ above roughly 0.2 and adding pods stops helping — the two Sharpe figures diverge
        sharply. That gap is the entire argument for enforcing genuine independence between teams.
      </Illustrative>
    </Widget>
  );
}

export const WIDGETS = {
  beta: BetaWidget,
  ou: OUWidget,
  merger: MergerWidget,
  gamma: GammaWidget,
  curve: CurveWidget,
  trend: TrendWidget,
  waterfall: WaterfallWidget,
  pods: PodsWidget,
};
