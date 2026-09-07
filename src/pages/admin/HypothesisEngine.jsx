import { useCallback, useEffect, useState } from 'react';
import { Lightbulb, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getHypothesisEngineDashboard,
  getHypothesisEngineHealth,
  getHypothesisEngineQualityGates,
  planHypothesisEngine,
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
        <span key={String(item)} className={`rounded-md border px-2 py-0.5 text-xs ${cls}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function HypothesisCard({ h }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            {h.id} · {h.type} · Priority {h.priority}
          </p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{h.hypothesis || h.statement}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold text-slate-900">
            {h.confidence_pct ?? Math.round(Number(h.confidence || 0) * 100)}%
          </p>
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Confidence</p>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <Row label="Analyst Owner" value={h.analyst_owner || (h.responsible_analysts || []).join(', ')} />
        <Row
          label="Current Status"
          value={h.status}
          tone={h.status === 'proposed' ? 'warn' : h.quality_compliant === false ? 'bad' : 'good'}
        />
      </div>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500 mb-1.5">
          Required Evidence
        </p>
        <ChipList items={h.required_evidence || []} />
      </div>
      {h.reason ? (
        <p className="text-xs text-slate-500">
          <span className="font-semibold text-slate-600">Reason:</span> {h.reason}
        </p>
      ) : null}
    </div>
  );
}

export default function HypothesisEngine() {
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
        getHypothesisEngineHealth(),
        getHypothesisEngineDashboard(),
        getHypothesisEngineQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Hypothesis Engine');
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
      const row = await planHypothesisEngine({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Hypothesis generation failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const ranking = result?.ranking || result?.ranking_by_type || {};
  const hypotheses = result?.hypotheses || [];

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-teal-700">
            RQ2 Sprint 1 · Institutional Hypothesis Generation Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Lightbulb className="h-6 w-6 text-teal-700" />
            Hypothesis Engine
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Generate specific, testable, falsifiable investment hypotheses after IREP and before the
            first analyst begins research — never generic opinions.
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
          value={gates ? pct(gates.hypothesis_generation_coverage) : '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Avg generation"
          value={gates?.avg_generation_ms != null ? `${gates.avg_generation_ms} ms` : '—'}
          hint={`target ≤ ${gates?.target_generation_ms ?? 30} ms`}
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
            {busy ? 'Generating…' : 'Generate Hypotheses'}
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
            <Stat label="Generated Hypotheses" value={result.hypothesis_count} />
            <Stat
              label="Overall Confidence"
              value={
                result.overall_confidence != null
                  ? `${Math.round(Number(result.overall_confidence) * 100)}%`
                  : '—'
              }
            />
            <Stat label="Generation" value={`${result.generation_ms ?? '—'} ms`} />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500 mb-3">
              Ranking (expected impact)
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(ranking).map(([type, weight]) => (
                <span
                  key={type}
                  className="rounded-md border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs text-teal-900"
                >
                  {type} {Math.round(Number(weight) * 100)}%
                </span>
              ))}
              {!Object.keys(ranking).length ? <span className="text-slate-400 text-sm">—</span> : null}
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Generated Hypotheses ↓ Confidence ↓ Required Evidence ↓ Analyst Owner ↓ Current Status
            </p>
            {hypotheses.map((h) => (
              <HypothesisCard key={h.id} h={h} />
            ))}
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          Five Quality Rules
        </p>
        <ChipList
          items={dashboard?.five_quality_rules || ['specific', 'testable', 'falsifiable', 'evidence_required', 'decision_relevant']}
          tone="good"
        />
        <p className="text-xs text-slate-500 pt-1">
          Soft-wired after IREP and before first analyst research. Not a top-level intelligence layer.
        </p>
      </div>
    </div>
  );
}
