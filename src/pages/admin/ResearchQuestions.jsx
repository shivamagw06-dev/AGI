import { useCallback, useEffect, useState } from 'react';
import { ListChecks, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getResearchQuestionsDashboard,
  getResearchQuestionsHealth,
  getResearchQuestionsQualityGates,
  planResearchQuestions,
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
        <span key={String(item)} className={`rounded-md border px-2 py-0.5 text-xs ${cls}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function priorityTone(p) {
  if (p === 'Critical') return 'bad';
  if (p === 'Important') return 'warn';
  if (p === 'Supporting') return 'good';
  return undefined;
}

function QuestionRow({ q }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 space-y-2">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            {q.id} · {q.type} · {q.priority}
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{q.question || q.research_question}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-lg font-semibold text-slate-900">{q.decision_impact ?? '—'}/10</p>
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Decision impact</p>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Analyst Owner</p>
          <p className="mt-0.5 text-sm text-slate-800">{q.analyst_owner || '—'}</p>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Status</p>
          <p className="mt-0.5 text-sm text-slate-800">{q.status || '—'}</p>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Confidence</p>
          <p className="mt-0.5 text-sm text-slate-800">
            {q.confidence != null ? `${Math.round(Number(q.confidence) * 100)}%` : '—'}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Evidence Needed</p>
          <div className="mt-1">
            <ChipList items={q.required_evidence || []} tone={priorityTone(q.priority)} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ResearchQuestions() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState('Should I buy HDFC Bank?');
  const [activeHyp, setActiveHyp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getResearchQuestionsHealth(),
        getResearchQuestionsDashboard(),
        getResearchQuestionsQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Research Questions');
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
      const row = await planResearchQuestions({ question: nextQ });
      setResult(row);
      const first = row?.hypothesis_question_sets?.[0]?.hypothesis_id || null;
      setActiveHyp(first);
    } catch (err) {
      setError(err?.message || 'Research question generation failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const sets = result?.hypothesis_question_sets || [];
  const active = sets.find((s) => s.hypothesis_id === activeHyp) || sets[0];
  const coverage = result?.coverage || {};

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-700">
            RQ2 Sprint 2 · Institutional Research Question Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <ListChecks className="h-6 w-6 text-cyan-700" />
            Research Questions
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            After hypotheses are generated, build the investigation plan — question trees, decision
            impact scores, and evidence-mapped questions analysts must answer before belief.
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
          label="Coverage"
          value={gates ? pct(gates.coverage) : '—'}
          hint={gates ? `${gates.passed}/${gates.total} sets` : undefined}
        />
        <Stat
          label="Questions generated"
          value={gates?.research_questions_generated?.toLocaleString?.() || gates?.research_questions_generated || '—'}
          hint={gates ? `avg ${gates.avg_generation_ms} ms` : undefined}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Question</p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onPlan();
            }}
            placeholder="Should I buy HDFC Bank?"
          />
          <Button onClick={() => onPlan()} disabled={busy}>
            {busy ? 'Generating…' : 'Generate Research Questions'}
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {samples.map((s) => (
            <button
              key={s.question}
              type="button"
              className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100"
              onClick={() => onPlan(s.question)}
            >
              {s.question}
            </button>
          ))}
        </div>
      </div>

      {result ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Hypotheses" value={result.hypothesis_count} />
            <Stat label="Research Questions" value={result.research_question_count} />
            <Stat label="Unanswered" value={coverage.questions_unanswered} />
            <Stat
              label="Coverage %"
              value={coverage.coverage_pct != null ? pct(coverage.coverage_pct) : '0%'}
              hint="answered / generated"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {sets.map((s) => (
              <button
                key={s.hypothesis_id}
                type="button"
                onClick={() => setActiveHyp(s.hypothesis_id)}
                className={`rounded-lg border px-3 py-2 text-left text-xs max-w-xs ${
                  (active?.hypothesis_id || activeHyp) === s.hypothesis_id
                    ? 'border-cyan-300 bg-cyan-50 text-cyan-900'
                    : 'border-slate-200 bg-white text-slate-700'
                }`}
              >
                <p className="font-bold">{s.hypothesis_id}</p>
                <p className="mt-0.5 line-clamp-2">{s.hypothesis}</p>
                <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">
                  {s.question_count} questions
                </p>
              </button>
            ))}
          </div>

          {active ? (
            <div className="space-y-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Hypothesis
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{active.hypothesis}</p>
                <p className="mt-2 text-xs text-slate-600">
                  <span className="font-semibold">Question tree:</span>{' '}
                  {(active.question_tree || {}).proof_chain || '—'}
                </p>
              </div>

              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Research Questions ↓ Priority ↓ Analyst Owner ↓ Evidence Needed ↓ Status ↓ Confidence
              </p>
              {(active.research_questions || []).map((q) => (
                <QuestionRow key={q.id} q={q} />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          Five Quality Rules · Enhancements
        </p>
        <ChipList
          items={
            dashboard?.five_quality_rules || [
              'specific',
              'answerable',
              'evidence_backed',
              'decision_relevant',
              'non_overlapping',
            ]
          }
          tone="good"
        />
        <ChipList items={['question_tree', 'decision_impact_score']} tone="warn" />
        <p className="text-xs text-slate-500 pt-1">
          Soft-wired after Hypothesis Generation and before Evidence Collection. Not a top-level
          intelligence layer.
        </p>
      </div>
    </div>
  );
}
