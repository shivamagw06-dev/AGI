import { useCallback, useEffect, useState } from 'react';
import { GitBranch, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  analyseCig,
  getCigCompany,
  getCigDashboard,
  getCigEvent,
  getCigHealth,
  getCigQualityGates,
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

export default function CausalIntelligence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [pack, setPack] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [event, setEvent] = useState('oil_spike');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getCigHealth(),
        getCigDashboard(),
        getCigQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Causal Intelligence');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCompany = async () => {
    setBusy('company');
    setError('');
    try {
      const out = await getCigCompany(ticker || 'HDFCBANK');
      setPack(out);
    } catch (err) {
      setError(err?.message || 'Company causal pack failed');
    } finally {
      setBusy('');
    }
  };

  const onEvent = async () => {
    setBusy('event');
    setError('');
    try {
      const out = await getCigEvent(event || 'repo_rate_cut');
      setPack(out);
    } catch (err) {
      setError(err?.message || 'Event propagation failed');
    } finally {
      setBusy('');
    }
  };

  const onAnalyse = async () => {
    setBusy('analyse');
    setError('');
    try {
      const out = await analyseCig({
        ticker: ticker || undefined,
        event: event || undefined,
        question: `Why did ${ticker || 'markets'} move under ${event || 'this shock'}?`,
      });
      setPack(out);
      await load();
    } catch (err) {
      setError(err?.message || 'Analyse failed');
    } finally {
      setBusy('');
    }
  };

  const conf = pack?.confidence || {};
  const report = pack?.report || {};
  const chains = pack?.chains || [];
  const heat = dashboard?.confidence_heatmap || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-teal-700 font-semibold">
            Causal Intelligence Graph v1.0 · soft layer
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-teal-700" />
            Why did this happen?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Living economic relationship model — transmission chains, event propagation,
            confidence heatmaps and counterfactuals. Reasoning layer, not a data dump.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-40"
            value={event}
            onChange={(e) => setEvent(e.target.value)}
            placeholder="event id"
          />
          <Button variant="outline" onClick={onCompany} disabled={!!busy}>
            {busy === 'company' ? 'Loading…' : 'Company'}
          </Button>
          <Button variant="outline" onClick={onEvent} disabled={!!busy}>
            {busy === 'event' ? 'Loading…' : 'Event'}
          </Button>
          <Button variant="outline" onClick={onAnalyse} disabled={!!busy}>
            {busy === 'analyse' ? 'Analysing…' : 'Analyse'}
          </Button>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'cig'} />
        <Stat label="Nodes" value={dashboard?.node_count ?? '—'} hint={`${dashboard?.edge_count ?? '—'} edges`} />
        <Stat
          label="Sample confidence"
          value={conf.confidence ?? dashboard?.sample_confidence ?? '—'}
          hint={conf.label || 'Run company'}
        />
        <Stat
          label="Sectors modelled"
          value={(dashboard?.sectors_modelled || []).length || '—'}
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint="Evidenced chains only"
        />
      </div>

      {pack ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">
              {pack.ticker || pack.label || 'Causal pack'}
            </h2>
            <p className="text-slate-600">{report.executive_summary || pack.description}</p>
            <ul className="space-y-1 text-slate-600">
              {(pack.upstream_drivers || []).slice(0, 6).map((d) => (
                <li key={d}>Upstream: {d}</li>
              ))}
              {(pack.affected_sectors || []).slice(0, 6).map((d) => (
                <li key={d}>Sector: {d}</li>
              ))}
            </ul>
            <p className="text-xs text-slate-400 mt-3">{report.cio_brief}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Propagation chains</h2>
            <ul className="space-y-2 text-slate-600">
              {chains.slice(0, 8).map((c, i) => (
                <li key={i}>
                  <span className="text-xs uppercase tracking-wide text-teal-700 mr-2">
                    {c.order_label || `order ${c.order}`}
                  </span>
                  {(c.path_labels || c.path || []).join(' → ')}
                  <span className="text-slate-400"> · p={c.transmission_probability}</span>
                </li>
              ))}
              {!chains.length ? <li>Run company or event to populate chains.</li> : null}
            </ul>
          </div>
        </div>
      ) : null}

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Confidence heatmap — strongest drivers</h2>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {heat.slice(0, 8).map((h) => (
            <div
              key={`${h.source}-${h.target}`}
              className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
            >
              <span className="text-slate-600">
                {h.source} → {h.target}
              </span>
              <span className="text-teal-700 font-medium">{h.score}</span>
            </div>
          ))}
        </div>
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
