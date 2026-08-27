import { useCallback, useEffect, useState } from 'react';
import { Database, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getAcquisitionPlannerDashboard,
  getAcquisitionPlannerHealth,
  getAcquisitionPlannerQualityGates,
  planAcquisitionPlanner,
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

function VisualPlan({ steps }) {
  if (!steps?.length) return <p className="text-sm text-slate-400">—</p>;
  return (
    <div className="space-y-2">
      {steps.map((s, idx) => (
        <div key={`${s.evidence_requirement}-${s.selected_provider}-${idx}`} className="text-sm">
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
            <span className="font-semibold text-slate-800">{s.evidence_requirement}</span>
            <span className="text-slate-300">→</span>
            <span className="text-sky-800">{s.selected_provider}</span>
            <span className="text-slate-300">→</span>
            <span className={s.retrieved_evidence === 'reuse' ? 'text-emerald-700' : 'text-violet-700'}>
              {s.retrieved_evidence}
            </span>
            <span className="text-slate-300">→</span>
            <span className="text-slate-600">{s.destination_layer}</span>
          </div>
          {idx < steps.length - 1 ? <div className="py-0.5 text-center text-slate-300">↓</div> : null}
        </div>
      ))}
    </div>
  );
}

export default function AcquisitionPlanner() {
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
        getAcquisitionPlannerHealth(),
        getAcquisitionPlannerDashboard(),
        getAcquisitionPlannerQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Acquisition Planner');
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
      const row = await planAcquisitionPlanner({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Plan failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-700">
            RQ1 Sprint 7 · Institutional Acquisition & API Planning Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Database className="h-6 w-6 text-teal-700" />
            Acquisition Planner
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Determine what evidence must be acquired, from where, in what order, and why — before any
            external API is called.
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
          label="Provider selection"
          value={gates ? pct(gates.provider_selection_accuracy) : '—'}
          hint={gates ? `${gates.checked} scenarios` : undefined}
        />
        <Stat
          label="API reduction"
          value={gates ? pct(gates.average_api_reduction) : '—'}
          hint={`Avg plan ${gates?.average_planning_ms ?? '—'} ms`}
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
            {busy ? 'Planning…' : 'Plan acquisition'}
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
            <Row label="Research Question" value={result.question} />
            <Row label="Primary Objective" value={result.primary_objective} tone="good" />
            <Row label="Confidence" value={pct(result.confidence)} tone="good" />
            <Row
              label="Expected runtime"
              value={
                result.expected_runtime?.total_ms != null
                  ? `${result.expected_runtime.total_ms} ms`
                  : '—'
              }
            />
            <Row
              label="API calls / budget"
              value={`${result.evidence_budget?.api_calls_used ?? '—'} / ${result.evidence_budget?.maximum_api_calls ?? '—'}`}
            />
            <Row
              label="Expected quality"
              value={pct(result.expected_quality?.expected_quality)}
              tone="good"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Evidence required</h2>
              <ChipList
                items={(result.required_data || []).map((r) => r.label || r.evidence_key)}
                tone="good"
              />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Selected providers</h2>
              <ChipList
                items={(result.selected_providers || []).map(
                  (p) => `${p.provider_name || p.provider} (${p.evidence_key})`,
                )}
              />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Internal reuse</h2>
              <ChipList
                items={(result.reuse_internal_layers || []).map(
                  (r) => `${(r.provider_name || r.provider || '').toUpperCase()} ← ${r.evidence_key}`,
                )}
                tone="good"
              />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Skipped APIs</h2>
              <ChipList
                items={(result.skipped_apis || [])
                  .slice(0, 10)
                  .map((s) => s.provider || s.evidence_key || s.action)}
                tone="warn"
              />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Visual plan</h2>
              <p className="text-xs text-slate-500">
                Question → Evidence → Provider → Retrieved → Destination layer
              </p>
              <VisualPlan steps={result.visual_plan || []} />
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Fallback chain</h2>
              <div className="max-h-40 space-y-1 overflow-auto text-xs text-slate-600">
                {(result.fallback_chains || []).slice(0, 8).map((c) => (
                  <div key={c.evidence_key}>
                    <span className="font-semibold text-slate-800">{c.evidence_key}</span>:{' '}
                    {(c.authority_ranked || []).join(' → ') || '—'}
                  </div>
                ))}
              </div>
              <div className="rounded-xl border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
                Plan only · API reduction {pct(result.metrics?.api_reduction)} · duplicates{' '}
                {result.metrics?.duplicate_fetches ?? 0} · {result.metrics?.planning_ms} ms
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Provider selection" value={pct(gates.provider_selection_accuracy)} tone="good" />
            <Row label="Internal reuse" value={pct(gates.internal_reuse_accuracy)} tone="good" />
            <Row label="Authority" value={pct(gates.authority_compliance)} tone="good" />
            <Row label="Fallback" value={pct(gates.fallback_success)} tone="good" />
            <Row label="API reduction" value={pct(gates.average_api_reduction)} tone="good" />
            <Row label="Gate status" value={gates.ok ? 'PASS' : 'FAIL'} tone={gates.ok ? 'good' : 'bad'} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
