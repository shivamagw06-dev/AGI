import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getLeoDashboard,
  getLeoHealth,
  getLeoQualityGates,
  packageLeo,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

export default function LiveEvidence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [probe, setProbe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([getLeoHealth(), getLeoDashboard(), getLeoQualityGates()]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load LEO dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onProbe = async () => {
    setBusy('probe');
    setError('');
    try {
      const result = await packageLeo('Should I buy HDFC Bank?', 'HDFCBANK', 'admin');
      setProbe(result);
      await load();
    } catch (err) {
      setError(err?.message || 'LEO probe failed');
    } finally {
      setBusy('');
    }
  };

  const metrics = dashboard?.metrics || {};
  const contrib = dashboard?.evidence_contribution || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-sky-600 font-semibold">
            LEO v1.0 · Live Evidence Orchestrator
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Activity className="h-6 w-6 text-sky-600" />
            API Usage & Evidence
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Additive evidence acquisition before Ask AGI. Not a reasoning engine. Plans sources, fetches,
            normalises, verifies via EVE, and packages for CAE / Academy / SIF / IRP.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onProbe} disabled={!!busy}>
            {busy === 'probe' ? 'Probing…' : 'Probe HDFC'}
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
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'leo'} />
        <Stat label="Calls today" value={dashboard?.calls_today ?? metrics.calls_today ?? '—'} />
        <Stat label="Calls / query" value={dashboard?.calls_per_query ?? metrics.calls_per_query ?? '—'} />
        <Stat
          label="Avg latency"
          value={dashboard?.average_latency_ms != null ? `${dashboard.average_latency_ms}ms` : '—'}
        />
        <Stat
          label="Reasoning contrib %"
          value={contrib.reasoning_contribution_pct ?? metrics.reasoning_contribution_pct ?? '—'}
          hint={`${contrib.external_contributions ?? 0} external`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="font-semibold text-slate-900">Configured APIs</h2>
          <ul className="text-sm space-y-2 max-h-72 overflow-auto">
            {(dashboard?.configured_apis || []).map((api) => (
              <li
                key={api.source_id}
                className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2"
              >
                <span>
                  <span className="font-medium text-slate-800">{api.source_id}</span>
                  <span className="text-slate-400 ml-2">{api.category}</span>
                </span>
                <span className={api.configured ? 'text-emerald-600' : 'text-slate-400'}>
                  {api.configured ? 'Configured' : 'Unset'}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="font-semibold text-slate-900">Most useful / unused / failures</h2>
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-1">Most useful</h3>
            <p className="text-sm text-slate-600">
              {(dashboard?.most_useful_apis || [])
                .map((r) => `${r.source_id} (${r.used})`)
                .join(', ') || '—'}
            </p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-1">Unused (configured)</h3>
            <p className="text-sm text-slate-600">{(dashboard?.unused_apis || []).join(', ') || '—'}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-1">API failures</h3>
            <p className="text-sm text-slate-600">
              {Object.entries(dashboard?.api_failures || {})
                .map(([k, v]) => `${k}: ${v}`)
                .join(', ') || 'None'}
            </p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-700 mb-1">Evidence objects created</h3>
            <p className="text-sm text-slate-600">{contrib.objects_created ?? metrics.evidence_objects_created ?? '—'}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Quality gates</h2>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              gates?.pass ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
            }`}
          >
            {gates?.pass ? 'Pass' : 'Review'}
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(gates?.success_metrics || {}).map(([key, ok]) => (
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2">Ticker</th>
                <th>External</th>
                <th>Objects</th>
                <th>Blocked</th>
                <th>Sources</th>
              </tr>
            </thead>
            <tbody>
              {(gates?.packages || []).map((row) => (
                <tr key={row.ticker} className="border-b border-slate-50">
                  <td className="py-2 font-medium">{row.ticker}</td>
                  <td>{row.external ? 'Yes' : 'No'}</td>
                  <td>{row.objects}</td>
                  <td>{row.blocked ? 'Yes' : 'No'}</td>
                  <td className="text-slate-500">{(row.sources_used || []).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {probe ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h2 className="font-semibold text-slate-900">HDFC probe trace</h2>
          <p className="text-sm text-slate-600">
            Sources used: {(probe.sources_used || []).join(', ') || '—'} · Objects:{' '}
            {probe.evidence_count ?? 0} · Confidence: {probe.evidence_confidence ?? '—'}
          </p>
          <p className="text-sm text-slate-600">
            Missing: {(probe.missing_evidence || []).join(', ') || 'none'} · Gate blocked:{' '}
            {probe.quality_gate?.blocked ? 'Yes' : 'No'}
          </p>
          <ul className="text-xs text-slate-500 space-y-1 max-h-40 overflow-auto">
            {(probe.api_calls || []).map((c, i) => (
              <li key={`${c.source_id}-${i}`}>
                {c.source_id}: {c.status} · {c.latency_ms}ms · items {c.items}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
