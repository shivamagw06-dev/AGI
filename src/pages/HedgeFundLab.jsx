import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, BrainCircuit, Gauge, Layers, Sigma, Target, Zap } from 'lucide-react';
import HedgeFundTerminal, { InlineAsk } from '@/pages/hedgeFundTerminal';
import {
  getHflCompare,
  getHflStrategies,
  getHflStrategy,
  hflCalculate,
} from '@/lib/intelligenceApi';
import './hedgeFundLab.css';

function fmt(v, digits = 2) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  }
  return String(v);
}

function Stars({ n }) {
  return (
    <span className="hfl-stars" aria-label={`${n} of 5`}>
      {'★'.repeat(n)}
      <span className="dim">{'★'.repeat(Math.max(0, 5 - n))}</span>
    </span>
  );
}

function ExposureLab() {
  const [capital, setCapital] = useState(100);
  const [longBook, setLongBook] = useState(70);
  const [shortBook, setShortBook] = useState(40);
  const [out, setOut] = useState(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    // Do not compete with terminal/strategies on first paint.
    if (!touched) return undefined;
    let live = true;
    hflCalculate('exposure', { capital, long: longBook, short: shortBook })
      .then((res) => { if (live) setOut(res); })
      .catch(() => { if (live) setOut(null); });
    return () => { live = false; };
  }, [capital, longBook, shortBook, touched]);

  const touch = (setter) => (value) => {
    setTouched(true);
    setter(value);
  };

  const sliders = [
    ['Capital (₹ Cr)', capital, touch(setCapital), 10, 500, 10],
    ['Long book (₹ Cr)', longBook, touch(setLongBook), 0, 500, 5],
    ['Short book (₹ Cr)', shortBook, touch(setShortBook), 0, 500, 5],
  ];

  return (
    <section className="hfl-module">
      <h3><Layers size={15} /> Capital allocation &amp; exposure</h3>
      <div className="hfl-lab-grid">
        <div className="hfl-controls">
          {sliders.map(([label, value, setter, min, max, step]) => (
            <label key={label}>
              <span>{label}<b>{value}</b></span>
              <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => setter(Number(e.target.value))}
              />
            </label>
          ))}
        </div>
        <div className="hfl-readout">
          {out?.ok ? (
            <>
              <div className="hfl-rings">
                {[
                  ['Gross', out.gross_pct],
                  ['Net', out.net_pct],
                  ['Long', out.long_pct],
                  ['Short', out.short_pct],
                ].map(([label, pct]) => (
                  <div className="hfl-ring" key={label}>
                    <div
                      className="dial"
                      style={{
                        background: `conic-gradient(var(--hfl-teal) ${Math.min(
                          360,
                          (Math.abs(pct) / 200) * 360
                        )}deg, #e6ecf3 0deg)`,
                      }}
                    >
                      <span>{fmt(pct, 0)}%</span>
                    </div>
                    <div className="cap">{label}</div>
                  </div>
                ))}
              </div>
              <div className="hfl-kv">
                <span>Leverage</span><b>{fmt(out.leverage)}×</b>
                <span>Cash</span><b>{fmt(out.cash_pct, 0)}%</b>
                <span>Profile</span>
                <b>{out.market_neutral ? 'Market neutral' : 'Directional'}</b>
              </div>
            </>
          ) : (
            <p className="hfl-hint">
              {touched ? 'Computing exposure…' : 'Adjust the sliders to compute exposure.'}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

function ExpectancyLab() {
  const [inputs, setInputs] = useState({
    hit_rate_pct: 55,
    avg_win_pct: 6,
    avg_loss_pct: 4,
    trades_per_year: 60,
    leverage: 1.5,
    cost_per_trade_pct: 0.05,
  });
  const [out, setOut] = useState(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (!touched) return undefined;
    let live = true;
    hflCalculate('expectancy', inputs)
      .then((res) => { if (live) setOut(res); })
      .catch(() => { if (live) setOut(null); });
    return () => { live = false; };
  }, [inputs, touched]);

  const fields = [
    ['hit_rate_pct', 'Hit rate %', 20, 80, 1],
    ['avg_win_pct', 'Avg win %', 1, 25, 0.5],
    ['avg_loss_pct', 'Avg loss %', 1, 25, 0.5],
    ['trades_per_year', 'Trades / year', 4, 500, 4],
    ['leverage', 'Leverage', 0.5, 5, 0.1],
    ['cost_per_trade_pct', 'Cost / trade %', 0, 0.5, 0.01],
  ];

  return (
    <section className="hfl-module">
      <h3><Sigma size={15} /> Illustrative strategy expectancy</h3>
      <p className="hfl-hint">User-controlled assumptions, not AGI backtest results. Expectancy does not model correlation, overlapping positions, capacity or tail losses.</p>
      <div className="hfl-lab-grid">
        <div className="hfl-controls">
          {fields.map(([key, label, min, max, step]) => (
            <label key={key}>
              <span>{label}<b>{inputs[key]}</b></span>
              <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={inputs[key]}
                onChange={(e) => {
                  setTouched(true);
                  setInputs((s) => ({ ...s, [key]: Number(e.target.value) }));
                }}
              />
            </label>
          ))}
        </div>
        <div className="hfl-readout">
          {out?.ok ? (
            <>
              <div className="hfl-metrics">
                {[
                  ['Expected return', `${fmt(out.expected_annual_return_pct)}%`],
                  ['Volatility', `${fmt(out.expected_volatility_pct)}%`],
                  ['Sharpe', fmt(out.sharpe)],
                  ['Kelly', fmt(out.kelly_fraction)],
                  ['Half Kelly', fmt(out.half_kelly)],
                  ['Est. max DD', `${fmt(out.estimated_max_drawdown_pct)}%`],
                  ['Profit factor', fmt(out.profit_factor)],
                  ['Breakeven hit rate', `${fmt(out.breakeven_hit_rate_pct, 0)}%`],
                ].map(([label, value]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <b>{value}</b>
                  </div>
                ))}
              </div>
              {out.realism_warning ? (
                <p className="hfl-warn">{out.realism_warning}</p>
              ) : null}
              <p className="hfl-hint">{out.note}</p>
            </>
          ) : (
            <p className="hfl-hint">
              {touched ? 'Computing expectancy…' : 'Set the trade statistics to compute expectancy.'}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

function PairLab() {
  const [spread, setSpread] = useState(2.4);
  const [mean, setMean] = useState(1.8);
  const [std, setStd] = useState(0.25);
  const [out, setOut] = useState(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (!touched) return undefined;
    let live = true;
    hflCalculate('pair_signal', { spread, mean, std })
      .then((res) => { if (live) setOut(res); })
      .catch(() => { if (live) setOut(null); });
    return () => { live = false; };
  }, [spread, mean, std, touched]);

  const touch = (setter) => (value) => {
    setTouched(true);
    setter(value);
  };

  const z = out?.z_score ?? 0;
  const pos = Math.max(0, Math.min(100, ((z + 4) / 8) * 100));

  return (
    <section className="hfl-module">
      <h3><Activity size={15} /> Pair trade / statistical arbitrage</h3>
      <div className="hfl-lab-grid">
        <div className="hfl-controls">
          {[
            ['Current spread', spread, touch(setSpread), 0, 5, 0.05],
            ['Historical mean', mean, touch(setMean), 0, 5, 0.05],
            ['Std deviation', std, touch(setStd), 0.05, 1.5, 0.05],
          ].map(([label, value, setter, min, max, step]) => (
            <label key={label}>
              <span>{label}<b>{value}</b></span>
              <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => setter(Number(e.target.value))}
              />
            </label>
          ))}
        </div>
        <div className="hfl-readout">
          {out?.ok ? (
            <>
              <div className="hfl-zbar">
                <div className="band" />
                <div className="marker" style={{ left: `${pos}%` }}>
                  <span>{fmt(out.z_score)}σ</span>
                </div>
                <div className="labels"><span>−4σ</span><span>0</span><span>+4σ</span></div>
              </div>
              <div className={`hfl-signal ${out.signal}`}>{out.signal.replace('_', ' ')}</div>
              <p className="hfl-hint">{out.action}</p>
            </>
          ) : (
            <p className="hfl-hint">
              {touched ? 'Computing signal…' : 'Move the spread to see the signal.'}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}



export function HedgeFundLabSections() {
  const [strategies, setStrategies] = useState([]);
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const [libraryLoading, setLibraryLoading] = useState(true);

  useEffect(() => {
    let live = true;
    // Stagger after first paint so terminal gets the first engine slot.
    const timer = window.setTimeout(() => {
      Promise.allSettled([getHflStrategies(), getHflCompare()])
        .then(([sRes, cRes]) => {
          if (!live) return;
          const s = sRes.status === 'fulfilled' ? sRes.value : null;
          const c = cRes.status === 'fulfilled' ? cRes.value : null;
          setStrategies(s?.strategies || []);
          setRows(c?.rows || []);
          if (s?.strategies?.length) setSelected(s.strategies[0].id);
          if (!s?.strategies?.length && !c?.rows?.length) {
            setError(
              sRes.reason?.message
              || cRes.reason?.message
              || 'Strategy library unavailable while the intelligence engine recovers.',
            );
          } else {
            setError('');
          }
        })
        .finally(() => {
          if (live) setLibraryLoading(false);
        });
    }, 250);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (!selected) return undefined;
    let live = true;
    setDetail(null);
    getHflStrategy(selected)
      .then((res) => { if (live) setDetail(res); })
      .catch(() => { if (live) setDetail(null); });
    return () => { live = false; };
  }, [selected]);

  const agi = detail?.agi_intelligence;

  return (
    <div className="hfl-root">
      <header className="hfl-header">
        <h1>Hedge Fund</h1>
        <p>Live opportunities, strategy mechanics and institutional risk analytics</p>
        <div className="hfl-focus-links">
          <Link to="/hedge-fund/alpha-opportunities">
            <Target size={16} />
            <span>AGI Alpha</span>
            <strong>Alpha Opportunities</strong>
            <small>Fundamental confluence and research queue</small>
          </Link>
          <a href="#live-strategy-scanners">
            <Zap size={16} />
            <span>Intraday</span>
            <strong>Live Alpha</strong>
            <small>Leadership, activity, breakout, dislocation and positioning</small>
          </a>
          <a href="#forecast-intelligence">
            <BrainCircuit size={16} />
            <span>FIE + FLE</span>
            <strong>Forecast Intelligence</strong>
            <small>Scenario forecasts, outcomes, accuracy and governed learning</small>
          </a>
        </div>
        <InlineAsk />
      </header>

      <main className="hfl-body">
        {error ? <div className="hfl-error">{error}</div> : null}

        <HedgeFundTerminal />

        <h2 className="hfl-section-title">Strategy library — how these strategies work</h2>
        {libraryLoading ? <p className="hfl-hint">Loading strategy library…</p> : null}

        <section className="hfl-cards">
          {strategies.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`hfl-card ${selected === s.id ? 'active' : ''}`}
              onClick={() => setSelected(s.id)}
            >
              <div className="fam">{s.family}</div>
              <div className="name">{s.name}</div>
              <div className="hfl-hint">{s.label || 'Framework'} · {String(s.operational_scope || 'methodology_only').replaceAll('_', ' ')}</div>
              <div className="alpha"><Stars n={s.alpha_rating} /></div>
              <div className="meta">
                <span>Capacity {s.capacity}</span>
                <span>Leverage {s.leverage}</span>
                <span>Risk {s.risk}</span>
              </div>
              <div className="hold">{s.holding_period}</div>
            </button>
          ))}
        </section>

        {detail?.ok ? (
          <>
            <section className="hfl-detail">
              <div className="hfl-detail-head">
                <div>
                  <h2>{detail.name}</h2>
                  <p className="hfl-hint">
                    {detail.alpha_source} · gross {detail.typical_gross} · net {detail.typical_net}
                  </p>
                  <p className="hfl-hint">Qualification: <b>{detail.label || 'Framework'}</b> · {String(detail.operational_scope || 'methodology_only').replaceAll('_', ' ')}</p>
                </div>
                <div className="hfl-users">
                  {detail.top_users.map((u) => <span key={u}>{u}</span>)}
                </div>
              </div>

              <div className="hfl-two">
                <div>
                  <h3>Illustrative AGI strategy attribution</h3>
                  <p className="hfl-hint">Illustrative assumptions, not universal fund return attribution or demonstrated AGI performance.</p>
                  <div className="hfl-revenue">
                    {detail.revenue_sources.map((r) => (
                      <div key={r.source}>
                        <div className="row">
                          <span>{r.source}</span>
                          <b>{r.share}%</b>
                        </div>
                        <div className="track"><div className="fill" style={{ width: `${r.share}%` }} /></div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h3>Strategy flow</h3>
                  <ol className="hfl-flow">
                    {detail.flow.map((step) => <li key={step}>{step}</li>)}
                  </ol>
                </div>
              </div>
              {detail.id === 'equity_market_neutral' ? (
                <p className="hfl-hint">Qualification pipeline: valuation dispersion → economic comparability → correlation → cointegration → factor neutrality → borrow and liquidity → costed backtest → market-neutral candidate.</p>
              ) : null}
            </section>

            <section className="hfl-module">
              <h3>Production qualification</h3>
              <p className="hfl-hint">A framework is not a production engine. Promotion requires every evidence gate below.</p>
              <ol className="hfl-flow">
                {(detail.pipeline || []).map((step) => <li key={step}>{String(step).replaceAll('_', ' ')}</li>)}
              </ol>
            </section>

            {detail.id === 'long_short_equity' && detail.institutional_platform ? (
              <section className="hfl-module">
                <h3>Long/Short institutional readiness</h3>
                <p className="hfl-hint">
                  Lifecycle: <b>{detail.institutional_platform.lifecycle}</b> · Allowed use: {detail.institutional_platform.allowed_use}
                </p>
                <div className="hfl-table-wrap">
                  <table className="hfl-table">
                    <thead><tr><th>Dataset</th><th>Status</th><th>Evidence</th></tr></thead>
                    <tbody>
                      {(detail.institutional_platform.data_foundation || []).map((row) => (
                        <tr key={row.dataset}>
                          <td>{String(row.dataset).replaceAll('_', ' ')}</td>
                          <td><b>{String(row.status).toUpperCase()}</b></td>
                          <td>{row.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="hfl-hint">
                  Execution, position sizing, market-neutral claims and performance claims remain blocked until the validation gates pass.
                </p>
              </section>
            ) : null}

            <section className="hfl-module hfl-agi">
              <h3><Gauge size={15} /> AGI Intelligence</h3>
              <p className="hfl-lead">{agi.why_institutions_use_it}</p>
              <div className="hfl-three">
                {[
                  ['Performs when', agi.when_it_performs],
                  ['Struggles when', agi.when_it_struggles],
                  ['Favourable regimes', agi.favourable_regimes],
                  ['Risk factors', agi.risk_factors],
                  ['Monitored KPIs', agi.monitored_kpis],
                  ['Common mistakes', agi.common_mistakes],
                ].map(([title, items]) => (
                  <div key={title}>
                    <h4>{title}</h4>
                    <ul>{items.map((i) => <li key={i}>{i}</li>)}</ul>
                  </div>
                ))}
              </div>
              <p className="hfl-bottom">{agi.bottom_line}</p>
            </section>
          </>
        ) : null}

        <ExposureLab />
        <ExpectancyLab />
        <PairLab />

        <section className="hfl-module">
          <h3>Strategy comparison</h3>
          <div className="hfl-table-wrap">
            <table className="hfl-table">
              <thead>
                <tr>
                  <th>Strategy</th><th>Alpha source</th><th>Leverage</th>
                  <th>Capacity</th><th>Holding period</th><th>Risk</th><th>Complexity</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.strategy}>
                    <td><strong>{r.strategy}</strong></td>
                    <td>{r.alpha_source}</td>
                    <td>{r.leverage}</td>
                    <td>{r.capacity}</td>
                    <td>{r.holding_period}</td>
                    <td>{r.risk}</td>
                    <td>{r.complexity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <p className="hfl-note">
          Educational strategy mechanics and calculators. Every figure is computed server-side
          from the inputs you set — none of this is investment advice or a recommendation.
        </p>
      </main>
    </div>
  );
}

export default function HedgeFundLab() {
  return <HedgeFundLabSections />;
}
