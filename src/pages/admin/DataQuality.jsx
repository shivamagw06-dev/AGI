import { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getDvcDashboard,
  getDvcHealth,
  getDvcQualityGates,
  getDvcMetrics,
  validateDvc,
  enrichDvc,
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

function pct(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  return `${Math.round(n <= 1 ? n * 100 : n)}%`;
}

export default function DataQuality() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [probe, setProbe] = useState(null);
  const [ticker, setTicker] = useState('INFY');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g, m] = await Promise.all([
        getDvcHealth(),
        getDvcDashboard(),
        getDvcQualityGates(),
        getDvcMetrics(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
      setMetrics(m);
    } catch (err) {
      setError(err?.message || 'Failed to load DVC dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onValidate = async () => {
    setBusy('validate');
    setError('');
    try {
      const result = await validateDvc(ticker || 'INFY');
      setProbe(result);
      await load();
    } catch (err) {
      setError(err?.message || 'Validate failed');
    } finally {
      setBusy('');
    }
  };

  const onEnrich = async () => {
    setBusy('enrich');
    setError('');
    try {
      const result = await enrichDvc(ticker || 'INFY');
      setProbe(result);
      await load();
    } catch (err) {
      setError(err?.message || 'Enrich failed');
    } finally {
      setBusy('');
    }
  };

  const m = dashboard?.metrics || {};
  const providers = dashboard?.provider_health || [];
  const conflicts = dashboard?.conflict_queue || [];
  const heatmap = dashboard?.coverage_heatmap || [];
  const incomplete = dashboard?.most_incomplete_companies || [];
  const refresh = dashboard?.companies_needing_refresh || [];
  const updates = dashboard?.latest_updates || [];
  const errors = dashboard?.validation_errors || [];
  const consensus = dashboard?.consensus_results || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-700 font-semibold">
            DVC v1.0 · Data Validation & Consensus
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-emerald-700" />
            Data Quality
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Market Data platform layer — evaluate, validate, score, reconcile, and audit every field
            before it becomes institutional knowledge. Not an engine. Not a provider.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-28"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onValidate} disabled={!!busy}>
            {busy === 'validate' ? 'Validating…' : 'Validate'}
          </Button>
          <Button variant="outline" onClick={onEnrich} disabled={!!busy}>
            {busy === 'enrich' ? 'Enriching…' : 'Enrich CID'}
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
        <Stat label="Status" value={health?.status || '—'} hint={health?.version} />
        <Stat label="Companies" value={m.companies_tracked ?? 0} hint="Tracked validations" />
        <Stat label="Open conflicts" value={m.open_conflicts ?? 0} />
        <Stat label="Avg quality" value={pct(m.avg_overall_quality)} hint="Overall data quality" />
        <Stat label="Providers" value={m.providers_tracked ?? providers.length} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Coverage" value={pct(metrics?.coverage_pct)} hint="Success metric" />
        <Stat label="Freshness" value={pct(metrics?.freshness_pct)} />
        <Stat label="Validation" value={pct(metrics?.validation_pct)} />
        <Stat label="Provider uptime" value={pct(metrics?.provider_uptime_avg)} />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Provider Health / Reliability</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2 pr-4">Provider</th>
                <th className="py-2 pr-4">Priority</th>
                <th className="py-2 pr-4">Uptime</th>
                <th className="py-2 pr-4">Latency</th>
                <th className="py-2 pr-4">Wins</th>
                <th className="py-2 pr-4">Conflicts</th>
                <th className="py-2 pr-4">Adj. confidence</th>
              </tr>
            </thead>
            <tbody>
              {providers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-4 text-slate-400">
                    No provider samples yet — run Validate on a ticker.
                  </td>
                </tr>
              ) : (
                providers.map((p) => (
                  <tr key={p.provider} className="border-b border-slate-50">
                    <td className="py-2 pr-4 font-medium">{p.provider}</td>
                    <td className="py-2 pr-4">{p.priority}</td>
                    <td className="py-2 pr-4">{pct(p.uptime_pct)}</td>
                    <td className="py-2 pr-4">{p.avg_latency_ms != null ? `${p.avg_latency_ms}ms` : '—'}</td>
                    <td className="py-2 pr-4">{p.wins ?? 0}</td>
                    <td className="py-2 pr-4">{p.conflicts ?? 0}</td>
                    <td className="py-2 pr-4">{pct(p.adjusted_confidence)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="font-semibold text-slate-900">Coverage Heatmap</h2>
          <div className="overflow-x-auto max-h-80">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
                  <th className="py-2 pr-3">Company</th>
                  <th className="py-2 pr-3">Coverage</th>
                  <th className="py-2 pr-3">Fresh</th>
                  <th className="py-2 pr-3">Conf</th>
                  <th className="py-2 pr-3">Overall</th>
                  <th className="py-2 pr-3">Grade</th>
                </tr>
              </thead>
              <tbody>
                {heatmap.map((h) => (
                  <tr key={h.company_id} className="border-b border-slate-50">
                    <td className="py-2 pr-3 font-medium">{h.company_id}</td>
                    <td className="py-2 pr-3">{pct(h.coverage)}</td>
                    <td className="py-2 pr-3">{pct(h.freshness)}</td>
                    <td className="py-2 pr-3">{pct(h.confidence)}</td>
                    <td className="py-2 pr-3">{pct(h.overall)}</td>
                    <td className="py-2 pr-3">{h.research_grade || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="font-semibold text-slate-900">Conflict Queue</h2>
          <ul className="text-sm space-y-2 max-h-80 overflow-auto">
            {conflicts.length === 0 ? (
              <li className="text-slate-400">No open conflicts.</li>
            ) : (
              conflicts.map((c, idx) => (
                <li key={`${c.company_id}-${c.field}-${idx}`} className="border border-slate-100 rounded-lg p-3">
                  <p className="font-medium text-slate-800">
                    {c.company_id} · {c.field}{' '}
                    <span className="text-amber-700 uppercase text-xs">{c.severity}</span>
                  </p>
                  <p className="text-slate-500 mt-1">{c.reason}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Winner: {c.winning_provider} → {String(c.canonical_value)}
                  </p>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h2 className="font-semibold text-slate-900">Most Incomplete</h2>
          <ul className="text-sm space-y-1">
            {incomplete.length === 0 ? (
              <li className="text-slate-400">—</li>
            ) : (
              incomplete.map((r) => (
                <li key={r.company_id} className="flex justify-between gap-2">
                  <span>{r.company_id}</span>
                  <span className="text-slate-500">{pct(r.coverage)}</span>
                </li>
              ))
            )}
          </ul>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h2 className="font-semibold text-slate-900">Needing Refresh</h2>
          <ul className="text-sm space-y-1">
            {refresh.length === 0 ? (
              <li className="text-slate-400">—</li>
            ) : (
              refresh.map((r) => (
                <li key={r.company_id} className="flex justify-between gap-2">
                  <span>{r.company_id}</span>
                  <span className="text-slate-500">{pct(r.freshness)}</span>
                </li>
              ))
            )}
          </ul>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h2 className="font-semibold text-slate-900">Consensus Results</h2>
          <ul className="text-sm space-y-1 max-h-48 overflow-auto">
            {consensus.length === 0 ? (
              <li className="text-slate-400">—</li>
            ) : (
              consensus.map((r) => (
                <li key={r.company_id} className="flex justify-between gap-2">
                  <span>
                    {r.company_id} → {r.winning_provider || '—'}
                  </span>
                  <span className="text-slate-500">{pct(r.overall)}</span>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h2 className="font-semibold text-slate-900">Latest Updates</h2>
          <ul className="text-sm space-y-1 max-h-56 overflow-auto">
            {updates.map((u, idx) => (
              <li key={`${u.company_id}-${idx}`} className="flex justify-between gap-2 border-b border-slate-50 py-1">
                <span>
                  {u.company_id} · {u.canonical_provider || '—'}
                </span>
                <span className="text-slate-400 text-xs">{u.at ? String(u.at).slice(11, 19) : ''}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h2 className="font-semibold text-slate-900">Validation Errors</h2>
          <ul className="text-sm space-y-1 max-h-56 overflow-auto">
            {errors.length === 0 ? (
              <li className="text-slate-400">None</li>
            ) : (
              errors.map((e, idx) => (
                <li key={`${e.company_id}-${idx}`} className="border border-rose-50 rounded-lg p-2 text-rose-800">
                  {e.company_id}: {e.error}
                </li>
              ))
            )}
          </ul>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Quality Gates</h2>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(gates?.checks || {}).map(([key, ok]) => (
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400">
          Gates passed: {gates?.passed ? 'Yes' : 'No'} · {gates?.dvc_version}
        </p>
      </div>

      {probe ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
          <h2 className="font-semibold text-slate-900">Probe result</h2>
          <pre className="text-xs bg-slate-50 rounded-lg p-3 overflow-auto max-h-80">
            {JSON.stringify(probe, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
