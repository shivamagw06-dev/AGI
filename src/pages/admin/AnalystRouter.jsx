import { useCallback, useEffect, useState } from 'react';
import { Network, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getAnalystRouterDashboard,
  getAnalystRouterHealth,
  getAnalystRouterQualityGates,
  routeAnalystRouter,
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

export default function AnalystRouter() {
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
        getAnalystRouterHealth(),
        getAnalystRouterDashboard(),
        getAnalystRouterQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Analyst Router');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRoute = async (q) => {
    const nextQ = (q ?? question).trim();
    if (!nextQ) return;
    setBusy(true);
    setError('');
    setQuestion(nextQ);
    try {
      const row = await routeAnalystRouter({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Route failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const routing = result?.routing_confidence || {};
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const weightEntries = Object.entries(result?.weights || {});

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-sky-700">
            RQ1 Sprint 5 · Institutional Analyst Router · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Network className="h-6 w-6 text-sky-700" />
            Analyst Router
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Decide who participates, in what order, with what weight and research assignment —
            before any analyst executes. Suppressed specialists stay silent.
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
          label="Selection accuracy"
          value={gates ? pct(gates.analyst_selection_accuracy) : '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Avg routing"
          value={gates?.avg_routing_ms != null ? `${gates.avg_routing_ms} ms` : '—'}
          hint={`Target < ${health?.max_routing_ms_target || 30} ms`}
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[280px] flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onRoute();
            }}
            placeholder="Institutional research question"
          />
          <Button onClick={() => onRoute()} disabled={busy}>
            {busy ? 'Routing…' : 'Route analysts'}
          </Button>
        </div>
        {samples.length ? (
          <div className="flex flex-wrap gap-2">
            {samples.slice(0, 6).map((s) => (
              <button
                key={s.question}
                type="button"
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100"
                onClick={() => onRoute(s.question)}
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
              label="Routing Confidence"
              value={pct(routing.routing_confidence)}
              tone={routing.passes_threshold ? 'good' : 'bad'}
            />
            <Row label="Runtime" value={result.routing_ms != null ? `${result.routing_ms} ms` : '—'} />
            <Row label="Question Type" value={result.question_type} />
            <Row label="Research Depth" value={result.research_depth} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Required analysts</h2>
              <ChipList items={result.required_analysts} tone="good" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Optional analysts</h2>
              <ChipList items={result.optional_analysts} tone="warn" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Suppressed analysts</h2>
              <ChipList items={(result.suppressed_analysts || []).slice(0, 12)} tone="bad" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Speaking order</h2>
              <ol className="space-y-1.5 text-sm text-slate-700">
                {(result.speaking_order || []).map((a, i) => (
                  <li key={`${i}-${a}`}>
                    <span className="mr-2 font-semibold text-sky-700">{i + 1}.</span>
                    {a}
                  </li>
                ))}
              </ol>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Weights</h2>
              <div className="space-y-2">
                {weightEntries.length ? (
                  weightEntries.map(([name, w]) => (
                    <div key={name} className="flex items-center justify-between text-sm">
                      <span className="text-slate-700">{name}</span>
                      <span className="font-semibold text-slate-900">{pct(w)}</span>
                    </div>
                  ))
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </div>
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Dependencies</h2>
              <div className="space-y-1 text-xs text-slate-600">
                {Object.entries(result.dependencies || {})
                  .filter(([, deps]) => deps?.length)
                  .map(([analyst, deps]) => (
                    <div key={analyst}>
                      <span className="font-semibold text-slate-800">{analyst}</span> ←{' '}
                      {(deps || []).join(', ')}
                    </div>
                  ))}
              </div>
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Research assignments</h2>
              <div className="space-y-3 max-h-[360px] overflow-auto pr-1">
                {(result.assignments || []).map((a) => (
                  <div key={a.analyst} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-sm font-semibold text-slate-900">{a.analyst}</p>
                    <p className="mt-1 text-xs text-slate-600">{a.assignment}</p>
                    {a.questions_to_answer?.length ? (
                      <ul className="mt-2 list-disc pl-4 text-xs text-slate-500">
                        {a.questions_to_answer.slice(0, 4).map((q) => (
                          <li key={q}>{q}</li>
                        ))}
                      </ul>
                    ) : null}
                    <p className="mt-2 text-[10px] uppercase tracking-wide text-slate-400">
                      Max {a.maximum_length_words || '—'} words · never:{' '}
                      {(a.never || []).slice(0, 3).join(', ') || '—'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Selection" value={pct(gates.analyst_selection_accuracy)} tone="good" />
            <Row label="Exclusions" value={pct(gates.exclusion_accuracy)} tone="good" />
            <Row label="Speaking order" value={pct(gates.speaking_order_accuracy)} tone="good" />
            <Row label="Weights" value={pct(gates.weight_accuracy)} tone="good" />
            <Row
              label="Mandate violations"
              value={String(gates.mandate_violations ?? '—')}
              tone={gates.mandate_violations === 0 ? 'good' : 'bad'}
            />
            <Row label="Gate status" value={gates.ok ? 'PASS' : 'FAIL'} tone={gates.ok ? 'good' : 'bad'} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
