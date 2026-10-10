import { useCallback, useEffect, useState } from 'react';
import { FileStack, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getResearchBlueprintDashboard,
  getResearchBlueprintHealth,
  getResearchBlueprintQualityGates,
  planResearchBlueprint,
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

function VisualView({ steps }) {
  if (!steps?.length) return <p className="text-sm text-slate-400">—</p>;
  return (
    <div className="space-y-2">
      <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Blueprint
      </div>
      {steps.map((s, idx) => (
        <div key={`${s.owner}-${idx}`}>
          <div className="text-center text-slate-300">↓</div>
          <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-slate-900">
            {s.owner}
            <span className="ml-2 text-xs font-normal text-slate-500">via {s.via_section}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function BlueprintEngine() {
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
        getResearchBlueprintHealth(),
        getResearchBlueprintDashboard(),
        getResearchBlueprintQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Blueprint Engine');
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
      const row = await planResearchBlueprint({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Blueprint failed');
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
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-700">
            RQ1 Sprint 8 · Dynamic Research Blueprint Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <FileStack className="h-6 w-6 text-indigo-700" />
            Blueprint Engine
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Finalise the institutional publication plan — report type, section order, owners, and
            Research Assignment Book — before research begins.
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
          label="Blueprint accuracy"
          value={gates ? pct(gates.blueprint_accuracy) : '—'}
          hint={gates ? `${gates.checked} scenarios` : undefined}
        />
        <Stat
          label="Avg blueprint time"
          value={gates?.average_blueprint_ms != null ? `${gates.average_blueprint_ms} ms` : '—'}
          hint="Target < 20 ms"
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
            {busy ? 'Planning…' : 'Build blueprint'}
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
            <Row label="Question" value={result.question} />
            <Row label="Blueprint / Report Type" value={result.report_name || result.report_type} tone="good" />
            <Row label="Audience" value={result.audience} />
            <Row label="Sections" value={String(result.section_order?.length ?? '—')} />
            <Row
              label="Assignments"
              value={String(result.assignment_book?.assignment_count ?? '—')}
              tone="good"
            />
            <Row
              label="Blueprint time"
              value={
                result.metrics?.blueprint_ms != null ? `${result.metrics.blueprint_ms} ms` : '—'
              }
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Section order</h2>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
                {(result.section_order || []).map((key) => (
                  <li key={key}>
                    <span className="font-medium">{key}</span>
                    <span className="text-slate-400"> · {result.section_owner?.[key]}</span>
                  </li>
                ))}
              </ol>
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Mandatory</h2>
              <ChipList items={result.mandatory_sections} tone="good" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Hidden</h2>
              <ChipList items={result.hidden_sections} tone="warn" />
              <h2 className="pt-2 text-sm font-semibold text-slate-900">Suppressed</h2>
              <ChipList items={(result.suppressed_sections || []).slice(0, 12)} tone="bad" />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
              <h2 className="text-sm font-semibold text-slate-900">Visual ownership chain</h2>
              <VisualView steps={result.visual_view || []} />
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Quality rules</h2>
              <div className="grid gap-2 sm:grid-cols-2">
                <Row label="Max sections" value={String(result.quality_rules?.maximum_sections ?? '—')} />
                <Row label="Writing style" value={result.quality_rules?.writing_style} />
                <Row label="Citations" value={result.quality_rules?.citation_rules} />
                <Row
                  label="Max words"
                  value={String(result.quality_rules?.maximum_length_words ?? '—')}
                />
              </div>
              <h2 className="pt-3 text-sm font-semibold text-slate-900">Assignment Book</h2>
              <div className="max-h-56 space-y-2 overflow-auto text-xs text-slate-600">
                {(result.assignment_book?.assignments || []).map((a) => (
                  <div key={a.owner} className="rounded-lg border border-slate-200 bg-slate-50 p-2">
                    <p className="font-semibold text-slate-800">{a.owner}</p>
                    <p className="mt-0.5">{a.mission}</p>
                    <p className="mt-1 text-slate-400">
                      Sections: {(a.assigned_sections || []).join(', ')}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {gates ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">IRS quality gates</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Blueprint accuracy" value={pct(gates.blueprint_accuracy)} tone="good" />
            <Row label="Report selection" value={pct(gates.correct_report_selection)} tone="good" />
            <Row label="Section ownership" value={pct(gates.correct_section_ownership)} tone="good" />
            <Row label="No irrelevant sections" value={pct(gates.no_irrelevant_sections)} tone="good" />
            <Row
              label="Avg time"
              value={gates.average_blueprint_ms != null ? `${gates.average_blueprint_ms} ms` : '—'}
              tone="good"
            />
            <Row label="Gate status" value={gates.ok ? 'PASS' : 'FAIL'} tone={gates.ok ? 'good' : 'bad'} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
