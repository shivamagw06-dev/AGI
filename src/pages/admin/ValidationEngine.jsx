import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, ShieldAlert, ShieldQuestion } from 'lucide-react';
import {
  getValidationEngineDashboard,
  getValidationEngineHealth,
  getValidationEngineQualityGates,
  validateValidationEngine,
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

function stateTone(state) {
  if (state === 'READY') return 'good';
  if (state === 'READY_WITH_WARNINGS') return 'warn';
  if (state === 'CLARIFICATION_REQUIRED' || state === 'BLOCKED') return 'bad';
  return undefined;
}

export default function ValidationEngine() {
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
        getValidationEngineHealth(),
        getValidationEngineDashboard(),
        getValidationEngineQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Validation Engine');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onValidate = async (q) => {
    const nextQ = (q ?? question).trim();
    if (!nextQ) return;
    setBusy(true);
    setError('');
    setQuestion(nextQ);
    try {
      const row = await validateValidationEngine({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Validation failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const memo = result?.readiness_memo;

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-rose-700">
            RQ1 Sprint 9 · Institutional Validation & Clarification Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <ShieldQuestion className="h-6 w-6 text-rose-700" />
            Validation Engine
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Final gate before research executes — readiness score, warnings, clarifications, and
            Research Readiness Memo.
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
          label="Validation accuracy"
          value={gates ? pct(gates.validation_accuracy) : '—'}
          hint={gates ? `${gates.checked} scenarios` : undefined}
        />
        <Stat
          label="False ready rate"
          value={gates ? pct(gates.false_ready_rate) : '—'}
          hint={`Avg ${gates?.average_runtime_ms ?? '—'} ms`}
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[280px] flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onValidate();
            }}
            placeholder="Institutional research question"
          />
          <Button onClick={() => onValidate()} disabled={busy}>
            {busy ? 'Validating…' : 'Validate readiness'}
          </Button>
        </div>
        {samples.length ? (
          <div className="flex flex-wrap gap-2">
            {samples.slice(0, 8).map((s) => (
              <button
                key={s.question}
                type="button"
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100"
                onClick={() => onValidate(s.question)}
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
            <Row
              label="Readiness state"
              value={result.readiness_state}
              tone={stateTone(result.readiness_state)}
            />
            <Row label="Readiness score" value={pct(result.overall_readiness)} tone="good" />
            <Row
              label="Execution allowed?"
              value={result.execution_allowed ? 'YES' : 'NO'}
              tone={result.execution_allowed ? 'good' : 'bad'}
            />
            <Row label="Confidence" value={pct(result.confidence)} />
            <Row
              label="Validation time"
              value={
                result.metrics?.validation_ms != null ? `${result.metrics.validation_ms} ms` : '—'
              }
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Validation checks</h2>
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  ['Question', result.question_status],
                  ['Entity', result.entity_status],
                  ['Intent', result.intent_status],
                  ['Context', result.context_status],
                  ['Evidence', result.evidence_status],
                  ['Routing', result.routing_status],
                  ['Blueprint', result.blueprint_status],
                  ['Policy', result.policy_status],
                ].map(([label, status]) => (
                  <Row
                    key={label}
                    label={label}
                    value={`${status?.status || '—'} · ${pct(status?.score)}`}
                    tone={
                      status?.status === 'valid' || status?.status === 'compliant' || status?.status === 'sufficient'
                        ? 'good'
                        : status?.status === 'warning' || status?.status === 'inferred'
                          ? 'warn'
                          : 'bad'
                    }
                  />
                ))}
              </div>
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Warnings</h2>
              {(result.warnings || []).length ? (
                <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
                  {result.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">None</p>
              )}
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Clarifications</h2>
              {(result.clarifications || []).length ? (
                <ul className="space-y-2 text-sm text-rose-800">
                  {result.clarifications.map((c) => (
                    <li key={c.prompt} className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2">
                      <p className="text-[10px] font-bold uppercase tracking-wide text-rose-500">{c.type}</p>
                      <p className="mt-0.5">{c.prompt}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">None</p>
              )}
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Research Readiness Memo</h2>
              {memo ? (
                <div className="space-y-3 text-sm text-slate-700">
                  <Row label="Status" value={memo.status} tone={stateTone(memo.status)} />
                  <Row label="Readiness" value={`${memo.readiness_pct ?? '—'}%`} tone="good" />
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Strengths</p>
                    <ul className="mt-1 list-disc pl-5 text-emerald-800">
                      {(memo.strengths || []).map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Weaknesses</p>
                    <ul className="mt-1 list-disc pl-5 text-amber-800">
                      {(memo.weaknesses || []).length ? (
                        memo.weaknesses.map((s) => <li key={s}>{s}</li>)
                      ) : (
                        <li className="text-slate-400 list-none -ml-5">None</li>
                      )}
                    </ul>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Risks</p>
                    <ul className="mt-1 list-disc pl-5 text-rose-800">
                      {(memo.risks || []).length ? (
                        memo.risks.map((s) => <li key={s}>{s}</li>)
                      ) : (
                        <li className="text-slate-400 list-none -ml-5">None</li>
                      )}
                    </ul>
                  </div>
                  <Row
                    label="Recommended analysts"
                    value={(memo.recommended_analysts || []).join(', ') || '—'}
                  />
                  <Row label="Suppressed" value={(memo.suppressed || []).join(', ') || '—'} />
                  <Row label="Expected confidence" value={pct(memo.expected_confidence)} />
                  <Row
                    label="Expected runtime"
                    value={
                      memo.expected_runtime_seconds != null
                        ? `${memo.expected_runtime_seconds}s`
                        : '—'
                    }
                  />
                </div>
              ) : (
                <p className="text-sm text-slate-400">—</p>
              )}
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                Question → Validation → {result.execution_allowed ? 'Ready → Research' : 'Paused'}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Validation accuracy" value={pct(gates.validation_accuracy)} tone="good" />
            <Row label="Clarification accuracy" value={pct(gates.clarification_accuracy)} tone="good" />
            <Row label="False ready" value={pct(gates.false_ready_rate)} tone="good" />
            <Row label="False block" value={pct(gates.false_block_rate)} tone="good" />
            <Row
              label="Avg runtime"
              value={gates.average_runtime_ms != null ? `${gates.average_runtime_ms} ms` : '—'}
              tone="good"
            />
            <Row label="Gate status" value={gates.ok ? 'PASS' : 'FAIL'} tone={gates.ok ? 'good' : 'bad'} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
