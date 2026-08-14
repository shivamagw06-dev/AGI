import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Beaker, Database, Pause, Play, RefreshCw, ShieldCheck } from 'lucide-react';
import { getStrategyLabDashboard, getStrategyLabHealth, getStrategyLabScan, runStrategyLabBacktest } from '@/lib/strategyLabApi';
import './StrategyLab.css';
import './StrategyLabGovernance.css';

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
  const strategyGroups = useMemo(() => ([
    ['IMPLEMENTED', 'Implemented'],
    ['DATA_BUILDING', 'Data building'],
    ['BLOCKED', 'Blocked'],
  ].map(([key, label]) => ({ key, label, rows: strategies.filter((item) => item.category === key) }))), [strategies]);
  const current = strategies.find((item) => item.strategy_id === selected) || strategies[0];
  const signals = useMemo(() => [...(scan?.signals || current?.signals || [])].sort((a, b) => (SIGNAL_ORDER[a.signal] || 9) - (SIGNAL_ORDER[b.signal] || 9)), [scan, current]);
  const live = scan?.live_market || dashboard?.live_market || health?.live_market;
  const clocks = scan?.clocks || dashboard?.clocks || health?.clocks;

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
          <div className="sl-meta"><Status tone="restricted">ADMIN ONLY</Status><Status>GOVERNANCE V1.1</Status><span>Version {dashboard?.version || health?.version || '—'}</span><span>Research → Validation → Paper → Production</span></div>
        </div>
        <div className="sl-actions">
          <button onClick={load} disabled={loading} title="Refresh Strategy Lab"><RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh</button>
          <button onClick={runScan} disabled={!!busy || !current?.calculator_available}><Play size={16} /> Run current scan</button>
          <button onClick={runBacktest} disabled={!!busy || !current?.calculator_available}><Activity size={16} /> Backtest</button>
          <button disabled title="Promotion gates have not passed"><Pause size={16} /> Deploy blocked</button>
        </div>
      </header>

      {error ? <div className="sl-alert"><AlertTriangle size={17} /><span>{error}</span></div> : null}

      <section className="sl-live-monitor">
        <div><span className="sl-kicker">Live market input</span><h3>{String(live?.provider || 'Upstox').toUpperCase()}</h3><Status tone={live?.status === 'connected' ? 'research' : 'restricted'}>{live?.status || 'NOT CONNECTED'}</Status></div>
        <div><span>Subscriptions</span><strong>{fmt(live?.subscribed_instruments, 0)}</strong><small>{fmt(live?.observed_instruments, 0)} observed</small></div>
        <div><span>Feed health</span><strong>{fmt(live?.decode_errors, 0)} errors</strong><small>{fmt(live?.reconnects, 0)} reconnects</small></div>
        <div><span>Signal clock</span><strong>{clocks?.signal?.mode || 'EOD'}</strong><small>{clocks?.signal?.completed_session || 'Unavailable'} completed</small></div>
        <div><span>Market clock</span><strong>{clocks?.market?.session || 'UNKNOWN'}</strong><small>{clocks?.market?.local_date || '—'} · {clocks?.market?.local_time || '—'}</small></div>
      </section>

      <div className="sl-workspace">
        <aside className="sl-sidebar">
          <div className="sl-sidebar-title"><span>Strategy library</span><b>{strategies.length}</b></div>
          <nav>{strategyGroups.map((group) => group.rows.length ? <section className="sl-nav-group" key={group.key}><h4>{group.label}<b>{group.rows.length}</b></h4>{group.rows.map((item) => (
            <button key={item.strategy_id} className={selected === item.strategy_id ? 'active' : ''} onClick={() => { setSelected(item.strategy_id); setScan(null); setBacktest(null); }}>
              <strong>{item.name}</strong><span>{item.family} · {item.version}</span><small><i>{item.lifecycle}</i><em>{item.calculator_available ? `${item.universe || 0} eligible` : 'No output'}</em></small>
            </button>
          ))}</section> : null)}</nav>
          <div className="sl-data"><Database size={15} /><div><strong>Warehouse source</strong><span>Adjusted daily OHLCV</span><span>PIT status: PIT_LIMITED</span></div></div>
        </aside>

        <main className="sl-main">
          {current ? <>
            <section className="sl-strategy-head">
              <div><span className="sl-kicker">{current.family}</span><h2>{current.name}</h2><p>{current.formula}</p></div>
              <div className="sl-head-status"><Status>{current.data_mode || 'EOD'}</Status><Status>{current.lifecycle}</Status><Status tone="restricted">{current.signal_status || 'BLOCKED'}</Status><span>Completed session {dashboard?.session_health?.latest_completed_session || current.as_of || '—'}</span></div>
            </section>

            {!current.calculator_available ? <section className="sl-alert sl-inline"><AlertTriangle size={17} /><span>This family is visible for governance and design review only. Output is blocked: {(current.reason_codes || current.blocked_by || []).join(' · ') || 'STRATEGY_NOT_IMPLEMENTED'}.</span></section> : null}

            {current.overlap ? <section className="sl-overlap"><AlertTriangle size={16} /><div><strong>Strategy overlap detected: {current.overlap}</strong><p>{current.overlap_note}</p></div></section> : null}

            <section className="sl-grid">
              <div><span>Common-session universe</span><strong>{fmt(scan?.universe_with_sufficient_history ?? current.universe, 0)}</strong><small>{fmt(dashboard?.session_health?.mixed_session_blocked, 0)} stale/mixed blocked</small></div>
              <div><span>Displayed signals</span><strong>{signals.length}</strong><small>No trade-eligible signals</small></div>
              <div><span>Data status</span><strong>PIT limited</strong><small>Adjusted close preferred</small></div>
              <div><span>Execution</span><strong>Blocked</strong><small>No strategy may self-promote</small></div>
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
              <div className="sl-table-wrap"><table><thead><tr><th>Ticker</th><th>Research direction</th><th>Strength</th><th>Signal price</th><th>Completed close</th><th>Live price</th><th>Eligibility</th><th>Failed gates</th><th>Evidence</th></tr></thead>
                <tbody>{signals.map((row) => <tr key={`${row.strategy_id}-${row.ticker}`}><td><strong>{row.ticker}</strong><small>{row.signal_session || row.timestamp}</small></td><td><Status tone={String(row.signal).toLowerCase()}>{row.research_direction || row.signal}</Status><small>{row.signal}</small></td><td>{fmt(row.signal_strength ?? Math.abs(row.score))}<small>{row.confidence}</small></td><td><strong>{fmt(row.prices?.signal_price ?? row.entry)}</strong><small>{row.prices?.signal_session || row.timestamp}</small></td><td><strong>{fmt(row.prices?.latest_completed_close)}</strong><small>{row.prices?.latest_completed_session || 'Unavailable'}</small></td><td><strong>{fmt(row.prices?.live_price)}</strong><small>{row.prices?.live_source || 'Not connected'}{row.prices?.live_quote_age_ms != null ? ` · ${Math.round(row.prices.live_quote_age_ms / 1000)}s old` : ''}</small><small>{(row.live_validation?.reason_codes || []).join(' · ')}</small></td><td><Status tone="restricted">{row.eligibility}</Status><small>Execution blocked</small></td><td><span>{(row.reason_codes || []).join(' · ')}</span></td><td><span>Data {row.validation?.data}</span><small>PIT {row.validation?.pit} · Costs {row.validation?.costs} · Risk {row.validation?.risk}</small></td></tr>)}</tbody></table></div>
              {!signals.length ? <p className="sl-empty">No output is displayed until the strategy has sufficient verified history.</p> : null}
            </section>

            <section className="sl-validation">
              <div><span className="sl-kicker">Validation registry</span><h3>Promotion decision: DO NOT DEPLOY</h3><p>A running formula is not evidence of economic validity.</p></div>
              <ul>{(dashboard?.promotion_gates || []).map((gate) => <li key={gate}><i />{gate.replaceAll('_', ' ')}</li>)}</ul>
            </section>

            <section className="sl-panel">
              <header><div><span className="sl-kicker">Admin strategy builder</span><h3>Governed draft contract</h3></div><Status>DRAFT ONLY</Status></header>
              <div className="sl-spec"><div><span>Definition fields</span><code>{(dashboard?.builder_contract?.fields || []).join(' + ')}</code></div><div><span>Code policy</span><strong>Arbitrary code blocked</strong></div><div><span>Promotion policy</span><strong>Self-promotion blocked</strong></div></div>
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
