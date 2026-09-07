import { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getDecisionReadinessDashboard,
  getDecisionReadinessHealth,
  getDecisionReadinessQualityGates,
  planDecisionReadiness,
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

function statusClass(status) {
  if (status === 'READY') return 'border-emerald-200 bg-emerald-50 text-emerald-900';
  if (status === 'READY WITH CONDITIONS') return 'border-amber-200 bg-amber-50 text-amber-900';
  if (status === 'RESEARCH REQUIRED') return 'border-orange-200 bg-orange-50 text-orange-900';
  return 'border-rose-200 bg-rose-50 text-rose-900';
}

export default function DecisionReadiness() {
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
        getDecisionReadinessHealth(),
        getDecisionReadinessDashboard(),
        getDecisionReadinessQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Decision Readiness');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (nextQuestion = question) => {
    const next = nextQuestion.trim();
    if (!next) return;
    setBusy(true);
    setError('');
    setQuestion(next);
    try {
      setResult(await planDecisionReadiness({ question: next, falsification_complete: true }));
    } catch (err) {
      setError(err?.message || 'Decision readiness failed');
    } finally {
      setBusy(false);
    }
  };

  const heatMap = result?.decision_heat_map || [];
  const packageData = result?.decision_package || {};
  const dimensions = result?.dimensions || {};
  const conditions = result?.decision_conditions || [];

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1450px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-700">
            RQ2 Sprint 9 · Final Pre-Committee Quality Gate · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <ShieldCheck className="h-6 w-6 text-emerald-700" />
            Decision Readiness
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Determine whether evidence, reasoning, debate, portfolio fit, monitoring and policy are
            sufficient for an institutional decision—and separate thesis quality from capital readiness.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <ShieldAlert className="h-4 w-4 shrink-0" /> {error}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Status" value={health?.status || (loading ? '…' : '—')} />
        <Stat label="Version" value={health?.version || '—'} hint={health?.sprint_name} />
        <Stat
          label="Scenarios"
          value={gates?.decision_scenarios?.toLocaleString?.() || '—'}
          hint={gates ? `${gates.passed}/${gates.total} passed` : undefined}
        />
        <Stat
          label="Classification Accuracy"
          value={gates ? `${Math.round(Number(gates.readiness_classification) * 100)}%` : '—'}
          hint={gates ? `${gates.avg_readiness_ms} ms average` : undefined}
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && run()}
          />
          <Button onClick={() => run()} disabled={busy}>
            {busy ? 'Evaluating…' : 'Evaluate Decision Readiness'}
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {(dashboard?.samples || []).map((sample) => (
            <button
              key={sample.question}
              type="button"
              className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs"
              onClick={() => run(sample.question)}
            >
              {sample.question}
            </button>
          ))}
        </div>
      </div>

      {result ? (
        <div className="space-y-5">
          <div className={`rounded-xl border p-5 ${statusClass(result.decision_status)}`}>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em]">Decision Status</p>
            <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
              <p className="text-3xl font-bold">{result.decision_status}</p>
              <p className="text-4xl font-bold">{result.readiness_score_pct}%</p>
            </div>
            <p className="mt-2 text-sm">{packageData.executive_summary}</p>
          </div>

          <div>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Decision Heat Map
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {heatMap.map((dimension) => (
                <div key={dimension.dimension} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex justify-between gap-2">
                    <p className="font-semibold text-slate-900">{dimension.dimension}</p>
                    <strong>{dimension.score_pct}</strong>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-slate-100">
                    <div
                      className={`h-2 rounded-full ${
                        dimension.score_pct >= 85
                          ? 'bg-emerald-500'
                          : dimension.score_pct >= 70
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                      }`}
                      style={{ width: `${dimension.score_pct}%` }}
                    />
                  </div>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {dimension.state}{dimension.weight ? ` · weight ${Math.round(dimension.weight * 100)}%` : ' · reported separately'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Stat
              label="Thesis / Decision Readiness"
              value={`${result.readiness_score_pct}%`}
              hint={result.decision_status}
            />
            <Stat
              label="Capital Allocation Readiness"
              value={`${result.capital_allocation_readiness_pct}%`}
              hint={result.capital_state}
            />
            <Stat
              label="Confidence"
              value={`${result.confidence_pct}%`}
              hint={`Uncertainty ${Math.round(Number(result.uncertainty || 0) * 100)}%`}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Supporting Factors
              </p>
              {(result.strengths || []).slice(0, 10).map((item, index) => (
                <p key={`${item.factor}-${index}`} className="text-sm text-emerald-800">
                  ✓ <strong>{item.dimension}</strong> — {item.factor}
                </p>
              ))}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Limiting Factors
              </p>
              {(result.weaknesses || []).slice(0, 10).map((item, index) => (
                <p key={`${item.factor}-${index}`} className="text-sm text-rose-800">
                  • <strong>{item.dimension}</strong> — {item.factor}
                </p>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Objective Go / No-Go Conditions
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {conditions.map((condition) => (
                <div
                  key={condition.condition}
                  className={`rounded-lg border px-3 py-2 ${
                    condition.go
                      ? 'border-emerald-100 bg-emerald-50/50'
                      : 'border-rose-100 bg-rose-50/50'
                  }`}
                >
                  <div className="flex justify-between gap-2">
                    <p className="text-xs font-semibold text-slate-800">{condition.condition}</p>
                    <strong className={condition.go ? 'text-emerald-700' : 'text-rose-700'}>
                      {condition.result}
                    </strong>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">
                    Current {condition.current_pct}% · threshold {condition.threshold_pct}% · distance{' '}
                    {condition.distance_pp > 0 ? '+' : ''}{condition.distance_pp} pp
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Gate Detail
              </p>
              {Object.entries(dimensions).map(([name, gate]) => (
                <div key={name} className="flex justify-between gap-2 text-sm">
                  <span>{name}</span>
                  <span className={gate.passed ? 'text-emerald-700' : 'text-amber-700'}>
                    {gate.score_pct} · {gate.passed ? 'PASS' : 'CONDITION'}
                  </span>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Required Follow-Up
              </p>
              {(result.required_follow_up || []).slice(0, 12).map((item, index) => (
                <p key={`${item}-${index}`} className="text-sm text-slate-700">• {item}</p>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Monitoring Plan
            </p>
            <p className="mt-1 text-sm text-slate-800">
              {result.monitoring_plan?.review_frequency} review · next {result.monitoring_plan?.next_review}
            </p>
            <p className="mt-1 text-xs text-slate-600">{result.monitoring_plan?.evidence_refresh}</p>
            <p className="text-xs text-slate-600">{result.monitoring_plan?.portfolio_review}</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
