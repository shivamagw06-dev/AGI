import { useCallback, useEffect, useMemo, useState } from 'react';
import { GitBranch, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getLayerRouterDashboard,
  getLayerRouterHealth,
  getLayerRouterQualityGates,
  planLayerRouter,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value ?? '—'}</p>
      {hint ? <p className="mt-1 text-xs text-slate-400">{hint}</p> : null}
    </div>
  );
}

function Row({ label, value, tone }) {
  const color =
    tone === 'good'
      ? 'text-emerald-700'
      : tone === 'warn'
        ? 'text-amber-700'
        : tone === 'bad'
          ? 'text-rose-700'
          : 'text-slate-900';
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-medium break-words ${color}`}>{value || '—'}</p>
    </div>
  );
}

function ChipList({ items, tone }) {
  if (!items?.length) return <span className="text-slate-400">—</span>;
  const cls =
    tone === 'good'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : tone === 'bad'
        ? 'border-rose-200 bg-rose-50 text-rose-800'
        : tone === 'warn'
          ? 'border-amber-200 bg-amber-50 text-amber-800'
          : 'border-slate-200 bg-white text-slate-700';
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span key={item} className={`rounded-md border px-2 py-0.5 text-xs ${cls}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function DagView({ groups }) {
  if (!groups?.length) return <p className="text-sm text-slate-400">—</p>;
  return (
    <div className="space-y-3">
      {groups.map((g) => (
        <div key={g.level} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="mb-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            <span>Level {g.level}</span>
            <span>{g.parallel ? 'Parallel' : 'Serial'}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {(g.layers || []).map((layer) => (
              <div
                key={layer}
                className="min-w-[88px] rounded-lg border border-sky-200 bg-white px-3 py-2 text-center shadow-sm"
              >
                <p className="text-xs font-semibold text-slate-900">{layer}</p>
                <p className="mt-0.5 text-[10px] text-slate-400">planned</p>
              </div>
            ))}
          </div>
          {g.level < groups.length - 1 ? (
            <div className="mt-2 text-center text-slate-300">↓</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default function LayerRouter() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState('Should I buy HDFC Bank?');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getLayerRouterHealth(),
        getLayerRouterDashboard(),
        getLayerRouterQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Layer Router');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onPlan = async (q) => {
    const nextQ = (q ?? question).trim();
    if (!nextQ) return;
    setBusy(true);
    setError('');
    setQuestion(nextQ);
    try {
      const row = await planLayerRouter({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Plan failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const contribRows = useMemo(() => {
    const rows = result?.expected_contributions || [];
    return rows.filter((r) => r.runs).slice(0, 12);
  }, [result]);

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-violet-700">
            RQ1 Sprint 6 · Intelligence Layer Router · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <GitBranch className="h-6 w-6 text-violet-700" />
            Layer Router
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Plan which intelligence layers execute, in what order, with what cost and expected
            contribution — before any layer runs.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Status" value={health?.status || (loading ? '…' : '—')} />
        <Stat label="Version" value={health?.version || '—'} hint={health?.sprint_name} />
        <Stat
          label="Routing accuracy"
          value={gates ? pct(gates.layer_routing_accuracy) : '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Runtime reduction"
          value={gates ? pct(gates.avg_runtime_reduction) : '—'}
          hint={`Avg plan ${gates?.avg_planning_ms ?? '—'} ms`}
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[280px] flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onPlan();
            }}
            placeholder="Institutional research question"
          />
          <Button onClick={() => onPlan()} disabled={busy}>
            {busy ? 'Planning…' : 'Plan execution'}
          </Button>
        </div>
        {samples.length ? (
          <div className="flex flex-wrap gap-2">
            {samples.slice(0, 6).map((s) => (
              <button
                key={s.question}
                type="button"
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100"
                onClick={() => onPlan(s.question)}
              >
                {s.question}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {result ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <Row label="Question" value={result.question} />
            <Row label="Primary Objective" value={result.primary_objective} tone="good" />
            <Row
              label="Est. runtime"
              value={result.estimated_runtime != null ? `${result.estimated_runtime} ms` : '—'}
            />
            <Row label="Runtime reduction" value={pct(result.runtime_reduction)} tone="good" />
            <Row
              label="Cost units"
              value={String(result.expected_cost?.cost_units ?? '—')}
            />
            <Row
              label="Planned confidence"
              value={pct(result.confidence_plan?.planned_confidence)}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Execution graph (DAG)</h2>
              <DagView groups={result.parallel_groups} />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Required layers</h2>
              <ChipList items={result.required_layers} tone="good" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Optional layers</h2>
              <ChipList items={result.optional_layers} tone="warn" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Suppressed layers</h2>
              <ChipList items={(result.suppressed_layers || []).slice(0, 14)} tone="bad" />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Expected contribution</h2>
              <div className="overflow-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="py-1 pr-2">Layer</th>
                      <th className="py-1 pr-2">Runs</th>
                      <th className="py-1 pr-2">Expected</th>
                      <th className="py-1">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contribRows.map((r) => (
                      <tr key={r.layer} className="border-t border-slate-100">
                        <td className="py-1.5 pr-2 font-semibold text-slate-800">{r.layer}</td>
                        <td className="py-1.5 pr-2">{r.required ? '✅' : '○'}</td>
                        <td className="py-1.5 pr-2">{pct(r.expected_contribution)}</td>
                        <td className="py-1.5 text-slate-500">{r.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Dependencies (sample)</h2>
              <div className="max-h-48 space-y-1 overflow-auto text-xs text-slate-600">
                {Object.entries(result.dependencies || {})
                  .filter(([, deps]) => deps?.length)
                  .slice(0, 12)
                  .map(([layer, deps]) => (
                    <div key={layer}>
                      <span className="font-semibold text-slate-800">{layer}</span> ←{' '}
                      {(deps || []).join(', ')}
                    </div>
                  ))}
              </div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                Plan only · no layers executed ({result.planning_ms} ms). Learning hook → ILM.
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Layer routing" value={pct(gates.layer_routing_accuracy)} tone="good" />
            <Row label="Dependencies" value={pct(gates.dependency_accuracy)} tone="good" />
            <Row label="Parallel" value={pct(gates.parallel_execution_accuracy)} tone="good" />
            <Row label="Suppression" value={pct(gates.suppressed_layer_accuracy)} tone="good" />
            <Row label="Runtime reduction" value={pct(gates.avg_runtime_reduction)} tone="good" />
            <Row label="Gate status" value={gates.ok ? 'PASS' : 'FAIL'} tone={gates.ok ? 'good' : 'bad'} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
