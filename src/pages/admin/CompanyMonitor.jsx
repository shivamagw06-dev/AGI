import { useCallback, useEffect, useState } from 'react';
import { Radar, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getCompanyMonitorDashboard,
  getCompanyMonitorHealth,
  getCompanyMonitorQualityGates,
  runCompanyMonitor,
  runCompanyMonitorUniverse,
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

export default function CompanyMonitor() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [probe, setProbe] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getCompanyMonitorHealth(),
        getCompanyMonitorDashboard(),
        getCompanyMonitorQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Company Monitor dashboard');
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
      const result = await runCompanyMonitor(ticker || 'HDFCBANK');
      setProbe(result);
      await load();
    } catch (err) {
      setError(err?.message || 'Monitor run failed');
    } finally {
      setBusy('');
    }
  };

  const onUniverse = async () => {
    setBusy('universe');
    setError('');
    try {
      await runCompanyMonitorUniverse(8);
      await load();
    } catch (err) {
      setError(err?.message || 'Universe run failed');
    } finally {
      setBusy('');
    }
  };

  const m = dashboard?.metrics || {};
  const changes = dashboard?.latest_changes || [];
  const reviews = dashboard?.companies_needing_review || [];
  const critical = dashboard?.critical_alerts || [];
  const coverage = dashboard?.coverage || {};
  const freshness = dashboard?.freshness || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-rose-700 font-semibold">
            CMS v1.0 · Company Monitoring System
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Radar className="h-6 w-6 text-rose-700" />
            Company Monitor
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Living analyst for tracked companies — detect material changes, suggest House View
            reviews, never auto-change recommendations. Soft pipeline: LEO → CID → Company Analysis →
            Ask AGI.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onRun} disabled={!!busy}>
            {busy === 'run' ? 'Running…' : 'Monitor ticker'}
          </Button>
          <Button variant="outline" onClick={onUniverse} disabled={!!busy}>
            {busy === 'universe' ? 'Scanning…' : 'Run universe'}
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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
        <Stat label="Monitored" value={m.companies_monitored ?? 0} />
        <Stat label="Latest changes" value={m.change_events ?? 0} />
        <Stat label="Need review" value={m.companies_needing_review ?? 0} hint="House View hints" />
        <Stat label="Critical" value={m.critical_alerts ?? 0} />
        <Stat
          label="Coverage"
          value={coverage.financial_channel_pct != null ? `${coverage.financial_channel_pct}%` : '—'}
          hint="Financial channel"
        />
        <Stat label="Gates" value={gates?.passed ? 'PASS' : gates ? 'FAIL' : '—'} hint={health?.version} />
      </div>

      {probe ? (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Probe · {probe.ticker}</h2>
          <p className="text-sm text-slate-600">
            Changes: {(probe.what_changed || {}).change_count ?? 0} · Max significance:{' '}
            {(probe.what_changed || {}).max_significance || '—'} · Auto house-view changed:{' '}
            {String(probe.auto_house_view_changed)}
          </p>
          <ul className="space-y-2">
            {((probe.what_changed || {}).rows || []).slice(0, 8).map((r, idx) => (
              <li key={`${r.metric}-${idx}`} className="text-sm border-l-2 border-rose-200 pl-3 text-slate-700">
                <span className="font-semibold">{r.label || r.metric}</span> · {r.significance} — {r.detail}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-lg font-semibold text-slate-900 mb-3">Latest changes</h2>
          {changes.length === 0 ? (
            <p className="text-sm text-slate-500">No changes yet — run a monitor cycle.</p>
          ) : (
            <ul className="space-y-2 max-h-80 overflow-auto">
              {changes.slice(0, 20).map((c, idx) => (
                <li key={`${c.ticker}-${c.detected_at}-${idx}`} className="text-sm text-slate-700">
                  <span className="font-medium">{c.ticker}</span> · {c.significance} · {c.detail || c.change_type}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-lg font-semibold text-slate-900 mb-3">Critical alerts · Reviews</h2>
          {critical.length === 0 && reviews.length === 0 ? (
            <p className="text-sm text-slate-500">No critical alerts or review suggestions.</p>
          ) : (
            <div className="space-y-4">
              <ul className="space-y-2">
                {critical.slice(0, 10).map((a, idx) => (
                  <li key={`c-${idx}`} className="text-sm text-rose-800">
                    {a.ticker}: {a.detail || a.change_type}
                  </li>
                ))}
              </ul>
              <ul className="space-y-2">
                {reviews.slice(0, 10).map((r) => (
                  <li key={r.ticker} className="text-sm text-slate-700">
                    <span className="font-medium">{r.ticker}</span> — {r.action} ({r.material_changes} material)
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Freshness / knowledge age</h2>
        {freshness.length === 0 ? (
          <p className="text-sm text-slate-500">No snapshots yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
                  <th className="py-2 pr-4">Ticker</th>
                  <th className="py-2 pr-4">Captured</th>
                  <th className="py-2 pr-4">Knowledge age hint</th>
                  <th className="py-2">LEO evidence</th>
                </tr>
              </thead>
              <tbody>
                {freshness.map((f) => (
                  <tr key={f.ticker} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-medium">{f.ticker}</td>
                    <td className="py-2 pr-4 text-slate-500">{f.captured_at || '—'}</td>
                    <td className="py-2 pr-4 text-slate-500">{f.knowledge_age_hint || '—'}</td>
                    <td className="py-2">{f.leo_evidence_count ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
