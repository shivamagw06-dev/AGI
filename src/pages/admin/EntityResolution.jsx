import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Fingerprint, RefreshCw, ShieldAlert } from 'lucide-react';
import {
  diagnoseEntityResolution,
  getEntityResolutionDashboard,
  getEntityResolutionHealth,
  getEntityResolutionQualityGates,
  resolveEntityResolution,
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

export default function EntityResolution() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [result, setResult] = useState(null);
  const [question, setQuestion] = useState('HDFC Bank');
  const [priorEntityId, setPriorEntityId] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([
        getEntityResolutionHealth(),
        getEntityResolutionDashboard(),
        getEntityResolutionQualityGates(),
      ]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Entity Resolution');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onResolve = async (q) => {
    const nextQ = (q ?? question).trim();
    if (!nextQ) return;
    setBusy(true);
    setError('');
    setQuestion(nextQ);
    try {
      const payload = {
        question: nextQ,
        prior_entity_id: priorEntityId || undefined,
        use_cache: false,
      };
      const row = await diagnoseEntityResolution(payload);
      setResult(row);
    } catch (err) {
      try {
        const row = await resolveEntityResolution({
          question: nextQ,
          prior_entity_id: priorEntityId || undefined,
          use_cache: false,
        });
        setResult(row);
      } catch (err2) {
        setError(err2?.message || err?.message || 'Resolve failed');
      }
    } finally {
      setBusy(false);
    }
  };

  const samples = dashboard?.samples || [];
  const rel = result?.relationships || {};

  return (
    <div className="space-y-6 p-6 lg:p-8 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-700">
            RQ1 Sprint 2 · Entity Resolution Engine · Admin Only
          </p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Fingerprint className="h-6 w-6 text-indigo-700" />
            Entity Resolution
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Canonical institutional identity before any research begins. Never guess — IKG is the
            source of truth.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Status" value={health?.status || '—'} hint={health?.programme} />
        <Stat
          label="Accuracy"
          value={gates ? `${Math.round((gates.accuracy || 0) * 1000) / 10}%` : '—'}
          hint={gates ? `${gates.passed}/${gates.total} cases` : 'gates'}
        />
        <Stat
          label="Avg Resolve"
          value={gates?.avg_resolution_ms != null ? `${gates.avg_resolution_ms} ms` : '—'}
          hint="Target &lt; 20 ms"
        />
        <Stat
          label="Ambiguity Flag"
          value={
            gates?.ambiguity_flag_rate != null
              ? `${Math.round(gates.ambiguity_flag_rate * 1000) / 10}%`
              : '—'
          }
          hint="Never guess"
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              Live Resolver
            </p>
            <p className="text-sm text-slate-600">
              Confidence &lt; 85% or ambiguous stems → clarification, research blocked.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs text-indigo-800">
            <ShieldAlert className="h-3.5 w-3.5" />
            Soft-wire · IKG authoritative
          </div>
        </div>

        <div className="grid gap-2 md:grid-cols-[1fr_220px_auto]">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onResolve();
            }}
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm"
            placeholder="Entity mention or full question…"
          />
          <input
            value={priorEntityId}
            onChange={(e) => setPriorEntityId(e.target.value)}
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm"
            placeholder="Prior entity id (context)"
          />
          <Button type="button" onClick={() => onResolve()} disabled={busy}>
            {busy ? 'Resolving…' : 'Resolve'}
          </Button>
        </div>

        {result ? (
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            <Row label="Original Question" value={result.question} />
            <Row
              label="Detected Entities"
              value={(result.detected_entities || []).join(', ') || '—'}
            />
            <Row
              label="Resolved Entity"
              value={result.entity || 'Unresolved'}
              tone={result.needs_clarification ? 'warn' : 'good'}
            />
            <Row label="Entity Type" value={result.entity_type} />
            <Row label="Ticker / Exchange" value={[result.ticker, result.exchange].filter(Boolean).join(' · ')} />
            <Row
              label="Confidence"
              value={`${result.confidence_pct ?? '—'}%`}
              tone={result.confidence_pct >= 85 ? 'good' : 'warn'}
            />
            <Row label="Sector / Industry" value={[result.sector, result.industry].filter(Boolean).join(' · ')} />
            <Row
              label="Knowledge Graph Node"
              value={result.knowledge_graph_id || '—'}
              tone={result.knowledge_graph_linked ? 'good' : 'warn'}
            />
            <Row
              label="Clarification Status"
              value={result.clarification_status}
              tone={result.needs_clarification ? 'warn' : 'good'}
            />
            <Row label="Execution Time" value={`${result.execution_time_ms ?? '—'} ms`} />
            <Row label="Aliases" value={(result.aliases || []).slice(0, 8).join(', ') || '—'} />
            <Row
              label="Peers"
              value={(rel.peers || []).slice(0, 6).join(', ') || '—'}
            />
          </div>
        ) : (
          <p className="text-sm text-slate-500">Resolve a mention to inspect the canonical entity.</p>
        )}

        {result?.needs_clarification ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            <p className="font-semibold">Clarification required — research blocked.</p>
            <ul className="mt-2 list-disc pl-5">
              {(result.possible_matches || []).map((m) => (
                <li key={m.id || m.entity}>
                  <button
                    type="button"
                    className="underline"
                    onClick={() => {
                      setPriorEntityId('');
                      onResolve(m.entity || m.ticker);
                    }}
                  >
                    {m.entity}
                    {m.ticker ? ` (${m.ticker})` : ''}
                    {m.status === 'historical' ? ' · historical' : ''}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {result ? (
          <pre className="max-h-96 overflow-auto rounded-xl border border-slate-200 bg-slate-950 p-4 text-[11px] text-emerald-100">
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Benchmark Mentions
          </p>
          <div className="mt-3 space-y-2">
            {samples.map((s) => (
              <button
                key={s.question}
                type="button"
                onClick={() => onResolve(s.question)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-left hover:border-indigo-300 hover:bg-indigo-50/40"
              >
                <p className="text-sm font-medium text-slate-900">{s.question}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {s.entity_type} · {s.entity || 'clarify'} · {s.confidence_pct}% ·{' '}
                  {s.execution_time_ms} ms
                </p>
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setPriorEntityId('COMP_HDFCBANK');
                onResolve('ICICI');
              }}
              className="w-full rounded-xl border border-indigo-200 bg-indigo-50/40 px-3 py-2 text-left"
            >
              <p className="text-sm font-medium text-slate-900">ICICI (context: HDFC Bank)</p>
              <p className="mt-1 text-xs text-indigo-700">Must resolve to ICICI Bank, not Lombard</p>
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Quality Gates
          </p>
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-slate-500">Cases</p>
              <p className="text-xl font-semibold">{gates?.total ?? '—'}</p>
            </div>
            <div>
              <p className="text-slate-500">Accuracy</p>
              <p className="text-xl font-semibold">
                {gates ? `${Math.round(gates.accuracy * 1000) / 10}%` : '—'}
              </p>
            </div>
            <div>
              <p className="text-slate-500">False resolve</p>
              <p className="text-xl font-semibold">
                {gates ? `${Math.round(gates.false_resolution_rate * 1000) / 10}%` : '—'}
              </p>
            </div>
            <div>
              <p className="text-slate-500">KG link rate</p>
              <p className="text-xl font-semibold">
                {gates ? `${Math.round(gates.knowledge_graph_link_rate * 1000) / 10}%` : '—'}
              </p>
            </div>
          </div>
          {(gates?.failures_sample || []).length ? (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-rose-600">
                Failure sample
              </p>
              {(gates.failures_sample || []).slice(0, 8).map((f) => (
                <p key={f.question} className="text-xs text-slate-600">
                  {f.question} → {f.actual_entity || 'clarify'} ({f.actual_ticker || '—'})
                </p>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-emerald-700">No failure samples.</p>
          )}
        </div>
      </div>
    </div>
  );
}
