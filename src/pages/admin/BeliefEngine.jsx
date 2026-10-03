import { useCallback, useEffect, useState } from 'react';
import { Gauge, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getBeliefEngineDashboard,
  getBeliefEngineHealth,
  getBeliefEngineQualityGates,
  planBeliefEngine,
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

function stateTone(state) {
  if (['Strongly Supported', 'Supported', 'Leaning Positive'].includes(state)) return 'good';
  if (['Neutral', 'Leaning Negative'].includes(state)) return 'warn';
  return 'bad';
}

export default function BeliefEngine() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState('Should I buy HDFC Bank?');
  const [activeId, setActiveId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getBeliefEngineHealth(),
        getBeliefEngineDashboard(),
        getBeliefEngineQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Belief Engine');
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
      const row = await planBeliefEngine({ question: nextQ });
      setResult(row);
      setActiveId(row?.beliefs?.[0]?.hypothesis_id || null);
    } catch (err) {
      setError(err?.message || 'Belief update failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const beliefs = result?.beliefs || [];
  const active = beliefs.find((b) => b.hypothesis_id === activeId) || beliefs[0];

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-fuchsia-700">
            RQ2 Sprint 6 · Bayesian Belief & Confidence Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Gauge className="h-6 w-6 text-fuchsia-700" />
            Belief Engine
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Convert tested and challenged hypotheses into calibrated institutional beliefs —
            prior → evidence update → posterior, with confidence, uncertainty, and drift.
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
          label="Beliefs updated"
          value={gates?.beliefs_updated?.toLocaleString?.() || gates?.beliefs_updated || '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Avg update"
          value={gates?.avg_update_ms != null ? `${gates.avg_update_ms} ms` : '—'}
          hint={`target ≤ ${gates?.target_update_ms ?? 40} ms`}
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
          />
          <Button onClick={() => onPlan()} disabled={busy}>
            {busy ? 'Updating…' : 'Update Beliefs'}
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
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Beliefs" value={result.belief_count} />
            <Stat
              label="Material drifts"
              value={result.drift_summary?.material_drift_count ?? '—'}
              hint={
                result.drift_summary?.requires_committee_attention
                  ? 'Committee attention flagged'
                  : 'Stable package'
              }
            />
            <Stat
              label="Mean posterior"
              value={
                result.metrics?.mean_posterior != null
                  ? `${Math.round(Number(result.metrics.mean_posterior) * 100)}%`
                  : '—'
              }
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {beliefs.map((b) => (
              <button
                key={b.hypothesis_id}
                type="button"
                onClick={() => setActiveId(b.hypothesis_id)}
                className={`rounded-lg border px-3 py-2 text-left text-xs max-w-xs ${
                  (active?.hypothesis_id || activeId) === b.hypothesis_id
                    ? 'border-fuchsia-300 bg-fuchsia-50 text-fuchsia-900'
                    : 'border-slate-200 bg-white text-slate-700'
                }`}
              >
                <p className="font-bold">
                  {b.hypothesis_id} · {b.belief_state}
                </p>
                <p className="mt-0.5 line-clamp-2">{b.hypothesis}</p>
                <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">
                  {Math.round(Number(b.prior_belief || 0) * 100)}% →{' '}
                  {b.posterior_belief_pct ?? Math.round(Number(b.posterior_belief || 0) * 100)}%
                </p>
              </button>
            ))}
          </div>

          {active ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-4">
                <Stat
                  label="Prior Belief"
                  value={`${active.prior_belief_pct ?? Math.round(Number(active.prior_belief || 0) * 100)}%`}
                />
                <Stat
                  label="Posterior Belief"
                  value={`${active.posterior_belief_pct ?? Math.round(Number(active.posterior_belief || 0) * 100)}%`}
                  hint={`Δ ${active.delta > 0 ? '+' : ''}${Math.round(Number(active.delta || 0) * 100)} pp`}
                />
                <Stat
                  label="Confidence"
                  value={`${active.confidence_pct ?? Math.round(Number(active.confidence || 0) * 100)}%`}
                  hint={active.calibration?.confidence_band}
                />
                <Stat
                  label="Uncertainty"
                  value={pct((active.uncertainty || {}).overall_uncertainty)}
                  hint={(active.uncertainty || {}).band}
                />
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Belief State
                </p>
                <ChipList items={[active.belief_state]} tone={stateTone(active.belief_state)} />
                <p className="text-sm text-slate-700">{active.decision_hint}</p>
                <p className="text-xs text-slate-500">
                  Drift: {(active.drift || {}).note || '—'} (
                  {(active.drift || {}).drift_level || 'n/a'})
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Probability History
                </p>
                <div className="space-y-2 max-h-72 overflow-auto">
                  {(active.history || []).map((h, idx) => (
                    <div key={`${h.step}-${idx}`} className="flex gap-3 text-sm">
                      <div className="w-28 shrink-0 text-[10px] uppercase tracking-wide text-slate-400">
                        {h.step}
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">
                          {h.probability != null
                            ? `${Math.round(Number(h.probability) * 100)}%`
                            : '—'}
                          {h.belief_state ? ` · ${h.belief_state}` : ''}
                        </p>
                        <p className="text-xs text-slate-600">{h.note}</p>
                        {h.log_lr != null ? (
                          <p className="text-[10px] text-fuchsia-700">log LR {h.log_lr}</p>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          Belief States
        </p>
        <ChipList items={dashboard?.belief_states || []} tone="warn" />
        <p className="text-xs text-slate-500 pt-1">
          Soft-wired after Falsification and before analyst opinions. Not a top-level intelligence
          layer.
        </p>
      </div>
    </div>
  );
}
