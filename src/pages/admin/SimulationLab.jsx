import { useCallback, useEffect, useState } from 'react';
import { FlaskConical, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getSslDashboard,
  getSslHealth,
  getSslHistory,
  getSslQualityGates,
  getSslScenarios,
  runSslSimulation,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value ?? '—'}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

export default function SimulationLab() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [scenarioId, setScenarioId] = useState('rebalance_hdfc_plus');
  const [ticker, setTicker] = useState('HDFCBANK');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g, s, hist] = await Promise.all([
        getSslHealth(),
        getSslDashboard(),
        getSslQualityGates(),
        getSslScenarios(),
        getSslHistory(12),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
      setScenarios(s?.scenarios || []);
      setHistory(hist?.history || []);
      if ((s?.scenarios || [])[0]?.id) setScenarioId(s.scenarios[0].id);
    } catch (err) {
      setError(err?.message || 'Failed to load Simulation Lab');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRun = async () => {
    setBusy('run');
    setError('');
    try {
      const out = await runSslSimulation({
        scenario_id: scenarioId,
        ticker: ticker || undefined,
        n: 1200,
      });
      setResult(out);
      const hist = await getSslHistory(12);
      setHistory(hist?.history || []);
    } catch (err) {
      setError(err?.message || 'Simulation run failed');
    } finally {
      setBusy('');
    }
  };

  const dist = result?.probabilities?.distribution || {};
  const strategies = result?.strategies?.strategies || [];
  const stress = result?.stress?.tests || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-800 font-semibold">
            Institutional Simulation & Strategy Lab v1.0 · soft layer
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <FlaskConical className="h-6 w-6 text-cyan-800" />
            What happens if this decision is taken?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Experiment before allocate — reproducible portfolio, macro and strategy simulations with
            explicit assumptions, stress tests, historical replay and opportunity-cost analysis.
            Probabilistic bands only; never a trade ticket.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'ssl'} />
        <Stat
          label="Catalogue"
          value={dashboard?.catalogue?.scenario_count ?? scenarios.length ?? '—'}
          hint="seeded scenarios"
        />
        <Stat
          label="Sample E[r]"
          value={result?.probabilities?.expected_return ?? dashboard?.sample_expected_return ?? '—'}
          hint="not a price target"
        />
        <Stat
          label="Confidence"
          value={result?.confidence?.confidence ?? dashboard?.sample_confidence ?? '—'}
          hint="simulation integrity"
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint="Reproducible · no point outcomes"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Scenario builder</h2>
          <select
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={scenarioId}
            onChange={(e) => setScenarioId(e.target.value)}
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
          <input
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER override"
          />
          <Button variant="outline" onClick={onRun} disabled={!!busy}>
            {busy === 'run' ? 'Simulating…' : 'POST /simulation/run'}
          </Button>
          <p className="text-xs text-slate-400">
            {result?.report?.executive_summary || dashboard?.sample_summary || 'Run a scenario to inspect outcomes.'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Probability distribution</h2>
          {result ? (
            <ul className="space-y-1 text-slate-600">
              <li>Bull {dist.bull ?? '—'} · Base {dist.base ?? '—'} · Bear {dist.bear ?? '—'} · Stress {dist.stress ?? '—'}</li>
              <li>
                Bands p05 {result.probabilities?.bands?.p05} · p50 {result.probabilities?.bands?.p50} ·
                p95 {result.probabilities?.bands?.p95}
              </li>
              <li>Seed {result.run_key_seed} · reproducible={String(result.reproducible)}</li>
              <li>
                Opportunity cost analysed={String(result.opportunity_cost?.analysed)} · stress=
                {String(result.stress?.completed)}
              </li>
            </ul>
          ) : (
            <p className="text-xs text-slate-400">Distributions appear after a run.</p>
          )}
        </div>
      </div>

      {result ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Strategy comparison</h2>
            <ul className="space-y-2 text-slate-600">
              {strategies.map((s, i) => (
                <li key={i}>
                  <span className="text-xs uppercase tracking-wide text-cyan-800 mr-2">{s.label}</span>
                  E[r] {s.expected_return} · p05 {s.tail_risk_p05}
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-400 mt-2">
              {(result.strategies?.trade_offs || []).join(' · ')}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Stress / replay / decision</h2>
            <ul className="space-y-1 text-slate-600">
              {stress.slice(0, 4).map((t, i) => (
                <li key={i}>
                  {t.name}: {typeof t.result === 'object' ? JSON.stringify(t.result) : String(t.result)}
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500 mt-2">
              Replay: {result.replay?.active ? result.replay?.label || result.replay?.replay_id : 'available on demand'}
            </p>
            <p className="text-xs text-slate-500">{result.report?.cio_brief}</p>
          </div>
        </div>
      ) : null}

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
        <h2 className="font-semibold text-slate-900">Run history (append-only)</h2>
        <ul className="space-y-1 text-slate-600">
          {history.slice().reverse().map((h, i) => (
            <li key={i}>
              #{h.run_index} {h.scenario_id} · {h.ticker} · E[r]={h.expected_return} · seed {h.seed}
            </li>
          ))}
          {!history.length ? <li className="text-slate-400">No runs in this process yet.</li> : null}
        </ul>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Quality gates</h2>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              gates?.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
            }`}
          >
            {gates?.passed ? 'Pass' : 'Review'}
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(gates?.checks || {}).map(([key, ok]) => (
            <div
              key={key}
              className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
            >
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
