import { useCallback, useEffect, useState } from 'react';
import {
  ClipboardCheck,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  StepForward,
} from 'lucide-react';
import {
  getReasoningAuditDashboard,
  getReasoningAuditHealth,
  getReasoningAuditQualityGates,
  planReasoningAudit,
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
  if (status === 'PASS') return 'border-emerald-200 bg-emerald-50 text-emerald-900';
  if (status === 'PASS WITH OBSERVATIONS') return 'border-amber-200 bg-amber-50 text-amber-900';
  if (status === 'REVIEW REQUIRED') return 'border-orange-200 bg-orange-50 text-orange-900';
  return 'border-rose-200 bg-rose-50 text-rose-900';
}

export default function ReasoningAudit() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState('Should I buy HDFC Bank?');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [replayIndex, setReplayIndex] = useState(0);
  const [playing, setPlaying] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getReasoningAuditHealth(),
        getReasoningAuditDashboard(),
        getReasoningAuditQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Reasoning Audit');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const events = result?.reasoning_replay?.events || [];
  useEffect(() => {
    if (!playing || !events.length) return undefined;
    const timer = setInterval(() => {
      setReplayIndex((current) => {
        if (current >= events.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 1400);
    return () => clearInterval(timer);
  }, [playing, events.length]);

  const run = async (nextQuestion = question) => {
    const next = nextQuestion.trim();
    if (!next) return;
    setBusy(true);
    setError('');
    setQuestion(next);
    setPlaying(false);
    setReplayIndex(0);
    try {
      setResult(await planReasoningAudit({ question: next }));
    } catch (err) {
      setError(err?.message || 'Reasoning audit failed');
    } finally {
      setBusy(false);
    }
  };

  const scorecard = result?.reasoning_scorecard || {};
  const trace = result?.reasoning_trace || {};
  const activeEvent = events[replayIndex];

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1450px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-700">
            RQ2 Sprint 10 · Final Reasoning Certification · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <ClipboardCheck className="h-6 w-6 text-blue-700" />
            Reasoning Audit
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Prove that AGIB reasoned correctly: trace every conclusion, validate logic, assumptions,
            calibration, scope and policy, then replay the complete reasoning chain.
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
          label="Audited Chains"
          value={gates?.audited_reasoning_chains?.toLocaleString?.() || '—'}
          hint={gates ? `${gates.passed}/${gates.total} passed` : undefined}
        />
        <Stat
          label="Traceability"
          value={gates ? `${Math.round(Number(gates.traceability) * 100)}%` : '—'}
          hint={gates ? `${gates.avg_audit_ms} ms average` : undefined}
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
            {busy ? 'Auditing…' : 'Audit Reasoning'}
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
          <div className={`rounded-xl border p-5 ${statusClass(result.audit_status)}`}>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em]">Reasoning Certification</p>
            <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-3xl font-bold">{result.audit_status}</p>
                <p className="text-sm">{result.certification}</p>
              </div>
              <p className="text-4xl font-bold">{result.reasoning_score_pct}%</p>
            </div>
            <p className="mt-2 text-xs">
              Audit {result.registry?.audit_id} · confidence {result.confidence_pct}% ·{' '}
              {result.may_proceed ? 'May proceed' : 'Blocked from Committee'}
            </p>
          </div>

          <div>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Institutional Reasoning Scorecard
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {Object.entries(scorecard).map(([metric, score]) => (
                <div key={metric} className="rounded-xl border border-slate-200 bg-white p-3">
                  <p className="text-[10px] capitalize text-slate-500">{metric.replaceAll('_', ' ')}</p>
                  <p className="mt-1 text-xl font-semibold text-slate-900">{score}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-blue-700">
                  Reasoning Replay Engine
                </p>
                <p className="text-xs text-slate-600">
                  Replay {result.reasoning_replay?.replay_id} · {events.length} steps
                </p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setPlaying(!playing)}>
                  {playing ? <Pause className="mr-1 h-3 w-3" /> : <Play className="mr-1 h-3 w-3" />}
                  {playing ? 'Pause' : 'Replay'}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setReplayIndex((current) => Math.min(events.length - 1, current + 1))}
                >
                  <StepForward className="mr-1 h-3 w-3" /> Step
                </Button>
                <Button size="sm" variant="outline" onClick={() => { setPlaying(false); setReplayIndex(0); }}>
                  <RotateCcw className="mr-1 h-3 w-3" /> Restart
                </Button>
              </div>
            </div>
            {activeEvent ? (
              <div className="rounded-xl border border-blue-200 bg-white p-4">
                <p className="text-[10px] font-bold uppercase text-blue-700">
                  Step {activeEvent.sequence} · {activeEvent.stage}
                </p>
                <p className="mt-1 text-base font-semibold text-slate-900">{activeEvent.title}</p>
                <p className="mt-1 text-sm text-slate-600">{activeEvent.detail}</p>
                {activeEvent.before != null || activeEvent.after != null ? (
                  <p className="mt-2 text-xs font-semibold text-blue-800">
                    {activeEvent.before != null ? `${Math.round(Number(activeEvent.before) * 100)}%` : '—'} →{' '}
                    {activeEvent.after != null ? `${Math.round(Number(activeEvent.after) * 100)}%` : '—'}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div className="flex gap-1">
              {events.map((event, index) => (
                <button
                  key={event.sequence}
                  type="button"
                  aria-label={`Replay step ${event.sequence}`}
                  onClick={() => { setPlaying(false); setReplayIndex(index); }}
                  className={`h-2 flex-1 rounded-full ${index <= replayIndex ? 'bg-blue-500' : 'bg-blue-100'}`}
                />
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Reasoning Timeline · {trace.completeness_pct}% complete
            </p>
            <div className="flex flex-wrap gap-2">
              {(trace.nodes || []).map((node, index) => (
                <div key={node.id} className={`rounded-lg border px-3 py-2 text-xs ${
                  node.present ? 'border-emerald-200 bg-emerald-50' : 'border-rose-200 bg-rose-50'
                }`}>
                  <p className="font-semibold">{index + 1}. {node.stage}</p>
                  <p className="text-[10px] text-slate-500">{node.summary}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Evidence Trace
              </p>
              <p className="text-2xl font-semibold">{result.traceability?.traceability_pct}%</p>
              <p className="text-xs text-slate-500">
                {result.traceability?.traceable_count}/{result.traceability?.conclusion_count} conclusions traced ·{' '}
                {result.traceability?.orphan_count} orphans
              </p>
              {(result.traceability?.conclusion_traces || []).slice(0, 6).map((item) => (
                <div key={item.conclusion_id} className="rounded-lg border border-slate-100 bg-slate-50 p-2">
                  <p className="text-xs font-semibold">{item.conclusion_type}</p>
                  <p className="text-[10px] text-slate-600">{item.conclusion}</p>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Logic Checks
              </p>
              {Object.entries(result.logic?.checks || {}).map(([check, passed]) => (
                <div key={check} className="flex justify-between text-sm">
                  <span className="capitalize">{check.replaceAll('_', ' ')}</span>
                  <strong className={passed ? 'text-emerald-700' : 'text-rose-700'}>
                    {passed ? 'PASS' : 'FAIL'}
                  </strong>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Stat label="Assumption Quality" value={`${result.assumptions?.score_pct}%`} hint={`${result.assumptions?.assumption_count || 0} assumptions`} />
            <Stat label="Calibration" value={`${result.calibration?.score_pct}%`} hint={`${result.calibration?.calibrated_count || 0}/${result.calibration?.belief_count || 0} calibrated`} />
            <Stat label="Analyst Scope" value={`${result.scope?.score_pct}%`} hint={`${result.scope?.violation_count || 0} violations`} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Policy</p>
              {Object.entries(result.policy?.checks || {}).map(([check, passed]) => (
                <p key={check} className="mt-1 text-sm">
                  {passed ? '✓' : '✕'} {check.replaceAll('_', ' ')}
                </p>
              ))}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Required Actions</p>
              {(result.required_actions || []).length ? (
                result.required_actions.map((action) => <p key={action} className="mt-1 text-sm">• {action}</p>)
              ) : (
                <p className="mt-1 text-sm text-emerald-700">No blocking actions.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
