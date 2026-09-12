import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Play, RefreshCw, Search, Shield } from 'lucide-react';
import {
  consultEve,
  getEveConflicts,
  getEveDashboard,
  getEveHealth,
  getEveSources,
  runEveVerification,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return n > 1 ? `${Math.round(n)}` : `${Math.round(n * 100)}%`;
}

function Card({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

export default function Evidence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [sources, setSources] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [query, setQuery] = useState('Infosys revenue');
  const [hits, setHits] = useState([]);
  const [consult, setConsult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, s, c] = await Promise.all([
        getEveHealth(),
        getEveDashboard(),
        getEveSources().catch(() => ({ sources: [] })),
        getEveConflicts('open').catch(() => ({ conflicts: [] })),
      ]);
      setHealth(h);
      setDashboard(d);
      setSources(s?.sources || []);
      setConflicts(c?.conflicts || d?.conflicts || []);
    } catch (err) {
      setError(err?.message || 'Failed to load Evidence console');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runJobs = async () => {
    setBusy('jobs');
    setError('');
    try {
      await runEveVerification();
      await load();
    } catch (err) {
      setError(err?.message || 'Verification job failed');
    } finally {
      setBusy('');
    }
  };

  const onSearch = async (e) => {
    e?.preventDefault?.();
    if (!query.trim()) return;
    setBusy('search');
    try {
      const result = await consultEve(query.trim(), 10);
      setConsult(result);
      setHits(result?.hits || []);
    } catch (err) {
      setError(err?.message || 'Evidence consult failed');
    } finally {
      setBusy('');
    }
  };

  const metrics = dashboard?.metrics || {};
  const heatmap = dashboard?.confidence_heatmap || [];
  const queue = dashboard?.verification_queue || [];
  const recent = dashboard?.recent_evidence || [];
  const audit = dashboard?.audit || [];

  return (
    <div className="p-6 lg:p-8 max-w-7xl">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-orange-600 font-semibold">
            EVE v1.0 · Between AOI and KCV/KF
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Evidence & Verification</h1>
          <p className="text-slate-500 mt-1 max-w-2xl">
            Provenance, trust scoring, conflict preservation, and auditable fact history — without
            redesigning locked architecture cores.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={!!busy || loading} onClick={runJobs} className="bg-blue-700 hover:bg-blue-800">
            <Play size={16} className="mr-2" />
            {busy === 'jobs' ? 'Verifying…' : 'Run verification jobs'}
          </Button>
          <Button variant="outline" disabled={!!busy || loading} onClick={load} className="border-slate-300">
            <RefreshCw size={16} className="mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>
      ) : null}

      {loading ? (
        <p className="text-slate-400">Loading evidence console…</p>
      ) : (
        <>
          <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
            <p className="font-semibold text-slate-900">
              Status: {health?.status || 'unknown'} · {health?.version || 'eve-v1.0.0'} ·{' '}
              {health?.architecture_status || 'v1.0.1 LOCKED'}
            </p>
            <p className="mt-1">
              Position: {health?.position || 'between_aoi_and_kcv_kf'} · Answer policy: verified
              evidence before raw facts.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card label="Evidence" value={metrics.evidence_count ?? 0} hint="immutable records" />
            <Card label="Verified facts" value={metrics.verified_facts ?? 0} hint="multi-source / high conf" />
            <Card label="Conflicts" value={metrics.conflicts ?? conflicts.length} hint="preserved, not overwritten" />
            <Card label="Avg confidence" value={pct(metrics.average_confidence)} hint="dynamic score" />
            <Card label="Source reliability" value={pct(metrics.source_reliability_avg)} hint="registry average" />
            <Card label="Knowledge health" value={metrics.knowledge_health_avg ?? 0} hint="trust average" />
            <Card label="Verification queue" value={queue.length} hint="open tasks" />
            <Card label="Sources" value={sources.length} hint="registry" />
          </div>

          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={16} className="text-amber-600" />
                <h2 className="font-semibold text-slate-900">Conflict Centre</h2>
              </div>
              {conflicts.length === 0 ? (
                <p className="text-sm text-slate-400">No open conflicts. Run AOI publish through EVE to populate.</p>
              ) : (
                <ul className="space-y-3 max-h-80 overflow-y-auto text-sm">
                  {conflicts.slice(0, 12).map((c) => (
                    <li key={c.conflict_id} className="border-b border-slate-100 pb-2">
                      <p className="font-medium text-slate-900">
                        <span className="text-xs uppercase tracking-wide text-amber-700 mr-2">{c.severity}</span>
                        {c.fact_key}
                      </p>
                      <p className="text-slate-500 mt-0.5">
                        {c.left_value?.slice(0, 90)} vs {c.right_value?.slice(0, 90)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Shield size={16} className="text-blue-700" />
                <h2 className="font-semibold text-slate-900">Verification queue</h2>
              </div>
              {queue.length === 0 ? (
                <p className="text-sm text-slate-400">Queue empty.</p>
              ) : (
                <ul className="space-y-3 max-h-80 overflow-y-auto text-sm">
                  {queue.slice(0, 12).map((t) => (
                    <li key={t.task_id} className="border-b border-slate-100 pb-2">
                      <p className="font-medium text-slate-900">{t.title}</p>
                      <p className="text-slate-500 mt-0.5">{t.detail}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-8">
            <h2 className="font-semibold text-slate-900 mb-3">Confidence / trust heatmap</h2>
            {heatmap.length === 0 ? (
              <p className="text-sm text-slate-400">No company health scores yet.</p>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {heatmap.slice(0, 18).map((h) => (
                  <div key={h.company_id} className="rounded-lg border border-slate-100 px-3 py-2 text-sm">
                    <div className="flex justify-between">
                      <span className="font-medium">{h.symbol || h.company_id}</span>
                      <span className="text-slate-500">{Math.round(h.trust || 0)}</span>
                    </div>
                    <div className="mt-2 h-2 rounded bg-slate-100 overflow-hidden">
                      <div className="h-full bg-blue-600" style={{ width: `${Math.min(100, Number(h.trust) || 0)}%` }} />
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      conf {pct(h.confidence)} · conflicts {h.conflicts ?? 0}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <form onSubmit={onSearch} className="mb-8 bg-white rounded-xl border border-slate-200 p-5">
            <label className="text-sm font-semibold text-slate-900">Evidence explorer / consult</label>
            <div className="mt-3 flex flex-wrap gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Fact, company, conflict…"
                className="flex-1 min-w-[220px] rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <Button type="submit" disabled={busy === 'search'} className="bg-blue-700 hover:bg-blue-800">
                <Search size={16} className="mr-2" />
                {busy === 'search' ? 'Consulting…' : 'Consult evidence'}
              </Button>
            </div>
            {consult?.guidance ? (
              <p className="text-xs text-slate-500 mt-3">
                <CheckCircle2 size={12} className="inline mr-1" />
                Highest-confidence first
                {consult.guidance.present_conflicts ? ' · conflicts present' : ''}
                {consult.guidance.inform_reasoning_if_low_confidence ? ' · low-confidence flagged' : ''}
              </p>
            ) : null}
            {hits.length > 0 ? (
              <ul className="mt-4 divide-y divide-slate-100 text-sm">
                {hits.map((hit) => (
                  <li key={`${hit.kind}-${hit.id}`} className="py-3">
                    <p className="font-medium text-slate-900">
                      <span className="text-xs uppercase tracking-wide text-slate-400 mr-2">{hit.kind}</span>
                      {hit.label}
                      {hit.confidence != null ? (
                        <span className="ml-2 text-xs text-slate-500">conf {pct(hit.confidence)}</span>
                      ) : null}
                    </p>
                    {hit.snippet ? <p className="text-slate-500 mt-1 line-clamp-2">{hit.snippet}</p> : null}
                  </li>
                ))}
              </ul>
            ) : null}
          </form>

          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="font-semibold text-slate-900">Source registry</h2>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-xs tracking-wide">
                    <tr>
                      <th className="text-left px-4 py-3 font-medium">Source</th>
                      <th className="text-left px-4 py-3 font-medium">Category</th>
                      <th className="text-left px-4 py-3 font-medium">Reliability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sources.map((s) => (
                      <tr key={s.source_id} className="border-t border-slate-100">
                        <td className="px-4 py-2.5 text-slate-800">{s.name}</td>
                        <td className="px-4 py-2.5 text-slate-600">{s.category}</td>
                        <td className="px-4 py-2.5 text-slate-600">{pct(s.reliability_score)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="font-semibold text-slate-900">Recent evidence</h2>
              </div>
              <ul className="divide-y divide-slate-100 text-sm max-h-96 overflow-y-auto">
                {recent.length === 0 ? (
                  <li className="p-6 text-slate-400">No evidence yet — publish AOI artifacts through EVE.</li>
                ) : (
                  recent.map((e) => (
                    <li key={e.evidence_id} className="px-5 py-3">
                      <p className="font-medium text-slate-900">
                        {(e.company_symbol || e.company_id || 'macro')} · {e.fact_key}
                      </p>
                      <p className="text-slate-500 mt-0.5 line-clamp-2">{e.value_text}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {e.verification_status} · conf {pct(e.confidence)} · {e.provenance?.source_name}
                      </p>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Audit log</h2>
            {audit.length === 0 ? (
              <p className="text-sm text-slate-400">No audit events yet.</p>
            ) : (
              <ul className="space-y-2 text-sm text-slate-600 max-h-64 overflow-y-auto">
                {audit.map((a) => (
                  <li key={a.audit_id} className="border-b border-slate-100 pb-2">
                    <span className="font-medium text-slate-800">{a.action}</span>
                    {a.detail ? ` — ${a.detail}` : ''}
                    <span className="text-xs text-slate-400 ml-2">{a.at}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
