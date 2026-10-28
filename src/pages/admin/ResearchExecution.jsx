import { useCallback, useEffect, useState } from 'react';
import { Package, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  buildResearchExecution,
  getResearchExecutionDashboard,
  getResearchExecutionHealth,
  getResearchExecutionQualityGates,
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

export default function ResearchExecution() {
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
        getResearchExecutionHealth(),
        getResearchExecutionDashboard(),
        getResearchExecutionQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Research Execution Package');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onBuild = async (q) => {
    const nextQ = (q ?? question).trim();
    if (!nextQ) return;
    setBusy(true);
    setError('');
    setQuestion(nextQ);
    try {
      const row = await buildResearchExecution({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Build failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const contract = result?.research_contract;

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-700">
            RQ1 Sprint 10 · Institutional Research Execution Package · Final RQ1 · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Package className="h-6 w-6 text-emerald-700" />
            Research Execution Package
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Canonical immutable planning brief before any intelligence layer executes — the contract
            between planning and reasoning.
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
          label="Package completeness"
          value={gates ? pct(gates.package_completeness) : '—'}
          hint={gates ? `${gates.checked} scenarios` : undefined}
        />
        <Stat
          label="Avg package time"
          value={gates?.average_package_ms != null ? `${gates.average_package_ms} ms` : '—'}
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[280px] flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onBuild();
            }}
            placeholder="Institutional research question"
          />
          <Button onClick={() => onBuild()} disabled={busy}>
            {busy ? 'Building…' : 'Build IREP'}
          </Button>
        </div>
        {samples.length ? (
          <div className="flex flex-wrap gap-2">
            {samples.slice(0, 6).map((s) => (
              <button
                key={s.question}
                type="button"
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100"
                onClick={() => onBuild(s.question)}
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
            <Row label="Question" value={result.question?.original || result.question} />
            <Row label="Package ID" value={result.package_id} tone="good" />
            <Row
              label="Entity"
              value={
                result.entity?.canonical_name
                  ? `${result.entity.canonical_name}${result.entity.ticker ? ` (${result.entity.ticker})` : ''}`
                  : result.entity?.ticker || '—'
              }
            />
            <Row label="Objective" value={result.intent?.research_objective || result.intent?.primary_intent} />
            <Row
              label="Blueprint"
              value={result.blueprint?.report_name || result.blueprint?.report_type}
              tone="good"
            />
            <Row
              label="Readiness"
              value={result.validation?.readiness_state}
              tone={result.validation?.execution_allowed ? 'good' : 'bad'}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Analysts</h2>
              <ChipList items={result.analyst_plan?.required_analysts} tone="good" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Suppressed analysts</h2>
              <ChipList items={result.analyst_plan?.suppressed_analysts} tone="bad" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Layers</h2>
              <ChipList items={result.layer_plan?.required_layers} tone="good" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Providers / reuse</h2>
              <ChipList
                items={[
                  ...(result.api_plan?.providers || []),
                  ...((result.api_plan?.internal_reuse || []).map((x) => `reuse:${x}`) || []),
                ]}
              />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Section order</h2>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
                {(result.blueprint?.section_order || []).map((s) => (
                  <li key={s}>
                    {s}
                    {result.blueprint?.section_owner?.[s] ? (
                      <span className="text-slate-400"> · {result.blueprint.section_owner[s]}</span>
                    ) : null}
                  </li>
                ))}
              </ol>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Research Contract</h2>
              {contract ? (
                <div className="space-y-2 text-sm text-slate-700">
                  <Row label="Objective" value={contract.objective} />
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Must answer</p>
                    <ul className="mt-1 list-disc pl-5">
                      {(contract.must_answer || []).map((x) => (
                        <li key={x}>{x}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Must not</p>
                    <ul className="mt-1 list-disc pl-5 text-rose-800">
                      {(contract.must_not || []).map((x) => (
                        <li key={x}>{x}</li>
                      ))}
                    </ul>
                  </div>
                  <Row label="Success definition" value={contract.success_definition} />
                  <Row label="Min evidence" value={String(contract.minimum_evidence ?? '—')} />
                  <Row
                    label="Internal debate"
                    value={(contract.required_internal_debate || []).join(', ') || '—'}
                  />
                </div>
              ) : (
                <p className="text-sm text-slate-400">—</p>
              )}
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Execution plan</h2>
              <div className="grid gap-2 sm:grid-cols-2">
                <Row
                  label="Expected confidence"
                  value={pct(result.execution_plan?.expected_confidence)}
                  tone="good"
                />
                <Row
                  label="Est. runtime"
                  value={
                    result.execution_plan?.estimated_runtime_seconds != null
                      ? `${result.execution_plan.estimated_runtime_seconds}s`
                      : '—'
                  }
                />
                <Row
                  label="May execute"
                  value={result.execution_plan?.may_execute ? 'YES' : 'NO'}
                  tone={result.execution_plan?.may_execute ? 'good' : 'bad'}
                />
                <Row
                  label="Immutable"
                  value={result.immutable ? 'YES' : 'NO'}
                  tone={result.immutable ? 'good' : 'bad'}
                />
              </div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                Question → IREP → Analysts / Layers / Committee / CIO / Writer ·{' '}
                {result.metrics?.package_ms} ms
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Completeness" value={pct(gates.package_completeness)} tone="good" />
            <Row label="Consistency" value={pct(gates.package_consistency)} tone="good" />
            <Row label="No conflicts" value={pct(gates.no_conflicting_plans)} tone="good" />
            <Row label="Analyst plan" value={pct(gates.correct_analyst_plan)} tone="good" />
            <Row label="Layer plan" value={pct(gates.correct_layer_plan)} tone="good" />
            <Row label="Gate status" value={gates.ok ? 'PASS' : 'FAIL'} tone={gates.ok ? 'good' : 'bad'} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
