import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Layers,
  RefreshCw,
  Search,
  Timer,
} from 'lucide-react';
import {
  clearCaeCache,
  getCaeContext,
  getCaeDashboard,
  getCaeHealth,
  getCaeMetrics,
  getCaeQueryPlan,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  return n > 1 ? `${Math.round(n)}%` : `${Math.round(n * 100)}%`;
}

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

const MODULES = [
  'Live Requests',
  'Context Packages',
  'Query Planner',
  'Retrieval Breakdown',
  'Ranking Inspector',
  'Token Budget',
  'Cache Dashboard',
  'Latency',
  'Engine Contributions',
  'Duplicate Reduction',
  'Compression Analysis',
  'Context Explorer',
];

export default function ContextAssembly() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [query, setQuery] = useState('Should I buy INFY?');
  const [plan, setPlan] = useState(null);
  const [pack, setPack] = useState(null);
  const [module, setModule] = useState(MODULES[0]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, m] = await Promise.all([getCaeHealth(), getCaeDashboard(), getCaeMetrics()]);
      setHealth(h);
      setDashboard(d);
      setMetrics(m?.metrics || d?.metrics || {});
    } catch (err) {
      setError(err?.message || 'Failed to load Context console');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onAssemble = async (e) => {
    e?.preventDefault?.();
    setBusy('assemble');
    setError('');
    try {
      const [p, c] = await Promise.all([
        getCaeQueryPlan(query.trim()),
        getCaeContext(query.trim(), { use_cache: true }),
      ]);
      setPlan(p);
      setPack(c);
      await load();
    } catch (err) {
      setError(err?.message || 'Assembly failed');
    } finally {
      setBusy('');
    }
  };

  const onClearCache = async () => {
    setBusy('cache');
    try {
      await clearCaeCache();
      await load();
    } catch (err) {
      setError(err?.message || 'Cache clear failed');
    } finally {
      setBusy('');
    }
  };

  const m = metrics || dashboard?.metrics || health?.metrics || {};
  const live = dashboard?.live_requests || [];
  const cache = dashboard?.cache || {};
  const contributions = pack?.engine_contributions || [];
  const ranking = pack?.ranking || [];
  const token = pack?.token_usage || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">CAE v1.0</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Context Assembly</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Unified orchestration gateway — one ranked, token-efficient institutional context package before reasoning. Engines stay independent.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={onClearCache} disabled={busy === 'cache'}>
            Clear cache
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm flex gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Assemblies" value={m.assemblies ?? '—'} />
        <Stat label="Cache hit rate" value={pct(m.cache_hit_rate)} hint={`Hits ${m.cache_hits ?? 0}`} />
        <Stat label="Avg latency" value={`${m.avg_assembly_latency_ms ?? '—'} ms`} />
        <Stat
          label="Avg tokens"
          value={m.avg_context_tokens ?? '—'}
          hint={`Dupes removed avg ${m.avg_duplicates_removed ?? 0}`}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {MODULES.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setModule(name)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              module === name
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Search className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Assemble Context</h2>
            </div>
            <form className="flex gap-2" onSubmit={onAssemble}>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Ask AGI style question"
              />
              <Button type="submit" disabled={busy === 'assemble'}>
                <Layers className="w-4 h-4 mr-2" />
                Assemble
              </Button>
            </form>
            {plan ? (
              <div className="mt-4 text-sm space-y-1">
                <p className="text-slate-700">
                  Intents: <span className="font-medium">{(plan.intents || []).join(', ')}</span>
                </p>
                <p className="text-slate-600">Engines: {(plan.engines || []).join(' → ')}</p>
                <p className="text-xs text-slate-500">
                  Strategy: {plan.reasoning_strategy} · ticker {plan.primary_ticker || '—'}
                </p>
              </div>
            ) : null}
            {pack ? (
              <div className="mt-4 grid md:grid-cols-3 gap-3 text-sm">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-400">Evidence</p>
                  <p className="text-xl font-semibold">{pack.evidence?.length || 0}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-400">Events</p>
                  <p className="text-xl font-semibold">{pack.events?.length || 0}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-400">Forecasts</p>
                  <p className="text-xl font-semibold">{pack.forecasts?.length || 0}</p>
                </div>
                <div className="md:col-span-3 text-xs text-slate-500">
                  Package {pack.package_id} · latency {pack.assembly_latency_ms} ms · tokens{' '}
                  {token.total_estimate ?? '—'} / {token.budget ?? '—'} · dupes removed{' '}
                  {pack.duplicates_removed} · compression {pack.compression_ratio}
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500 mt-4">Assemble a query to inspect the unified package.</p>
            )}
          </section>

          {(module === 'Ranking Inspector' || module === 'Token Budget') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">{module}</h2>
              {module === 'Token Budget' ? (
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Critical</p>
                    <p className="text-xl font-semibold">{token.critical ?? '—'}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Important</p>
                    <p className="text-xl font-semibold">{token.important ?? '—'}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Optional</p>
                    <p className="text-xl font-semibold">{token.optional ?? '—'}</p>
                  </div>
                </div>
              ) : (
                <ul className="space-y-2 text-sm">
                  {ranking.slice(0, 12).map((r) => (
                    <li key={r.item_id} className="flex justify-between gap-3 border-b border-slate-100 pb-2">
                      <span className="text-slate-700 truncate">
                        {r.priority} · {r.engine} · {r.title}
                      </span>
                      <span className="text-slate-500 shrink-0">{r.ranking_score}</span>
                    </li>
                  ))}
                  {!ranking.length ? <li className="text-slate-500">No ranking yet.</li> : null}
                </ul>
              )}
            </section>
          )}

          {(module === 'Live Requests' || module === 'Context Packages') && (
            <section className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-900 mb-3">Live Requests</h2>
              <ul className="space-y-2 text-sm">
                {live.slice(0, 10).map((p) => (
                  <li key={p.package_id} className="border-b border-slate-100 pb-2">
                    <p className="font-medium text-slate-800 truncate">{p.query}</p>
                    <p className="text-xs text-slate-500">
                      {p.assembly_latency_ms} ms · cache {String(p.cache_hit)} · tokens{' '}
                      {p.token_usage?.total_estimate ?? '—'}
                    </p>
                  </li>
                ))}
                {!live.length ? <li className="text-slate-500">No assemblies yet.</li> : null}
              </ul>
            </section>
          )}
        </div>

        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
              <Timer className="w-4 h-4" /> Engine Contributions
            </h2>
            <ul className="space-y-2 text-sm">
              {contributions.length ? (
                contributions.map((c) => (
                  <li key={c.engine} className="flex justify-between gap-2">
                    <span className="text-slate-700">{c.engine}</span>
                    <span className="text-slate-500">
                      {c.succeeded ? `${c.item_count} items` : c.error || 'fail'} · {Math.round(c.latency_ms || 0)} ms
                    </span>
                  </li>
                ))
              ) : (
                <li className="text-slate-500">Assemble to see engine breakdown.</li>
              )}
            </ul>
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Cache Dashboard</h2>
            <p className="text-sm text-slate-700">Entries: {cache.entries ?? 0}</p>
            <p className="text-xs text-slate-500 mt-1">Hit rate {pct(m.cache_hit_rate)}</p>
            <p className="text-[11px] text-slate-400 mt-3">
              Health: {health?.status || '—'} · gateway {String(health?.flags?.CAE_ASK_AGI_GATEWAY)} ·{' '}
              {health?.architecture_status || ''}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
