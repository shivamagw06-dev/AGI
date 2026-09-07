import { useCallback, useEffect, useState } from 'react';
import { Network, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getIkgCompany,
  getIkgDashboard,
  getIkgHealth,
  getIkgPath,
  getIkgQualityGates,
  queryIkg,
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

export default function KnowledgeGraph() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [pack, setPack] = useState(null);
  const [queryResult, setQueryResult] = useState(null);
  const [ticker, setTicker] = useState('HDFCBANK');
  const [question, setQuestion] = useState('Show companies exposed to copper');
  const [pathSource, setPathSource] = useState('oil');
  const [pathTarget, setPathTarget] = useState('NESTLEIND');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getIkgHealth(),
        getIkgDashboard(),
        getIkgQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Knowledge Graph');
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
      const out = await getIkgCompany(ticker || 'HDFCBANK');
      setPack(out);
    } catch (err) {
      setError(err?.message || 'Company graph failed');
    } finally {
      setBusy('');
    }
  };

  const onQuery = async () => {
    setBusy('query');
    setError('');
    try {
      const out = await queryIkg({ question });
      setQueryResult(out);
    } catch (err) {
      setError(err?.message || 'Query failed');
    } finally {
      setBusy('');
    }
  };

  const onPath = async () => {
    setBusy('path');
    setError('');
    try {
      const out = await getIkgPath(pathSource, pathTarget);
      setQueryResult({ result: { intent: 'path', ...out } });
    } catch (err) {
      setError(err?.message || 'Path failed');
    } finally {
      setBusy('');
    }
  };

  const gh = dashboard?.graph_health || {};
  const rels = pack?.relationships || [];
  const deps = pack?.dependencies || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-700 font-semibold">
            Institutional Knowledge Graph v1.0 · soft layer
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Network className="h-6 w-6 text-indigo-700" />
            What is connected?
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Permanent institutional knowledge network — entities, evidenced relationships,
            supply chain, ownership, macro links and dependency traversal. Not isolated facts.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-36"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="TICKER"
          />
          <Button variant="outline" onClick={onCompany} disabled={!!busy}>
            {busy === 'company' ? 'Loading…' : 'Entity'}
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
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'ikg'} />
        <Stat label="Nodes" value={gh.node_count ?? '—'} hint={`${gh.edge_count ?? '—'} edges`} />
        <Stat
          label="Sample links"
          value={pack?.relationship_count ?? dashboard?.sample_relationship_count ?? '—'}
          hint={pack?.canonical_id || 'Run entity'}
        />
        <Stat
          label="Confidence"
          value={pack?.confidence?.confidence ?? dashboard?.sample_confidence ?? '—'}
          hint="evidenced edges"
        />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : 'Review'}
          hint="No unsupported edges"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Graph query</h2>
          <input
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Show suppliers of Nestlé / companies exposed to copper"
          />
          <Button variant="outline" onClick={onQuery} disabled={!!busy}>
            {busy === 'query' ? 'Querying…' : 'Run query'}
          </Button>
          {queryResult?.result ? (
            <pre className="text-xs bg-slate-50 border border-slate-100 rounded-lg p-3 overflow-auto max-h-56">
              {JSON.stringify(queryResult.result, null, 2)}
            </pre>
          ) : null}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 text-sm">
          <h2 className="font-semibold text-slate-900">Path explorer</h2>
          <div className="flex gap-2">
            <input
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-full"
              value={pathSource}
              onChange={(e) => setPathSource(e.target.value)}
              placeholder="source"
            />
            <input
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm w-full"
              value={pathTarget}
              onChange={(e) => setPathTarget(e.target.value)}
              placeholder="target"
            />
          </div>
          <Button variant="outline" onClick={onPath} disabled={!!busy}>
            {busy === 'path' ? 'Traversing…' : 'Find path'}
          </Button>
          <p className="text-xs text-slate-400">{pack?.report?.cio_brief || dashboard?.sample_summary}</p>
        </div>
      </div>

      {pack ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Relationships — {pack.canonical_id}</h2>
            <ul className="space-y-2 text-slate-600">
              {rels.slice(0, 12).map((r, i) => (
                <li key={i}>
                  <span className="text-xs uppercase tracking-wide text-indigo-700 mr-2">
                    {r.relation}
                  </span>
                  {r.counterpart_label || r.counterpart}
                  <span className="text-slate-400"> · conf {r.confidence}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-2 text-sm">
            <h2 className="font-semibold text-slate-900">Dependency map</h2>
            <p>Suppliers: {(deps.suppliers || []).join(', ') || '—'}</p>
            <p>Customers: {(deps.customers || []).join(', ') || '—'}</p>
            <p>Macro: {(deps.macro_drivers || []).join(', ') || '—'}</p>
            <p>Tech: {(deps.technology_exposure || []).join(', ') || '—'}</p>
            <p>Regulators: {(deps.regulators || []).join(', ') || '—'}</p>
          </div>
        </div>
      ) : null}

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
