import { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { getMissionControlAskObservability } from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function pct(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return `${Math.round(Number(v) * 100)}%`;
}

function num(v, digits = 0) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return Number(v).toFixed(digits);
}

function ms(v) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  if (n >= 1000) return `${(n / 1000).toFixed(1)}s`;
  return `${Math.round(n)}ms`;
}

function Glass({ children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-[var(--io-border)] bg-[rgba(255,255,255,0.03)] backdrop-blur-sm p-4 ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Internal Ask evidence intelligence — Mission Control only.
 * Never shown on public Ask surfaces.
 */
export default function AskObservabilityPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError('');
    try {
      const body = await getMissionControlAskObservability(20);
      setData(body);
      setLoading(false);
    } catch (err) {
      setError(String(err?.message || 'Ask observability unavailable'));
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = window.setInterval(load, 60_000);
    return () => window.clearInterval(t);
  }, [load]);

  const kpis = data?.kpis || {};
  const funnel = data?.funnel || {};
  const latency = data?.latency || {};
  const entity = data?.entity || {};
  const recent = data?.recent || data?.recent_traces || [];

  return (
    <section className="space-y-4" aria-label="Ask evidence observability">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--io-gold)]">
            Internal diagnostics · Ask Evidence Intelligence
          </p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--io-ink)]">Ask Observability</h2>
          <p className="mt-1 max-w-2xl text-sm text-[var(--io-muted)]">
            Retrieved → Ranked → Passed → Referenced, stage latency, entity confidence, and trace IDs.
            Sample size: {data?.sample_size ?? 0} (this engine process).
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <Glass>
          <p className="text-sm text-rose-300">{error}</p>
        </Glass>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Glass>
          <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">Entity success</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums">{pct(kpis.entity_success_rate ?? entity.success_rate)}</p>
          <p className="mt-1 text-[11px] text-[var(--io-muted)]">
            Avg confidence {num(kpis.average_entity_confidence ?? entity.average_confidence, 2)}
          </p>
        </Glass>
        <Glass>
          <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">Utilization</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums">{pct(kpis.evidence_utilization ?? funnel.avg_utilization)}</p>
          <p className="mt-1 text-[11px] text-[var(--io-muted)]">Referenced ÷ Passed</p>
        </Glass>
        <Glass>
          <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">Efficiency / Precision</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums">
            {pct(kpis.evidence_efficiency ?? funnel.avg_efficiency)} / {pct(kpis.retrieval_precision ?? funnel.avg_precision)}
          </p>
          <p className="mt-1 text-[11px] text-[var(--io-muted)]">Ref÷Retrieved · Ref÷Ranked</p>
        </Glass>
        <Glass>
          <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">Fallback rate</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums">{pct(kpis.fallback_rate ?? latency.timeout_or_fallback_rate)}</p>
          <p className="mt-1 text-[11px] text-[var(--io-muted)]">
            P95 total {ms(latency.p95_total_ms)} · P99 {ms(latency.p99_total_ms)}
          </p>
        </Glass>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <Glass>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">Evidence funnel (avg)</p>
          <ol className="mt-3 space-y-2 text-sm text-[var(--io-ink)]">
            <li>Retrieved — {num(funnel.avg_retrieved, 1)}</li>
            <li className="pl-3 text-[var(--io-muted)]">↓</li>
            <li>Ranked — {num(funnel.avg_ranked, 1)}</li>
            <li className="pl-3 text-[var(--io-muted)]">↓</li>
            <li>Passed — {num(funnel.avg_passed, 1)}</li>
            <li className="pl-3 text-[var(--io-muted)]">↓</li>
            <li>Referenced — {num(funnel.avg_referenced, 1)}</li>
          </ol>
        </Glass>
        <Glass>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">Stage latency (avg)</p>
          <ul className="mt-3 space-y-1.5 text-sm tabular-nums text-[var(--io-ink)]">
            <li className="flex justify-between gap-4"><span>Entity</span><span>{ms(latency.avg_entity_ms)}</span></li>
            <li className="flex justify-between gap-4"><span>Retrieval</span><span>{ms(latency.avg_retrieval_ms)}</span></li>
            <li className="flex justify-between gap-4"><span>Ranking</span><span>{ms(latency.avg_ranking_ms)}</span></li>
            <li className="flex justify-between gap-4"><span>Reasoning</span><span>{ms(latency.avg_reasoning_ms)}</span></li>
            <li className="flex justify-between gap-4"><span>Assembly</span><span>{ms(latency.avg_assembly_ms)}</span></li>
            <li className="flex justify-between gap-4 font-semibold"><span>Total</span><span>{ms(latency.avg_total_ms)}</span></li>
          </ul>
          {(entity.top_rejected || []).length ? (
            <p className="mt-3 text-[11px] text-[var(--io-muted)]">
              Top rejected: {(entity.top_rejected || []).slice(0, 6).map((r) => r.token).join(', ')}
            </p>
          ) : null}
        </Glass>
      </div>

      <Glass>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">Recent Ask traces</p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-xs">
            <thead className="text-[var(--io-muted)]">
              <tr>
                <th className="py-1.5 pr-3 font-medium">Trace</th>
                <th className="py-1.5 pr-3 font-medium">Entity</th>
                <th className="py-1.5 pr-3 font-medium">Funnel</th>
                <th className="py-1.5 pr-3 font-medium">Util</th>
                <th className="py-1.5 pr-3 font-medium">Total</th>
                <th className="py-1.5 font-medium">Fallback</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-3 text-[var(--io-muted)]">
                    No traces in this process yet — run Ask once after deploy.
                  </td>
                </tr>
              ) : (
                recent.slice(0, 12).map((row) => {
                  const ev = row.evidence || {};
                  const ent = row.entity || {};
                  const lat = row.latency || {};
                  return (
                    <tr key={row.ask_trace_id || row.ts} className="border-t border-[var(--io-border)]">
                      <td className="py-2 pr-3 font-mono text-[11px]">{row.ask_trace_id || '—'}</td>
                      <td className="py-2 pr-3">
                        {ent.name || ent.detected || '—'}
                        {ent.confidence != null ? ` (${num(ent.confidence, 2)})` : ''}
                      </td>
                      <td className="py-2 pr-3 tabular-nums">
                        {ev.retrieved ?? '—'}→{ev.ranked ?? '—'}→{ev.passed ?? ev.passed_to_ice ?? '—'}→{ev.referenced ?? '—'}
                      </td>
                      <td className="py-2 pr-3">{pct(ev.utilization)}</td>
                      <td className="py-2 pr-3">{ms(lat.total_ms ?? lat.total)}</td>
                      <td className="py-2">{row.fallback ? 'Yes' : 'No'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Glass>
    </section>
  );
}
