import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BrainCircuit, RefreshCw, ShieldCheck } from 'lucide-react';
import {
  classifyResearchOntology,
  getResearchOntologyConstitution,
  getResearchOntologyDashboard,
  getResearchOntologyHealth,
  getResearchOntologyQualityGates,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

const FLOW_STEPS = [
  'User Question',
  'Primary Intent',
  'Secondary Intents',
  'Entity',
  'Entity Type',
  'Objective',
  'Confidence',
  'Needs Clarification?',
  'Next Stage',
];

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value ?? '—'}</p>
      {hint ? <p className="mt-1 text-xs text-slate-400">{hint}</p> : null}
    </div>
  );
}

function FlowRow({ label, value, tone }) {
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
      <p className={`mt-1 text-sm font-medium ${color}`}>{value || '—'}</p>
    </div>
  );
}

export default function IntentIntelligence() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [constitution, setConstitution] = useState(null);
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
      const [h, d, c, g] = await Promise.all([
        getResearchOntologyHealth(),
        getResearchOntologyDashboard(),
        getResearchOntologyConstitution(),
        getResearchOntologyQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setConstitution(c);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load RQ1 Intent Intelligence');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onClassify = async (q) => {
    const nextQ = (q ?? question).trim();
    if (!nextQ) return;
    setBusy(true);
    setError('');
    setQuestion(nextQ);
    try {
      const row = await classifyResearchOntology(nextQ);
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Classify failed');
    } finally {
      setBusy(false);
    }
  };

  const benchmarks = dashboard?.benchmark_samples || [];
  const intents = useMemo(
    () => Object.entries(constitution?.primary_intents || {}),
    [constitution]
  );

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-700">
            RQ1 Sprint 1 · Research Ontology · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <BrainCircuit className="h-6 w-6 text-teal-700" />
            Intent Intelligence
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Constitution-first debugging surface. Classify the research type before any analyst or
            intelligence layer executes.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Status" value={health?.status || '—'} hint={health?.programme} />
        <Stat label="Sprint" value={`S${health?.sprint || 1}`} hint={health?.sprint_name} />
        <Stat
          label="Benchmark Gates"
          value={gates ? `${gates.passed}/${gates.total}` : '—'}
          hint={gates?.ok ? 'All passed' : 'Needs attention'}
        />
        <Stat
          label="Execution"
          value="Classify only"
          hint="0 layers · 0 analysts"
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Live Classifier
            </p>
            <p className="text-sm text-slate-600">
              No research begins when clarification is required.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs text-emerald-800">
            <ShieldCheck className="h-3.5 w-3.5" />
            Soft-wire · not a top-level layer
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onClassify();
            }}
            className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm"
            placeholder="Ask a research question…"
          />
          <Button type="button" onClick={() => onClassify()} disabled={busy}>
            {busy ? 'Classifying…' : 'Classify'}
          </Button>
        </div>

        {result ? (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            <FlowRow label="User Question" value={result.question} />
            <FlowRow label="Primary Intent" value={result.primary_intent} tone="good" />
            <FlowRow
              label="Secondary Intents"
              value={(result.secondary_intents || []).join(', ') || '—'}
            />
            <FlowRow label="Entity" value={result.entity || 'Unknown'} />
            <FlowRow label="Entity Type" value={result.entity_type} />
            <FlowRow label="Objective" value={result.research_objective} />
            <FlowRow
              label="Confidence"
              value={
                result.confidence_pct != null
                  ? `${result.confidence_pct}%`
                  : result.confidence != null
                    ? `${Math.round(result.confidence * 100)}%`
                    : '—'
              }
              tone={result.confidence_pct >= 90 ? 'good' : result.confidence_pct >= 60 ? 'warn' : 'bad'}
            />
            <FlowRow
              label="Needs Clarification?"
              value={result.requires_clarification ? 'Yes' : 'No'}
              tone={result.requires_clarification ? 'warn' : 'good'}
            />
            <FlowRow label="Next Stage" value={result.next_stage} />
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            Run a classification to see the full routing decision chain.
          </p>
        )}

        {result?.requires_clarification ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-semibold">Clarification required — no research begins.</p>
            <ul className="mt-2 list-disc pl-5">
              {(result.possible_matches || []).map((m) => (
                <li key={`${m.entity}-${m.ticker}`}>
                  {m.entity}
                  {m.ticker ? ` (${m.ticker})` : ''}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {result ? (
          <div>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Decision Trace
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
              {FLOW_STEPS.map((step, i) => (
                <span key={step} className="inline-flex items-center gap-2">
                  <span className="rounded-md border border-slate-200 bg-white px-2 py-1">{step}</span>
                  {i < FLOW_STEPS.length - 1 ? <span className="text-slate-300">↓</span> : null}
                </span>
              ))}
            </div>
            <pre className="mt-3 max-h-80 overflow-auto rounded-xl border border-slate-200 bg-slate-950 p-4 text-[11px] text-emerald-100">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Benchmark Questions
          </p>
          <div className="mt-3 space-y-2">
            {benchmarks.map((b) => (
              <button
                key={b.question}
                type="button"
                onClick={() => onClassify(b.question)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-left hover:border-teal-300 hover:bg-teal-50/40"
              >
                <p className="text-sm font-medium text-slate-900">{b.question}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {b.primary_intent} · {b.entity || '—'} · {b.confidence_pct}%
                </p>
              </button>
            ))}
            <button
              type="button"
              onClick={() => onClassify('Should I buy Tata?')}
              className="w-full rounded-xl border border-amber-200 bg-amber-50/50 px-3 py-2 text-left hover:border-amber-300"
            >
              <p className="text-sm font-medium text-slate-900">Should I buy Tata?</p>
              <p className="mt-1 text-xs text-amber-700">Ambiguity control — must clarify</p>
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Primary Intent Taxonomy
          </p>
          <div className="mt-3 max-h-[480px] space-y-2 overflow-auto">
            {intents.map(([id, meta]) => (
              <div key={id} className="rounded-xl border border-slate-200 px-3 py-2">
                <p className="text-sm font-semibold text-slate-900">{meta.label}</p>
                <p className="text-xs text-teal-700">{meta.objective}</p>
                <p className="mt-1 text-xs text-slate-500">{meta.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          Quality Gates
        </p>
        <div className="mt-3 overflow-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="py-2 pr-3">Question</th>
                <th className="py-2 pr-3">Expected</th>
                <th className="py-2 pr-3">Actual</th>
                <th className="py-2 pr-3">Entity</th>
                <th className="py-2">Pass</th>
              </tr>
            </thead>
            <tbody>
              {(gates?.results || []).map((r) => (
                <tr key={r.question} className="border-t border-slate-100">
                  <td className="py-2 pr-3 text-slate-800">{r.question}</td>
                  <td className="py-2 pr-3 text-slate-600">{r.expected_primary}</td>
                  <td className="py-2 pr-3 text-slate-800">{r.actual_primary}</td>
                  <td className="py-2 pr-3 text-slate-600">{r.entity || '—'}</td>
                  <td className={`py-2 font-medium ${r.passed ? 'text-emerald-700' : 'text-rose-700'}`}>
                    {r.passed ? 'Yes' : 'No'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
