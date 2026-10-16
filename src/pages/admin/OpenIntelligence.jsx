import { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, Brain, Play, Radar, RefreshCw, Search } from 'lucide-react';
import {
  consultAoi,
  getAoiConnectors,
  getAoiDashboard,
  getAoiHealth,
  runAoiCycle,
  seedAoiRegistry,
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

export default function OpenIntelligence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [connectors, setConnectors] = useState([]);
  const [query, setQuery] = useState('Infosys');
  const [hits, setHits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [lastRun, setLastRun] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, c] = await Promise.all([
        getAoiHealth(),
        getAoiDashboard(),
        getAoiConnectors().catch(() => ({ connectors: [] })),
      ]);
      setHealth(h);
      setDashboard(d);
      setConnectors(c?.connectors || []);
    } catch (err) {
      setError(err?.message || 'Failed to load Open Intelligence');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (action) => {
    setBusy(action);
    setError('');
    try {
      if (action === 'seed') await seedAoiRegistry();
      if (action === 'cycle') {
        const result = await runAoiCycle({
          limit_per_connector: 25,
          publish: true,
        });
        setLastRun(result);
      }
      await load();
    } catch (err) {
      setError(err?.message || `${action} failed`);
    } finally {
      setBusy('');
    }
  };

  const onSearch = async (e) => {
    e?.preventDefault?.();
    if (!query.trim()) return;
    setBusy('search');
    try {
      const result = await consultAoi(query.trim(), 10);
      setHits(result?.hits || []);
    } catch (err) {
      setError(err?.message || 'Search failed');
    } finally {
      setBusy('');
    }
  };

  const cov = dashboard?.coverage || {};
  const learning = dashboard?.learning || {};
  const gaps = dashboard?.gaps || [];
  const heatmap = dashboard?.quality_heatmap || [];
  const latest = dashboard?.latest_documents || [];
  const failures = dashboard?.failures || [];
  const scheduler = dashboard?.scheduler || {};

  return (
    <div className="p-6 lg:p-8 max-w-7xl">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-orange-600 font-semibold">
            AOI v1.0 · Architecture locked
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Open Intelligence</h1>
          <p className="text-slate-500 mt-1 max-w-2xl">
            Autonomous public knowledge acquisition into the Knowledge Corpus — connectors, quality,
            gaps, and learning without redesigning KF / KIP / IRP / RSP.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" disabled={!!busy || loading} onClick={() => run('seed')} className="border-slate-300">
            <Radar size={16} className="mr-2" />
            {busy === 'seed' ? 'Seeding…' : 'Seed registry'}
          </Button>
          <Button disabled={!!busy || loading} onClick={() => run('cycle')} className="bg-blue-700 hover:bg-blue-800">
            <Play size={16} className="mr-2" />
            {busy === 'cycle' ? 'Running…' : 'Run acquisition cycle'}
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
        <p className="text-slate-400">Loading Open Intelligence console…</p>
      ) : (
        <>
          <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
            <p className="font-semibold text-slate-900">
              Status: {health?.status || 'unknown'} · {health?.version || 'aoi-v1.0.0'} ·{' '}
              {health?.architecture_status || 'v1.0.1 LOCKED'}
            </p>
            <p className="mt-1">
              Connectors: {(health?.connectors || []).join(', ') || '—'} · Scheduler:{' '}
              {scheduler.scheduler_health || '—'} · Queue {scheduler.queue_length ?? 0}
            </p>
            {lastRun?.totals ? (
              <p className="mt-1 text-xs text-slate-500">
                Last cycle — discovered {lastRun.totals.discovered}, downloaded {lastRun.totals.downloaded},
                facts {lastRun.totals.extracted_facts}, published {lastRun.totals.published}
              </p>
            ) : null}
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card label="Artifacts" value={cov.artifacts ?? 0} hint="documents tracked" />
            <Card label="Structured facts" value={cov.facts ?? 0} hint="versioned extractions" />
            <Card label="Companies w/ docs" value={cov.companies_with_docs ?? 0} hint="Nifty path" />
            <Card label="Graph edges" value={cov.edges ?? 0} hint="relationships" />
            <Card label="Versions" value={cov.versions ?? 0} hint="immutable history" />
            <Card label="Diffs" value={cov.diffs ?? 0} hint="incremental learning" />
            <Card label="Gaps" value={gaps.length} hint="remediation queue" />
            <Card label="Failures" value={failures.length} hint="download/parse errors" />
          </div>

          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Activity size={16} className="text-blue-700" />
                <h2 className="font-semibold text-slate-900">Connector health</h2>
              </div>
              <ul className="space-y-2 max-h-80 overflow-y-auto text-sm">
                {(connectors.length ? connectors : dashboard?.connector_health || []).map((c) => (
                  <li key={c.connector_id} className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="font-medium text-slate-800">{c.name || c.connector_id}</span>
                    <span className="text-xs text-slate-500">
                      {c.status} · {c.discovered ?? 0} discovered
                      {c.latency_ms != null ? ` · ${Math.round(c.latency_ms)}ms` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={16} className="text-amber-600" />
                <h2 className="font-semibold text-slate-900">Gap queue</h2>
              </div>
              {gaps.length === 0 ? (
                <p className="text-sm text-slate-400">No gaps yet — run an acquisition cycle.</p>
              ) : (
                <ul className="space-y-3 max-h-80 overflow-y-auto text-sm">
                  {gaps.slice(0, 12).map((g) => (
                    <li key={g.task_id} className="border-b border-slate-100 pb-2">
                      <p className="font-medium text-slate-900">
                        <span className="text-xs uppercase tracking-wide text-amber-700 mr-2">{g.severity}</span>
                        {g.title}
                      </p>
                      <p className="text-slate-500 mt-0.5">{g.suggested_action || g.detail}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Today AGI learned</h2>
              <ul className="space-y-2 text-sm text-slate-600">
                {(learning.highlights || ['Run a cycle to generate the daily digest.']).map((item) => (
                  <li key={item} className="border-b border-slate-100 pb-2">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Quality heatmap (Nifty 50)</h2>
              {heatmap.length === 0 ? (
                <p className="text-sm text-slate-400">No quality scores yet.</p>
              ) : (
                <div className="grid sm:grid-cols-2 gap-2 max-h-80 overflow-y-auto">
                  {heatmap.slice(0, 20).map((q) => (
                    <div key={q.company_id} className="rounded-lg border border-slate-100 px-3 py-2 text-sm">
                      <div className="flex justify-between">
                        <span className="font-medium">{q.nse_symbol || q.company_id}</span>
                        <span className="text-slate-500">{pct(q.overall)}</span>
                      </div>
                      <div className="mt-2 h-2 rounded bg-slate-100 overflow-hidden">
                        <div className="h-full bg-blue-600" style={{ width: `${Math.min(100, Number(q.overall) || 0)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <form onSubmit={onSearch} className="mb-8 bg-white rounded-xl border border-slate-200 p-5">
            <label className="text-sm font-semibold text-slate-900">Structured knowledge search</label>
            <div className="mt-3 flex flex-wrap gap-2">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Company, risk, macro, product…"
                className="flex-1 min-w-[220px] rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <Button type="submit" disabled={busy === 'search'} className="bg-blue-700 hover:bg-blue-800">
                <Search size={16} className="mr-2" />
                {busy === 'search' ? 'Searching…' : 'Consult AOI'}
              </Button>
            </div>
            {hits.length > 0 ? (
              <ul className="mt-4 divide-y divide-slate-100 text-sm">
                {hits.map((hit) => (
                  <li key={`${hit.kind}-${hit.id}`} className="py-3">
                    <p className="font-medium text-slate-900">
                      <span className="text-xs uppercase tracking-wide text-slate-400 mr-2">{hit.kind}</span>
                      {hit.label}
                    </p>
                    {hit.snippet ? <p className="text-slate-500 mt-1 line-clamp-2">{hit.snippet}</p> : null}
                  </li>
                ))}
              </ul>
            ) : null}
          </form>

          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden mb-8">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
              <Brain size={16} className="text-slate-400" />
              <h2 className="font-semibold text-slate-900">Latest documents</h2>
            </div>
            {latest.length === 0 ? (
              <p className="p-6 text-sm text-slate-400">No documents ingested yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-xs tracking-wide">
                    <tr>
                      <th className="text-left px-4 py-3 font-medium">Title</th>
                      <th className="text-left px-4 py-3 font-medium">Connector</th>
                      <th className="text-left px-4 py-3 font-medium">Type</th>
                      <th className="text-left px-4 py-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latest.map((d) => (
                      <tr key={d.artifact_id} className="border-t border-slate-100">
                        <td className="px-4 py-2.5 text-slate-800">{d.title}</td>
                        <td className="px-4 py-2.5 text-slate-600">{d.connector_id}</td>
                        <td className="px-4 py-2.5 text-slate-600">{d.doc_type}</td>
                        <td className="px-4 py-2.5 text-slate-600">{d.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
