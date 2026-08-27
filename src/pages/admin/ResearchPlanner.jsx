import { useCallback, useEffect, useState } from 'react';
import { ClipboardList, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getResearchObjectiveDashboard,
  getResearchObjectiveHealth,
  getResearchObjectiveQualityGates,
  planResearchObjective,
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

function ChipList({ items }) {
  if (!items?.length) return <span className="text-slate-400">—</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-700"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export default function ResearchPlanner() {
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
        getResearchObjectiveHealth(),
        getResearchObjectiveDashboard(),
        getResearchObjectiveQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Research Planner');
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
      const row = await planResearchObjective({ question: nextQ, skip_ere: false });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Plan failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const routing = result?.routing_confidence || {};
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-700">
            RQ1 Sprint 3 · Research Objective Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <ClipboardList className="h-6 w-6 text-teal-700" />
            Research Planner
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Convert a resolved question into one institutional research objective, then plan
            analysts, layers, APIs, and the report blueprint — before any intelligence layer
            executes.
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
          label="Objective accuracy"
          value={gates ? pct(gates.primary_objective_accuracy) : '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Avg planning"
          value={gates?.avg_planning_ms != null ? `${gates.avg_planning_ms} ms` : '—'}
          hint={`Target < ${health?.max_planning_ms_target || 30} ms`}
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
            {busy ? 'Planning…' : 'Plan research'}
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
            <Row label="Primary Intent" value={result.primary_intent} />
            <Row
              label="Primary Objective"
              value={result.objective_alias || result.primary_objective}
              tone={result.requires_clarification ? 'warn' : 'good'}
            />
            <Row label="Question Type" value={result.question_type} />
            <Row label="Expected Output" value={result.expected_output} />
            <Row label="Research Depth" value={result.research_depth} />
            <Row label="Decision Type" value={result.decision_type} />
            <Row label="Urgency" value={result.urgency} />
            <Row
              label="Routing Confidence"
              value={pct(routing.routing_confidence ?? result.overall_confidence)}
              tone={routing.passes_threshold ? 'good' : 'bad'}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Analysts</h2>
              <ChipList items={result.analysts} />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Layers required</h2>
              <ChipList items={result.layers} />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Layers skipped</h2>
              <ChipList items={result.layers_skip?.slice?.(0, 8) || result.layers_skip} />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">APIs</h2>
              <ChipList items={result.apis} />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Blueprint</h2>
              <ol className="space-y-1.5 text-sm text-slate-700">
                {(result.blueprint || []).map((b) => (
                  <li key={`${b.order}-${b.section}`}>
                    <span className="mr-2 font-semibold text-teal-700">{b.order}.</span>
                    {b.section}
                  </li>
                ))}
              </ol>
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Secondary objectives</h2>
              <ChipList items={result.secondary_objectives} />
              <div className="grid grid-cols-2 gap-2 pt-2">
                <Row label="Intent conf." value={pct(routing.intent_confidence)} />
                <Row label="Objective conf." value={pct(routing.objective_confidence)} />
                <Row label="Blueprint conf." value={pct(routing.blueprint_confidence)} />
                <Row label="Overall conf." value={pct(routing.overall_confidence)} />
              </div>
              {result.requires_clarification ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Execution blocked — clarify objective (threshold 85%).
                </div>
              ) : (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                  Plan ready · no layers or analysts executed ({result.planning_ms} ms).
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Primary objective" value={pct(gates.primary_objective_accuracy)} tone="good" />
            <Row label="Question type" value={pct(gates.question_type_accuracy)} tone="good" />
            <Row label="Blueprint" value={pct(gates.blueprint_accuracy)} tone="good" />
            <Row label="Analyst routing" value={pct(gates.analyst_routing_accuracy)} tone="good" />
            <Row label="Layer routing" value={pct(gates.layer_routing_accuracy)} tone="good" />
            <Row
              label="Gate status"
              value={gates.ok ? 'PASS' : 'FAIL'}
              tone={gates.ok ? 'good' : 'bad'}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
