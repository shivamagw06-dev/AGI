import { useCallback, useEffect, useState } from 'react';
import { ClipboardCheck, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getEcpDashboard,
  getEcpHealth,
  getEcpQualityGates,
  completeEcp,
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

export default function EvidenceCompletion() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [probe, setProbe] = useState(null);
  const [ticker, setTicker] = useState('NESTLEIND');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getEcpHealth(),
        getEcpDashboard(),
        getEcpQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load ECP dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onComplete = async () => {
    setBusy('complete');
    setError('');
    try {
      const result = await completeEcp(ticker || 'NESTLEIND', `Should I buy ${ticker}?`);
      setProbe(result);
      await load();
    } catch (err) {
      setError(err?.message || 'Completion failed');
    } finally {
      setBusy('');
    }
  };

  const m = dashboard?.metrics || {};
  const reports = dashboard?.latest_reports || dashboard?.reports || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-teal-700 font-semibold">
            ECP v1.0 · Evidence Completion Pipeline
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <ClipboardCheck className="h-6 w-6 text-teal-700" />
            Evidence Completion Report
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Orchestration layer — identify why evidence is insufficient, auto-complete validated gaps,
            refresh LEO/CID, then re-evaluate quality gates. Recommendation gate unchanged. Not an engine.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-32"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onComplete} disabled={!!busy}>
            {busy === 'complete' ? 'Completing…' : 'Run Completion'}
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
        <Stat label="Runs" value={m.runs ?? 0} />
        <Stat label="Completed types" value={m.types_completed ?? 0} hint="Auto-filled" />
        <Stat label="Still missing" value={m.types_still_missing ?? 0} />
        <Stat
          label="Avg improvement"
          value={m.avg_quality_improvement_pct != null ? `${m.avg_quality_improvement_pct}%` : '—'}
        />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Completion Reports</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2 pr-3">Ticker</th>
                <th className="py-2 pr-3">Coverage</th>
                <th className="py-2 pr-3">Completed</th>
                <th className="py-2 pr-3">Still missing</th>
                <th className="py-2 pr-3">Providers</th>
                <th className="py-2 pr-3">Δ Quality</th>
                <th className="py-2 pr-3">Gate</th>
              </tr>
            </thead>
            <tbody>
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-4 text-slate-400">
                    No completion runs yet — probe a ticker.
                  </td>
                </tr>
              ) : (
                reports.map((r, idx) => (
                  <tr key={`${r.ticker}-${idx}`} className="border-b border-slate-50 align-top">
                    <td className="py-2 pr-3 font-medium">{r.ticker}</td>
                    <td className="py-2 pr-3">
                      {r.coverage != null ? `${r.coverage}%` : '—'}
                      {r.coverage_before != null ? (
                        <span className="text-slate-400 text-xs"> (was {r.coverage_before}%)</span>
                      ) : null}
                    </td>
                    <td className="py-2 pr-3">{(r.completed_automatically || []).join(', ') || '—'}</td>
                    <td className="py-2 pr-3">{(r.still_missing || []).slice(0, 4).join(', ') || '—'}</td>
                    <td className="py-2 pr-3">{(r.providers_used || []).join(', ') || '—'}</td>
                    <td className="py-2 pr-3">
                      {r.quality_improvement != null ? `${r.quality_improvement}%` : '—'}
                    </td>
                    <td className="py-2 pr-3">
                      {r.gate_blocked_after ? (
                        <span className="text-amber-700">Blocked</span>
                      ) : (
                        <span className="text-emerald-700">Eligible</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {probe ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
            <h2 className="font-semibold text-slate-900">Probe — {probe.ticker}</h2>
            <div className="grid gap-2 sm:grid-cols-2 text-sm">
              <div>Coverage: <strong>{probe.coverage ?? '—'}%</strong></div>
              <div>Improvement: <strong>{probe.quality_improvement ?? '—'}%</strong></div>
              <div className="sm:col-span-2">
                Completed: {(probe.completed_automatically || []).join(', ') || '—'}
              </div>
              <div className="sm:col-span-2">
                Still missing: {(probe.still_missing || []).join(', ') || '—'}
              </div>
              <div className="sm:col-span-2">
                Providers: {(probe.providers_used || []).join(', ') || '—'}
              </div>
              <div className="sm:col-span-2">
                Conflicts: {(probe.conflicts || []).length}
              </div>
            </div>
            {probe.withheld_explanation ? (
              <pre className="text-xs bg-amber-50 border border-amber-100 rounded-lg p-3 whitespace-pre-wrap">
                {probe.withheld_explanation}
              </pre>
            ) : null}
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2">
            <h2 className="font-semibold text-slate-900">Quality Panel</h2>
            <pre className="text-xs bg-slate-50 rounded-lg p-3 overflow-auto max-h-80">
              {JSON.stringify(probe.quality_panel || {}, null, 2)}
            </pre>
          </div>
        </div>
      ) : null}

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
          Gates passed: {gates?.passed ? 'Yes' : 'No'} · {gates?.ecp_version}
        </p>
      </div>
    </div>
  );
}
