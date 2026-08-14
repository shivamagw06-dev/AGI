import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Beaker, Database, Pause, Play, RefreshCw, ShieldCheck } from 'lucide-react';
import { getStrategyLabDashboard, getStrategyLabHealth, getStrategyLabScan, runStrategyLabBacktest } from '@/lib/strategyLabApi';
import './StrategyLab.css';

const SIGNAL_ORDER = { BUY: 1, SELL: 2, EXIT: 3, HOLD: 4 };

function fmt(value, digits = 2) {
  if (value == null || value === '') return '—';
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString('en-IN', { maximumFractionDigits: digits }) : '—';
}

function Status({ children, tone = '' }) {
  return <span className={`sl-status ${tone}`}>{children}</span>;
}

export default function StrategyLab() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [selected, setSelected] = useState('time_series_momentum');
  const [scan, setScan] = useState(null);
  const [backtest, setBacktest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [h, d] = await Promise.all([getStrategyLabHealth(), getStrategyLabDashboard(5)]);
      setHealth(h); setDashboard(d);
    } catch (err) { setError(err?.message || 'Strategy Lab unavailable'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  const strategies = dashboard?.strategies || [];
  const current = strategies.find((item) => item.strategy_id === selected) || strategies[0];
  const signals = useMemo(() => [...(scan?.signals || current?.signals || [])].sort((a, b) => (SIGNAL_ORDER[a.signal] || 9) - (SIGNAL_ORDER[b.signal] || 9)), [scan, current]);

  const runScan = async () => {
    setBusy('scan'); setError('');
    try { setScan(await getStrategyLabScan(selected, 30)); }
    catch (err) { setError(err?.message || 'Scan failed'); }
    finally { setBusy(''); }
  };
  const runBacktest = async () => {
    setBusy('backtest'); setError(''); setBacktest(null);
    try { setBacktest(await runStrategyLabBacktest(selected, { one_way_cost_bps: 25, holdings: 20 })); }
    catch (err) { setError(err?.message || 'Backtest failed'); }
    finally { setBusy(''); }
  };

  return (
    <div className="sl-root">
      <header className="sl-header">
        <div>
          <p><Beaker size={14} /> AGI internal systematic research</p>
          <h1>Strategy Lab</h1>
          <div className="sl-meta"><Status tone="restricted">ADMIN ONLY</Status><Status>PHASE 1</Status><span>Version {dashboard?.version || health?.version || '—'}</span><span>Execution blocked</span></div>
        </div>
        <div className="sl-actions">
          <button onClick={load} disabled={loading} title="Refresh Strategy Lab"><RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh</button>
          <button onClick={runScan} disabled={!!busy || !current}><Play size={16} /> Run current scan</button>
          <button onClick={runBacktest} disabled={!!busy || !current}><Activity size={16} /> Backtest</button>
          <button disabled title="Promotion gates have not passed"><Pause size={16} /> Deploy blocked</button>
        </div>
      </header>

      {error ? <div className="sl-alert"><AlertTriangle size={17} /><span>{error}</span></div> : null}

      <div className="sl-workspace">
        <aside className="sl-sidebar">
          <div className="sl-sidebar-title"><span>Strategy library</span><b>{strategies.length}</b></div>
          <nav>
            {strategies.map((item) => (
              <button key={item.strategy_id} className={selected === item.strategy_id ? 'active' : ''} onClick={() => { setSelected(item.strategy_id); setScan(null); setBacktest(null); }}>
                <strong>{item.name}</strong><span>{item.family} · {item.version}</span><small><i>{item.lifecycle}</i><em>{item.universe || 0} eligible</em></small>
              </button>
            ))}
          </nav>
          <div className="sl-data"><Database size={15} /><div><strong>Warehouse source</strong><span>Adjusted daily OHLCV</span><span>PIT status: PIT_LIMITED</span></div></div>
        </aside>

        <main className="sl-main">
          {current ? <>
            <section className="sl-strategy-head">
              <div><span className="sl-kicker">{current.family}</span><h2>{current.name}</h2><p>{current.formula}</p></div>
              <div className="sl-head-status"><Status>{current.lifecycle}</Status><Status tone="research">RESEARCH ONLY</Status><span>As of {current.as_of || '—'}</span></div>
            </section>

            {current.overlap ? <section className="sl-overlap"><AlertTriangle size={16} /><div><strong>Strategy overlap detected: {current.overlap}</strong><p>{current.overlap_note}</p></div></section> : null}

            <section className="sl-grid">
              <div><span>Universe with history</span><strong>{fmt(scan?.universe_with_sufficient_history ?? current.universe, 0)}</strong><small>Fails closed below required observations</small></div>
              <div><span>Displayed signals</span><strong>{signals.length}</strong><small>No trade-eligible signals</small></div>
              <div><span>Data status</span><strong>PIT limited</strong><small>Adjusted close preferred</small></div>
              <div><span>Promotion</span><strong>Blocked</strong><small>OOS and robustness pending</small></div>
            </section>

            <section className="sl-panel">
              <header><div><span className="sl-kicker">Formula and controls</span><h3>Reproducible specification</h3></div><ShieldCheck size={18} /></header>
              <div className="sl-spec">
                <div><span>Formula</span><code>{current.formula}</code></div>
                <div><span>Parameters</span><pre>{JSON.stringify(current.parameters, null, 2)}</pre></div>
                <div><span>Required data</span><ul>{(current.data_requirements || []).map((value) => <li key={value}>{value}</li>)}</ul></div>
              </div>
            </section>

            <section className="sl-panel sl-table-panel">
              <header><div><span className="sl-kicker">Signal monitor</span><h3>Current research outputs</h3></div><span>{busy === 'scan' ? 'Calculating…' : `${signals.length} shown · EOD observations, not live quotes`}</span></header>
              <div className="sl-table-wrap"><table><thead><tr><th>Ticker</th><th>Signal</th><th>Score</th><th>Confidence</th><th>Signal close</th><th>Stop</th><th>Target</th><th>Main reason</th><th>Data</th></tr></thead>
                <tbody>{signals.map((row) => <tr key={`${row.strategy_id}-${row.ticker}`}><td><strong>{row.ticker}</strong><small>{row.timestamp}</small></td><td><Status tone={String(row.signal).toLowerCase()}>{row.signal}</Status></td><td>{fmt(row.score)}</td><td>{row.confidence}</td><td><strong>{fmt(row.entry)}</strong><small>Close on {row.timestamp}</small></td><td>{fmt(row.stop)}</td><td>{fmt(row.target)}</td><td><span>{row.explanation?.main_driver}</span><small>{(row.reason_codes || []).join(' · ')}</small></td><td><span>{fmt(row.data?.completeness, 1)}%</span><small>{row.data?.pit_status}</small></td></tr>)}</tbody></table></div>
              {!signals.length ? <p className="sl-empty">No output is displayed until the strategy has sufficient verified history.</p> : null}
            </section>

            <section className="sl-validation">
              <div><span className="sl-kicker">Validation registry</span><h3>Promotion decision: DO NOT DEPLOY</h3><p>A running formula is not evidence of economic validity.</p></div>
              <ul>{(dashboard?.promotion_gates || []).map((gate) => <li key={gate}><i />{gate.replaceAll('_', ' ')}</li>)}</ul>
            </section>

            {backtest ? <section className="sl-panel"><header><div><span className="sl-kicker">Backtest receipt</span><h3>{backtest.ok ? 'Costed research result' : 'Backtest blocked'}</h3></div><Status tone={backtest.ok ? 'research' : 'restricted'}>{backtest.validation?.promotion || backtest.status || 'DO_NOT_DEPLOY'}</Status></header>
              {backtest.ok ? <div className="sl-grid metrics">{Object.entries(backtest.metrics || {}).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{fmt(value, 3)}</strong></div>)}</div> : <p className="sl-empty">{backtest.error}: this strategy remains DATA BUILDING until its specific walk-forward test is implemented.</p>}
            </section> : null}
          </> : <p className="sl-empty">{loading ? 'Loading governed strategy registry…' : 'No Strategy Lab registry available.'}</p>}
        </main>
      </div>
    </div>
  );
}
