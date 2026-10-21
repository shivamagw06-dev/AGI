import { useCallback, useEffect, useState } from 'react';
import { Layers3, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  enrichContextIntelligence,
  getContextIntelligenceDashboard,
  getContextIntelligenceHealth,
  getContextIntelligenceQualityGates,
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
      <p className={`mt-1 text-sm font-medium break-words whitespace-pre-wrap ${color}`}>
        {value || '—'}
      </p>
    </div>
  );
}

function ChipList({ items }) {
  if (!items?.length) return <span className="text-slate-400">—</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-700"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export default function ContextIntelligence() {
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
        getContextIntelligenceHealth(),
        getContextIntelligenceDashboard(),
        getContextIntelligenceQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Context Intelligence');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onEnrich = async (q) => {
    const nextQ = (q ?? question).trim();
    if (!nextQ) return;
    setBusy(true);
    setError('');
    setQuestion(nextQ);
    try {
      const row = await enrichContextIntelligence({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Enrich failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const card = result?.research_context_card || {};
  const conf = result?.confidence || {};
  const pct = (v) => (v == null ? '—' : `${Math.round(Number(v) * 1000) / 10}%`);
  const importance = Object.entries(result?.context_importance || {});

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-700">
            RQ1 Sprint 4 · Context Intelligence Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Layers3 className="h-6 w-6 text-cyan-700" />
            Context Intelligence
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Discover surrounding institutional context and produce a Research Context Card before
            any analyst begins reasoning.
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
          label="Context accuracy"
          value={gates ? pct(gates.context_accuracy) : '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Avg runtime"
          value={gates?.avg_runtime_ms != null ? `${gates.avg_runtime_ms} ms` : '—'}
          hint={`Target < ${health?.max_runtime_ms_target || 25} ms`}
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[280px] flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onEnrich();
            }}
            placeholder="Institutional research question"
          />
          <Button onClick={() => onEnrich()} disabled={busy}>
            {busy ? 'Enriching…' : 'Enrich context'}
          </Button>
        </div>
        {samples.length ? (
          <div className="flex flex-wrap gap-2">
            {samples.slice(0, 6).map((s) => (
              <button
                key={s.question}
                type="button"
                className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100"
                onClick={() => onEnrich(s.question)}
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
            <Row label="Primary Objective" value={result.primary_objective} tone="good" />
            <Row
              label="Context Confidence"
              value={pct(conf.overall)}
              tone={conf.passes_threshold ? 'good' : 'bad'}
            />
            <Row label="Time Horizon" value={result.time_context?.time_horizon} />
            <Row label="Market Regime" value={result.market_context?.regime} />
            <Row label="Scenario" value={result.scenario_context?.scenario} />
            <Row label="Entity" value={result.entity_context?.entity} />
            <Row
              label="Portfolio Context"
              value={result.portfolio_context?.required ? 'Required' : 'Not Required'}
            />
            <Row
              label="Runtime"
              value={result.runtime_ms != null ? `${result.runtime_ms} ms` : '—'}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Detected context</h2>
              <Row label="Macro" value={result.macro_context?.environment || result.macro_context?.summary} />
              <Row label="Expectation" value={result.expectation_context?.summary} />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Comparisons
                </p>
                <div className="mt-1">
                  <ChipList items={result.comparison_context?.lenses} />
                </div>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Events / catalysts
                </p>
                <div className="mt-1">
                  <ChipList items={result.event_context?.events} />
                </div>
              </div>
              <div>
                <p className="pt-1 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  Context importance
                </p>
                <div className="mt-2 space-y-1 text-sm">
                  {importance.length
                    ? importance.map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span>{k}</span>
                          <span className="font-semibold">{pct(v)}</span>
                        </div>
                      ))
                    : '—'}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Row label="Missing" value={(result.missing_context || []).join(', ') || 'None'} />
                <Row label="Ignored" value={(result.ignored_context || []).slice(0, 4).join(', ') || '—'} />
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Research Context Card</h2>
              <pre className="max-h-[520px] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-relaxed text-slate-800 whitespace-pre-wrap">
                {card.yaml_preview || '—'}
              </pre>
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Context accuracy" value={pct(gates.context_accuracy)} tone="good" />
            <Row label="Time horizon" value={pct(gates.time_horizon_detection)} tone="good" />
            <Row label="Market context" value={pct(gates.market_context_detection)} tone="good" />
            <Row label="Comparison" value={pct(gates.comparison_context_accuracy)} tone="good" />
            <Row label="Portfolio" value={pct(gates.portfolio_context_accuracy)} tone="good" />
            <Row label="Gate status" value={gates.ok ? 'PASS' : 'FAIL'} tone={gates.ok ? 'good' : 'bad'} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
