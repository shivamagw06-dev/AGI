import { useCallback, useEffect, useState } from 'react';
import { Landmark, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  getThesisEngineDashboard,
  getThesisEngineHealth,
  getThesisEngineQualityGates,
  planThesisEngine,
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

function verdictTone(v) {
  if (v === 'Strong') return 'good';
  if (v === 'Constructive') return 'good';
  if (v === 'Neutral') return 'warn';
  return 'bad';
}

function PillarCard({ p }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">{p.pillar}</p>
          <p className="text-[10px] uppercase tracking-wide text-slate-400">
            {p.belief_count ?? 0} belief(s)
          </p>
        </div>
        <ChipList items={[p.verdict]} tone={verdictTone(p.verdict)} />
      </div>
      <div className="h-2 w-full rounded-full bg-slate-100">
        <div
          className="h-2 rounded-full bg-indigo-500"
          style={{ width: `${p.strength_pct ?? Math.round(Number(p.strength || 0) * 100)}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-600">
        <span>Strength {p.strength_pct ?? Math.round(Number(p.strength || 0) * 100)}%</span>
        <span>Confidence {p.confidence_pct ?? Math.round(Number(p.confidence || 0) * 100)}%</span>
      </div>
      {(p.evidence || []).length ? (
        <p className="text-xs text-slate-500 line-clamp-2">
          <span className="font-semibold">Evidence:</span> {(p.evidence || [])[0]?.text}
        </p>
      ) : null}
      {(p.contradictions || []).length ? (
        <p className="text-xs text-rose-700 line-clamp-2">
          <span className="font-semibold">Contradiction:</span> {(p.contradictions || [])[0]?.text}
        </p>
      ) : null}
    </div>
  );
}

export default function ThesisConstruction() {
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
        getThesisEngineHealth(),
        getThesisEngineDashboard(),
        getThesisEngineQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Thesis Construction');
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
      const row = await planThesisEngine({ question: nextQ });
      setResult(row);
    } catch (err) {
      setError(err?.message || 'Thesis construction failed');
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const thesis = result?.thesis || {};
  const pillars = thesis.supporting_pillars || [];
  const catalysts = thesis.catalysts || [];
  const timeline = (thesis.timeline || {}).horizons || [];
  const contradictions = thesis.contradictions || {};
  const quality = thesis.quality || {};
  const stability = thesis.stability || {};
  const pressure = thesis.pressure_gauge || {};
  const waterfall = thesis.conviction_waterfall || {};
  const interactions = thesis.pillar_interaction_matrix || {};
  const monitoring = thesis.monitoring || {};
  const narratives = thesis.narratives || {};
  const dna = thesis.thesis_dna || {};
  const evolution = thesis.evolution || {};

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-700">
            RQ2 Sprint 7 · Institutional Thesis Construction Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Landmark className="h-6 w-6 text-indigo-700" />
            Thesis Construction
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Transform calibrated beliefs into one coherent institutional investment thesis — pillars,
            contradictions, catalysts, timeline and conviction — before the Committee debates it.
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
          label="Theses built"
          value={gates?.theses_built?.toLocaleString?.() || gates?.theses_built || '—'}
          hint={gates ? `${gates.passed}/${gates.total} gates` : undefined}
        />
        <Stat
          label="Avg build"
          value={gates?.avg_build_ms != null ? `${gates.avg_build_ms} ms` : '—'}
          hint={`target ≤ ${gates?.target_build_ms ?? 60} ms`}
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
            {busy ? 'Constructing…' : 'Construct Thesis'}
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
        <div className="space-y-5">
          <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-indigo-700">
              Core Thesis
            </p>
            <p className="mt-2 text-base font-semibold text-slate-900">
              {(thesis.core_thesis || {}).statement}
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-700">
              <span className="rounded-md border border-indigo-200 bg-white px-2 py-1">
                Status: <strong>{thesis.status}</strong>
              </span>
              <span className="rounded-md border border-indigo-200 bg-white px-2 py-1">
                Conviction: <strong>{(thesis.conviction || {}).overall_pct}%</strong>
              </span>
              <span className="rounded-md border border-indigo-200 bg-white px-2 py-1">
                Confidence: <strong>{thesis.confidence_pct}%</strong>
              </span>
              <span className="rounded-md border border-indigo-200 bg-white px-2 py-1">
                Quality: <strong>{quality.overall_pct ?? '—'}%</strong>
              </span>
              <span className="rounded-md border border-indigo-200 bg-white px-2 py-1">
                Stability: <strong>{stability.trend || '—'}</strong>
              </span>
              <span className="rounded-md border border-indigo-200 bg-white px-2 py-1">
                Pressure: <strong>{pressure.level || '—'} ({pressure.score ?? '—'})</strong>
              </span>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Thesis Quality (separate from conviction)
              </p>
              <p className="text-3xl font-semibold text-slate-900">{quality.overall_pct ?? '—'}%</p>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                {Object.entries(quality.dimension_pct || {}).map(([name, value]) => (
                  <div key={name} className="rounded-md bg-slate-50 px-2 py-1">
                    <span className="capitalize">{name.replaceAll('_', ' ')}</span>{' '}
                    <strong>{value}%</strong>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Thesis Stability
              </p>
              <p className="text-3xl font-semibold text-slate-900">{stability.score_pct ?? '—'}%</p>
              <ChipList items={[stability.trend, stability.classification].filter(Boolean)} tone="warn" />
              <p className="text-xs text-slate-500">
                Volatility {Math.round(Number(stability.volatility || 0) * 1000) / 10}% · latest
                change {Math.round(Number(stability.latest_delta || 0) * 1000) / 10} pp
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Thesis Pressure Gauge
              </p>
              <p className="text-3xl font-semibold text-slate-900">
                {pressure.score ?? '—'} <span className="text-base">{pressure.level}</span>
              </p>
              <div className="h-3 rounded-full bg-slate-100">
                <div
                  className={`h-3 rounded-full ${
                    pressure.level === 'Low'
                      ? 'bg-emerald-500'
                      : pressure.level === 'Moderate'
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                  }`}
                  style={{ width: `${Math.min(100, Number(pressure.score || 0))}%` }}
                />
              </div>
              <p className="text-xs text-slate-600">{pressure.message}</p>
              <div className="space-y-1">
                {(pressure.pillars || []).map((item) => (
                  <div key={item.pillar} className="flex justify-between gap-2 text-[10px] text-slate-600">
                    <span>{item.pillar}</span>
                    <span>{item.pressure_score} · {item.level}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Conviction Waterfall
              </p>
              {(waterfall.steps || []).map((step) => (
                <div key={step.driver} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-slate-700">{step.driver}</span>
                  <span className={step.impact >= 0 ? 'font-semibold text-emerald-700' : 'font-semibold text-rose-700'}>
                    {step.impact_pp > 0 ? '+' : ''}{step.impact_pp} pp
                  </span>
                </div>
              ))}
              <div className="border-t border-slate-200 pt-2 flex justify-between text-sm font-bold">
                <span>Final conviction</span>
                <span>{waterfall.ending_conviction_pct ?? '—'}%</span>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Pillar Interaction Matrix
              </p>
              <p className="text-xs text-slate-500">{interactions.example_chain}</p>
              <div className="space-y-1.5">
                {(interactions.edges || []).slice(0, 9).map((edge) => (
                  <div key={`${edge.from}-${edge.to}`} className="flex justify-between gap-3 text-xs">
                    <span className="text-slate-700">{edge.from} → {edge.to}</span>
                    <span className="font-semibold text-indigo-700">
                      {edge.influence > 0 ? '+' : ''}{edge.influence.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500 mb-2">
              Supporting Pillars
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {pillars.map((p) => (
                <PillarCard key={p.pillar} p={p} />
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Contradictions
              </p>
              {(contradictions.major || []).map((c, i) => (
                <div key={`${c.text}-${i}`} className="rounded-lg border border-rose-100 bg-rose-50/50 px-3 py-2">
                  <p className="text-sm text-slate-800">{c.text}</p>
                  <p className="text-[10px] text-slate-500">
                    {c.hypothesis_id ? `${c.hypothesis_id} · ` : ''}score {c.score}
                  </p>
                </div>
              ))}
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500 pt-2">
                Outstanding Questions
              </p>
              <ChipList items={(contradictions.outstanding_questions || []).slice(0, 5)} tone="warn" />
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Catalysts
              </p>
              {catalysts.slice(0, 8).map((c) => (
                <div
                  key={c.id}
                  className={`rounded-lg border px-3 py-2 ${
                    c.polarity === 'Positive'
                      ? 'border-emerald-100 bg-emerald-50/50'
                      : c.polarity === 'Negative'
                        ? 'border-rose-100 bg-rose-50/50'
                        : 'border-slate-100 bg-slate-50'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-slate-800">{c.event}</p>
                    <span className="shrink-0 text-xs font-semibold text-slate-700">
                      {c.probability_pct}%
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {c.polarity} · {c.expected_timing} · {(c.evidence_required || []).join(', ')}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Timeline</p>
            <div className="grid gap-3 sm:grid-cols-3">
              {timeline.map((h) => (
                <div key={h.horizon} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-sm font-semibold text-slate-900">{h.horizon}</p>
                  <p className="text-[10px] text-slate-500">{h.window}</p>
                  <p className="mt-1 text-xs text-slate-700">
                    {h.catalyst_count} catalysts · skew {h.skew}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Investment Narrative
              </p>
              <div>
                <p className="text-[10px] font-semibold uppercase text-slate-400">One sentence</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{narratives.one_sentence}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase text-slate-400">One paragraph</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-700">{narratives.one_paragraph}</p>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Thesis DNA
              </p>
              <p className="text-sm font-semibold text-slate-900">{dna.entity}</p>
              <ChipList items={dna.persistent_traits || []} tone="good" />
              <p className="text-xs text-slate-500">
                DNA alignment {dna.alignment_pct ?? '—'}% · fingerprint {dna.fingerprint || '—'} ·{' '}
                {dna.source}
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
                Live Thesis Monitoring
              </p>
              <p className="text-xs text-slate-500">
                {monitoring.healthy_count ?? 0} healthy · {monitoring.pressure_count ?? 0} pressured
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(monitoring.conditions || []).map((condition) => (
                <div key={condition.metric} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="flex justify-between gap-2">
                    <p className="text-xs font-semibold text-slate-800">{condition.metric}</p>
                    <span className="text-[10px] uppercase text-slate-500">{condition.status}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-600">
                    Current {condition.current_pct}% · threshold {condition.threshold_pct}% · distance{' '}
                    {condition.distance_pp > 0 ? '+' : ''}{condition.distance_pp} pp
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Thesis Evolution · v{evolution.current_version || 1}
            </p>
            <div className="flex flex-wrap gap-2">
              {(evolution.history || []).map((item) => (
                <div key={`${item.version}-${item.timestamp}`} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-800">
                    v{item.version} · {item.change_type}
                  </p>
                  <p className="text-[10px] text-slate-500">
                    Conviction {item.conviction != null ? `${Math.round(Number(item.conviction) * 100)}%` : '—'} · {item.status}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Thesis-Breaking Conditions
            </p>
            {(thesis.thesis_breaking_conditions || []).map((b, i) => (
              <p key={i} className="text-sm text-slate-800">
                • {b.condition}
              </p>
            ))}
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Committee Handoff
            </p>
            <p className="mt-1 text-sm text-slate-800">
              {(thesis.committee_handoff || {}).debate_this}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              Audit {thesis.audit?.passed ? 'PASSED' : 'GAPS'} ·{' '}
              {thesis.audit?.counts?.supporting_pillars} pillars ·{' '}
              {thesis.audit?.counts?.major_contradictions} contradictions ·{' '}
              {thesis.audit?.counts?.catalysts} catalysts
            </p>
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          Pillars · Thesis States
        </p>
        <ChipList items={dashboard?.pillars || []} tone="good" />
        <ChipList items={dashboard?.thesis_states || []} tone="warn" />
        <p className="text-xs text-slate-500 pt-1">
          Soft-wired after the Belief Engine and before the Investment Committee. Not a top-level
          intelligence layer.
        </p>
      </div>
    </div>
  );
}
