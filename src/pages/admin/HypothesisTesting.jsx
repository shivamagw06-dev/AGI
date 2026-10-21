import { useCallback, useEffect, useState } from 'react';
import { FlaskConical, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getHypothesisTestingDashboard,
  getHypothesisTestingHealth,
  getHypothesisTestingQualityGates,
  planHypothesisTesting,
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

function effectTone(effect) {
  if (['Confirms', 'Supports', 'Weakly Supports'].includes(effect)) return 'good';
  if (['Questions', 'Contradicts', 'Refutes'].includes(effect)) return 'bad';
  return 'warn';
}

function statusTone(status) {
  if (status === 'Supported') return 'good';
  if (status === 'Partially Supported' || status === 'Inconclusive') return 'warn';
  return 'bad';
}

export default function HypothesisTesting() {
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
        getHypothesisTestingHealth(),
        getHypothesisTestingDashboard(),
        getHypothesisTestingQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Hypothesis Testing');
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
      const row = await planHypothesisTesting({ question: nextQ });
      setResult(row);
      setActiveId(row?.tested_hypotheses?.[0]?.id || null);
    } catch (err) {
      setError(err?.message || 'Hypothesis testing failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const tested = result?.tested_hypotheses || [];
  const active = tested.find((h) => h.id === activeId) || tested[0];

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-700">
            RQ2 Sprint 4 · Institutional Hypothesis Testing Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <FlaskConical className="h-6 w-6 text-indigo-700" />
            Hypothesis Testing
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Test evidence against every hypothesis before analysts form opinions — qualitative
            effects, probability updates, and a full reasoning ledger.
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
          label="Tested hypotheses"
          value={gates?.tested_hypotheses?.toLocaleString?.() || gates?.tested_hypotheses || '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Avg testing"
          value={gates?.avg_testing_ms != null ? `${gates.avg_testing_ms} ms` : '—'}
          hint={`target ≤ ${gates?.target_testing_ms ?? 50} ms`}
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
            {busy ? 'Testing…' : 'Test Hypotheses'}
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
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500 mb-3">
              Hypothesis → Evidence → Support → Contradictions → Probability Update → Result
            </p>
            <div className="flex flex-wrap gap-2">
              {(dashboard?.visual_flow || []).map((step, i) => (
                <span key={step} className="text-xs text-slate-600">
                  {i > 0 ? ' → ' : ''}
                  <span className="rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-indigo-900">
                    {step}
                  </span>
                </span>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {tested.map((h) => (
              <button
                key={h.id}
                type="button"
                onClick={() => setActiveId(h.id)}
                className={`rounded-lg border px-3 py-2 text-left text-xs max-w-xs ${
                  (active?.id || activeId) === h.id
                    ? 'border-indigo-300 bg-indigo-50 text-indigo-900'
                    : 'border-slate-200 bg-white text-slate-700'
                }`}
              >
                <p className="font-bold">
                  {h.id} · {h.status}
                </p>
                <p className="mt-0.5 line-clamp-2">{h.hypothesis}</p>
                <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">
                  {Math.round(Number(h.initial_confidence || 0) * 100)}% →{' '}
                  {h.updated_probability_pct ?? Math.round(Number(h.updated_probability || 0) * 100)}%
                </p>
              </button>
            ))}
          </div>

          {active ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-4">
                <Stat
                  label="Updated Confidence"
                  value={`${active.updated_probability_pct ?? Math.round(Number(active.updated_probability || 0) * 100)}%`}
                  hint={`from ${Math.round(Number(active.initial_confidence || 0) * 100)}%`}
                />
                <Stat label="Support Score" value={active.support_score} />
                <Stat label="Contradiction Score" value={active.contradiction_score} />
                <Stat
                  label="Status"
                  value={active.status}
                  hint={active.decision}
                />
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                    Supporting Evidence
                  </p>
                  {(active.supporting_evidence || []).map((e) => (
                    <div key={e.id} className="rounded-lg border border-emerald-100 bg-emerald-50/50 px-3 py-2">
                      <div className="flex justify-between gap-2">
                        <p className="text-sm text-slate-800">{e.text}</p>
                        <ChipList items={[e.effect || 'Supports']} tone="good" />
                      </div>
                      <p className="mt-1 text-[10px] text-slate-500">Support {e.support_score}</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                    Contradicting Evidence
                  </p>
                  {(active.contradicting_evidence || []).map((e) => (
                    <div key={e.id} className="rounded-lg border border-rose-100 bg-rose-50/50 px-3 py-2">
                      <div className="flex justify-between gap-2">
                        <p className="text-sm text-slate-800">{e.text}</p>
                        <ChipList items={[e.effect || 'Contradicts']} tone="bad" />
                      </div>
                      <p className="mt-1 text-[10px] text-slate-500">
                        Contradiction {e.contradiction_score}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Missing Evidence
                </p>
                <ChipList items={active.missing_evidence || []} tone="warn" />
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Evidence Effects
                </p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(active.effect_breakdown || {}).map(([effect, n]) =>
                    n ? (
                      <span
                        key={effect}
                        className={`rounded-md border px-2 py-0.5 text-xs ${
                          effectTone(effect) === 'good'
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                            : effectTone(effect) === 'bad'
                              ? 'border-rose-200 bg-rose-50 text-rose-800'
                              : 'border-slate-200 bg-slate-50 text-slate-700'
                        }`}
                      >
                        {effect} {n}
                      </span>
                    ) : null,
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Reasoning Timeline / Ledger
                </p>
                <div className="space-y-2 max-h-80 overflow-auto">
                  {(active.reasoning_ledger || []).map((ev, idx) => (
                    <div key={`${ev.ts}-${idx}`} className="flex gap-3 text-sm">
                      <div className="w-28 shrink-0 text-[10px] text-slate-400">
                        {String(ev.ts || '').slice(11, 19) || `#${idx + 1}`}
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">{ev.event}</p>
                        <p className="text-xs text-slate-600">{ev.note}</p>
                        {ev.from_probability != null ? (
                          <p className="text-[10px] text-indigo-700">
                            {Math.round(Number(ev.from_probability) * 100)}% →{' '}
                            {Math.round(Number(ev.to_probability) * 100)}%
                          </p>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Audit Trail
                </p>
                <p className={`mt-1 text-sm font-medium ${statusTone(active.status) === 'good' ? 'text-emerald-700' : 'text-slate-800'}`}>
                  Coverage {active.audit?.passed ? 'PASSED' : 'GAPS'} · Test confidence{' '}
                  {active.confidence_pct ?? Math.round(Number(active.confidence || 0) * 100)}%
                </p>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          Evidence Effects · Enhancements
        </p>
        <ChipList items={dashboard?.evidence_effects || []} tone="good" />
        <ChipList items={['qualitative_evidence_effects', 'reasoning_ledger']} tone="warn" />
      </div>
    </div>
  );
}
