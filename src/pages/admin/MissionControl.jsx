import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  Download,
  RefreshCw,
  Search,
  Shield,
} from 'lucide-react';
import {
  acknowledgeMissionControlAlert,
  getMissionControlDashboard,
  getMissionControlHealth,
  getMissionControlQualityGates,
  getMissionControlReport,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';
import AgentMapPanel from '@/pages/admin/AgentMapPanel';
import AskObservabilityPanel from '@/pages/admin/AskObservabilityPanel';
import '@/office/theme.css';
import { API_ORIGIN } from '@/config';

function statusColour(status) {
  const s = String(status || '').toLowerCase();
  if (s.includes('healthy') || s === 'ok' || s === 'green') return 'text-emerald-400';
  if (s.includes('warn') || s.includes('yellow') || s.includes('unknown') || s.includes('soft'))
    return 'text-amber-300';
  if (s.includes('critical') || s.includes('offline') || s.includes('red') || s.includes('fail'))
    return 'text-rose-400';
  return 'text-[var(--io-muted)]';
}

function Glass({ children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-[var(--io-border)] bg-[rgba(255,255,255,0.03)] backdrop-blur-sm p-4 md:p-5 ${className}`}
    >
      {children}
    </div>
  );
}

function Kicker({ children }) {
  return <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--io-gold)]">{children}</p>;
}

function Stat({ label, value, hint, status }) {
  return (
    <Glass>
      <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${statusColour(status || value)}`}>
        {value ?? '—'}
      </p>
      {hint ? <p className="mt-1 text-[11px] text-[var(--io-muted)]">{hint}</p> : null}
    </Glass>
  );
}

export default function MissionControl() {
  const [health, setHealth] = useState(null);
  const [desk, setDesk] = useState(null);
  const [gates, setGates] = useState(null);
  const [researchPipeline, setResearchPipeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [agentMapOpen, setAgentMapOpen] = useState(false);

  const loadDashboard = useCallback(async () => {
    setError('');
    try {
      // Snapshot reader only — never triggers analytics rebuild.
      const d = await getMissionControlDashboard();
      setDesk(d);
      setLoading(false);
    } catch (err) {
      const msg = String(err?.message || 'Failed to load Mission Control');
      setError(msg);
      setLoading(false);
    }
  }, []);

  const loadHealth = useCallback(async () => {
    try {
      const [hRes, gRes] = await Promise.allSettled([
        getMissionControlHealth(),
        getMissionControlQualityGates(),
      ]);
      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (gRes.status === 'fulfilled') setGates(gRes.value);
      if (API_ORIGIN) {
        const response = await fetch(`${API_ORIGIN}/api/market/research-pipeline/health`, { headers: { Accept: 'application/json' } });
        if (response.ok) setResearchPipeline(await response.json());
      }
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    loadHealth();
    // Poll cached snapshot only (60–120s). Never rebuild on interval.
    const dashTimer = window.setInterval(loadDashboard, 90_000);
    const healthTimer = window.setInterval(loadHealth, 45_000);
    return () => {
      window.clearInterval(dashTimer);
      window.clearInterval(healthTimer);
    };
  }, [loadDashboard, loadHealth]);

  const load = loadDashboard;

  const exportReport = async () => {
    try {
      const report = await getMissionControlReport();
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agi-mission-control-report-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.message || 'Export failed');
    }
  };

  const onAck = async (id) => {
    try {
      await acknowledgeMissionControlAlert(id);
      await load();
    } catch (err) {
      setError(err?.message || 'Acknowledge failed');
    }
  };

  const exec = desk?.executive_status || {};
  const platforms = desk?.platform_status || [];
  const engines = desk?.engine_status || [];
  const apis = desk?.api_status || [];
  const knowledge = desk?.knowledge_growth || {};
  const learning5d = desk?.learning_last_5_days || null;
  const coverage = desk?.coverage_dashboard || {};
  const institutional = coverage?.institutional_intelligence || {};
  const evidenceRetrieval = institutional?.evidence_retrieval || null;
  const institutionalDocs = institutional?.institutional_documents || null;
  const liveDataBoard = institutional?.live_institutional_data || null;
  const continuousGatherLearn = institutional?.continuous_gather_learn || desk?.continuous_gather_learn || null;
  const researchHub = institutional?.research_intelligence_hub || null;
  const marketForecast = institutional?.market_forecast_intelligence || null;
  const sectorForecast = institutional?.sector_forecast_intelligence || null;
  const marketKnowledge = institutional?.continuous_market_knowledge || null;
  const marketAnalogues = institutional?.historical_market_analogue_intelligence || null;
  const fdoBoard = institutional?.financial_data_operations || null;
  const fseBoard = institutional?.financial_statements_engine || null;
  const fseSourceBoard = institutional?.fse_source_coverage || null;
  const fireBoard = institutional?.financial_intelligence || null;
  const fireDriversBoard = institutional?.financial_drivers || null;
  const fkbBoard = institutional?.financial_knowledge || null;
  const v4Office = {
    thesis: desk?.institutional_investment_thesis || null,
    decision: desk?.institutional_decision_office || null,
    portfolio: desk?.institutional_portfolio_office || null,
    monitoring: desk?.institutional_monitoring_office || null,
    learning: desk?.institutional_learning_office || null,
  };
  const v4Present = Object.values(v4Office).some(Boolean);
  const monitor = desk?.company_monitor || {};
  const observationCenter =
    institutional?.institutional_observation || desk?.institutional_observation || null;
  const portfolioKnowledge =
    institutional?.institutional_portfolio || desk?.institutional_portfolio || null;
  const portfolioCommand =
    institutional?.institutional_portfolio_decision ||
    desk?.institutional_portfolio_decision ||
    null;
  const portfolioRiskCenter =
    institutional?.institutional_portfolio_risk || desk?.institutional_portfolio_risk || null;
  const policyCenter =
    institutional?.institutional_policy || desk?.institutional_policy || null;
  const committeeCenter =
    institutional?.institutional_committee || desk?.institutional_committee || null;
  const orchestrationCenter =
    institutional?.institutional_orchestrator || desk?.institutional_orchestrator || null;
  const workspaceHealth =
    institutional?.institutional_workspace || desk?.institutional_workspace || null;
  const relationshipCenter =
    institutional?.institutional_cross_company || desk?.institutional_cross_company || null;
  const publicationCenter =
    institutional?.institutional_publishing || desk?.institutional_publishing || null;
  const platformOps =
    institutional?.institutional_multi_portfolio || desk?.institutional_multi_portfolio || null;
  const performanceCenter =
    institutional?.institutional_performance || desk?.institutional_performance || null;
  const securityCenter =
    institutional?.institutional_security || desk?.institutional_security || null;
  const operationsCenter =
    institutional?.institutional_observability || desk?.institutional_observability || null;
  const architectureCenter =
    institutional?.institutional_architecture || desk?.institutional_architecture || null;
  const launchCenter =
    institutional?.institutional_launch || desk?.institutional_launch || null;
  const acceptanceCenter =
    institutional?.institutional_acceptance || desk?.institutional_acceptance || null;
  const evidenceCenter =
    institutional?.institutional_evidence || desk?.institutional_evidence || null;
  const knowledgeHealth =
    institutional?.knowledge_health ||
    desk?.knowledge_health ||
    evidenceCenter?.knowledge_health ||
    null;
  const coverageFactory =
    institutional?.institutional_coverage_factory ||
    desk?.institutional_coverage_factory ||
    null;
  const pipeline = desk?.research_pipeline || {};
  const preds = desk?.prediction_intelligence || {};
  const dq = desk?.data_quality || {};
  const ca = desk?.company_analysis || {};
  const academy = desk?.academy || {};
  const cid = desk?.cid || {};
  const sys = desk?.system_health || {};
  const events = desk?.live_event_stream || [];
  const copilot = desk?.executive_copilot || {};
  const arch = desk?.architecture_map || {};
  const alerts = desk?.alerts_centre || [];
  const deploy = desk?.deployment_centre || {};
  const perf = desk?.performance_analytics || {};

  const filteredPlatforms = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return platforms;
    return platforms.filter((p) => JSON.stringify(p).toLowerCase().includes(q));
  }, [platforms, query]);

  const warming = Boolean(desk?._warming || desk?.status === 'warming');
  const lastUpdated =
    desk?.snapshot_meta?.persisted_at ||
    desk?.snapshot?.persisted_at ||
    health?.snapshot?.lastUpdated ||
    desk?.generated_at ||
    null;

  if (loading && !desk) {
    return (
      <div className="agi-office -m-6 min-h-screen p-4 md:p-6">
        <div className="mx-auto max-w-[1400px] py-16 text-center">
          <p className="mt-4 text-sm text-[var(--io-muted)]">Opening Mission Control…</p>
          <p className="mt-2 text-[11px] text-[var(--io-caption)]">
            Serving the latest snapshot — no live analytics rebuild.
          </p>
        </div>
      </div>
    );
  }

  if (warming && !desk?.executive_status?.agi_status?.includes?.('Healthy')) {
    return (
      <div className="agi-office -m-6 min-h-screen p-4 md:p-6">
        <div className="mx-auto max-w-[1400px] space-y-5 py-10">
          <Kicker>Administrator only · Mission Control v1.0</Kicker>
          <h1 className="io-title mt-2 text-3xl flex items-center gap-2">
            <Shield className="h-7 w-7 text-[var(--io-gold)]" />
            AGI Mission Control
          </h1>
          <Glass className="mt-6">
            <p className="text-lg font-semibold text-[var(--io-ink)]">Mission Control is warming up.</p>
            <p className="mt-2 text-sm text-[var(--io-muted)]">
              {desk?.message ||
                'The first operational snapshot is being generated by the intelligence worker.'}
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div>
                <p className="text-[11px] uppercase text-[var(--io-caption)]">Last Updated</p>
                <p className="mt-1 text-sm">Unknown</p>
              </div>
              <div>
                <p className="text-[11px] uppercase text-[var(--io-caption)]">System Health</p>
                <p className={`mt-1 text-sm ${statusColour(health?.status)}`}>
                  {health?.status === 'ok' ? 'Available' : health?.status || 'Checking…'}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase text-[var(--io-caption)]">Snapshot job</p>
                <p className="mt-1 text-sm">
                  {health?.worker?.queue_status || desk?.snapshot_meta?.job?.status || 'queued'}
                </p>
              </div>
            </div>
            <p className="mt-4 text-[11px] text-[var(--io-caption)]">
              This page polls the cached snapshot every 90s and will populate automatically — it never
              rebuilds analytics on refresh.
            </p>
            <div className="mt-4">
              <Button type="button" variant="outline" onClick={() => loadDashboard()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Check snapshot
              </Button>
            </div>
          </Glass>
          {error ? <p className="text-sm text-rose-400">{error}</p> : null}
        </div>
      </div>
    );
  }

  return (
    <div className="agi-office -m-6 min-h-screen p-4 md:p-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Kicker>Administrator only · Mission Control v1.0</Kicker>
            <h1 className="io-title mt-2 text-3xl flex items-center gap-2">
              <Shield className="h-7 w-7 text-[var(--io-gold)]" />
              AGI Mission Control
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-[var(--io-muted)]">
              Read-only operations cockpit. Serves a precomputed worker snapshot. Never modifies
              research, House Views, or recommendations. Never rebuilds analytics on page open.
            </p>
            <p className="mt-2 text-[11px] text-[var(--io-caption)]">
              Last snapshot {lastUpdated || desk?.generated_at || '—'} · Poll 90s · Gates{' '}
              {gates?.passed ? 'PASS' : gates ? 'FAIL' : '—'} · {health?.version || ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--io-muted)]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search platforms / APIs"
                className="w-56 rounded-xl border border-[var(--io-border)] bg-[rgba(255,255,255,0.03)] py-2 pl-9 pr-3 text-sm text-[var(--io-ink)] outline-none focus:border-[var(--io-gold)]"
              />
            </div>
            <Button
              variant="outline"
              onClick={() => setAgentMapOpen(true)}
              className="border-[var(--io-gold)]/50 text-[var(--io-ink)]"
            >
              <Bot className="h-4 w-4 mr-2 text-[var(--io-gold)]" />
              Agent Map
            </Button>
            <Button variant="outline" onClick={load} disabled={loading} className="border-[var(--io-border)] text-[var(--io-ink)]">
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button variant="outline" onClick={exportReport} className="border-[var(--io-border)] text-[var(--io-ink)]">
              <Download className="h-4 w-4 mr-2" />
              Export report
            </Button>
          </div>
        </div>

        {error ? (
          <Glass className="border-amber-500/40 bg-amber-500/10 text-amber-100 flex gap-2 text-sm">
            <AlertTriangle className="h-4 w-4 mt-0.5" />
            <span>{error}</span>
          </Glass>
        ) : null}

        <section className="space-y-3">
          <Kicker>Research Pipeline · Live Instrumentation</Kicker>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Stat label="Pipeline" value={researchPipeline?.status || 'CHECKING'} status={researchPipeline?.status} hint="Research-only · execution disabled" />
            <Stat label="Upstox Strategies" value={researchPipeline ? `${researchPipeline.feeds?.upstox_strategies?.healthy || 0} / 5` : '—'} hint="Live Alpha engines" />
            <Stat label="Groww Strategies" value={researchPipeline ? `${researchPipeline.feeds?.groww_strategies?.healthy || 0} / 2` : '—'} hint="EOD research" />
            <Stat label="Candidates" value={researchPipeline?.latest_cycle?.candidates ?? '—'} hint={`${researchPipeline?.latest_cycle?.eligible_confluence ?? 0} eligible`} />
            <Stat label="Confluence Events" value={researchPipeline?.totals?.events ?? '—'} hint={`${researchPipeline?.latest_cycle?.persisted ?? 0} last cycle`} />
            <Stat label="Memory States" value={researchPipeline?.totals?.memory ?? '—'} hint={`Coverage ${researchPipeline?.integrity?.memory_coverage ?? '—'}`} />
            <Stat label="Forecast Sets" value={researchPipeline?.totals?.feature_snapshots ?? '—'} hint={`${researchPipeline?.totals?.forecasts ?? 0} horizon forecasts`} />
            <Stat label="Ranked Rows" value={researchPipeline?.totals?.rankings ?? '—'} hint={`${researchPipeline?.totals?.cross_sections ?? 0} matured cross-sections`} />
          </div>
          {researchPipeline?.latest_cycle?.rejected ? (
            <Glass className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              {Object.entries(researchPipeline.latest_cycle.rejected)
                .filter(([, value]) => Number(value) > 0)
                .sort((a, b) => Number(b[1]) - Number(a[1]))
                .map(([reason, value]) => (
                  <div key={reason}>
                    <span className="text-[var(--io-caption)]">{reason.replaceAll('_', ' ')}</span>
                    <p className="mt-1 font-semibold tabular-nums">{value}</p>
                  </div>
                ))}
            </Glass>
          ) : null}
          {researchPipeline?.dominant_bottleneck ? (
            <Glass className="border-amber-500/30 text-sm">
              <p className="font-semibold text-amber-200">Dominant bottleneck · {researchPipeline.dominant_bottleneck.stage.replaceAll('_', ' ')}</p>
              <p className="mt-1 text-[var(--io-muted)]">
                {researchPipeline.dominant_bottleneck.reason.replaceAll('_', ' ')}
                {researchPipeline.dominant_bottleneck.affected != null ? ` · ${researchPipeline.dominant_bottleneck.affected} affected` : ''}
              </p>
            </Glass>
          ) : null}
        </section>

        {/* SECTION 1 */}
        <section className="space-y-3">
          <Kicker>Section 1 · Executive Status</Kicker>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Stat label="AGI Status" value={exec.agi_status} status={exec.agi_status} />
            <Stat label="Research Grade" value={exec.research_grade} />
            <Stat label="Knowledge Grade" value={exec.knowledge_grade} />
            <Stat label="Data Grade" value={exec.data_grade} />
            <Stat label="Coverage" value={exec.coverage != null ? `${exec.coverage}%` : '—'} />
            <Stat label="Companies Monitored" value={exec.companies_monitored} />
            <Stat label="Companies Covered" value={exec.companies_covered} />
            <Stat label="Questions Today" value={exec.questions_answered_today ?? '—'} />
            <Stat
              label="Last Learning"
              value={exec.last_successful_learning || learning5d?.latest_learning_date || '—'}
              hint={learning5d?.articles_learned != null ? `${learning5d.articles_learned} articles · 5d` : 'CMS / Academy'}
            />
            <Stat label="Last Health Check" value={(exec.last_health_check || '').slice(11, 19) || '—'} />
            <Stat label="Last Deployment" value={deploy.last_deployment || deploy.git_commit || '—'} />
            <Stat label="Branch" value={deploy.current_branch || '—'} />
          </div>
        </section>

        {/* Ask Evidence Intelligence — internal funnel / latency / traces */}
        <AskObservabilityPanel />

        {continuousGatherLearn ? (
          <section className="space-y-3">
            <Kicker>Continuous Gather → Learn</Kicker>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
              <Stat
                label="Loop Status"
                value={continuousGatherLearn.enabled ? continuousGatherLearn.status || 'ok' : 'off'}
                status={continuousGatherLearn.enabled ? 'healthy' : 'offline'}
                hint={continuousGatherLearn.version || 'cgl'}
              />
              <Stat
                label="Current Slot"
                value={continuousGatherLearn.current_slot || '—'}
                hint="IST pre/intra/post/overnight"
              />
              <Stat
                label="Last Cycle"
                value={continuousGatherLearn.latest_run?.ok == null ? '—' : continuousGatherLearn.latest_run.ok ? 'OK' : 'Degraded'}
                status={continuousGatherLearn.latest_run?.ok ? 'healthy' : 'warn'}
                hint={continuousGatherLearn.latest_run?.run_id || continuousGatherLearn.background?.run_id || '—'}
              />
              <Stat
                label="Latency"
                value={
                  continuousGatherLearn.latest_run?.latency_ms != null
                    ? `${Math.round(continuousGatherLearn.latest_run.latency_ms / 1000)}s`
                    : '—'
                }
                hint="Last gather→learn cycle"
              />
              <Stat
                label="Knowledge Extracts"
                value={
                  continuousGatherLearn.metrics?.knowledge_extracts_total ??
                  continuousGatherLearn.knowledge_growth?.extracts ??
                  '—'
                }
                hint="Structured facts (not ML training)"
              />
              <Stat
                label="Learnings Archived"
                value={continuousGatherLearn.archived_learnings ?? continuousGatherLearn.metrics?.learnings_archived_total ?? '—'}
                hint="Durable FVL/ILO archive"
              />
              <Stat
                label="Listed Universe"
                value={continuousGatherLearn.current_listed_universe ?? continuousGatherLearn.total_companies ?? '—'}
                hint={`Covered ${continuousGatherLearn.covered_companies ?? continuousGatherLearn.companies_fully_backfilled ?? '—'}`}
              />
              <Stat
                label="Coverage %"
                value={
                  continuousGatherLearn.historical_coverage_pct != null
                    ? `${continuousGatherLearn.historical_coverage_pct}%`
                    : '—'
                }
                hint="Living universe — never permanently finished"
              />
              <Stat
                label="Hard / Soft"
                value={
                  continuousGatherLearn.hard_coverage_pct != null
                    ? `${continuousGatherLearn.hard_coverage_pct}% / ${continuousGatherLearn.soft_coverage_pct ?? '—'}%`
                    : '—'
                }
                hint="Hard gates maintenance; soft is richness"
              />
              <Stat
                label="Avg History / Co"
                value={
                  continuousGatherLearn.average_history_years != null
                    ? `${continuousGatherLearn.average_history_years}y`
                    : '—'
                }
                hint="Price + annual depth"
              />
              <Stat
                label="Queue Length"
                value={continuousGatherLearn.queue_length ?? continuousGatherLearn.remaining_backlog ?? '—'}
                hint={`Today ${continuousGatherLearn.companies_processed_today ?? 0} · ready for new listings`}
              />
              <Stat
                label="New / IPO / Delist"
                value={`${continuousGatherLearn.new_listings_count ?? 0} / ${continuousGatherLearn.pending_ipos_count ?? 0} / ${continuousGatherLearn.delisted_count ?? 0}`}
                hint="Auto-enqueue on IPO list"
              />
              <Stat
                label="Embeddings"
                value={continuousGatherLearn.embeddings_total ?? '—'}
                hint={`Extracts ${continuousGatherLearn.knowledge_extracts_total ?? continuousGatherLearn.metrics?.knowledge_extracts_total ?? '—'} · Docs ${continuousGatherLearn.documents_downloaded ?? '—'}`}
              />
              <Stat
                label="Backfill Mode"
                value={
                  continuousGatherLearn.maintenance_only
                    ? 'maintenance'
                    : continuousGatherLearn.backfill_mode || (continuousGatherLearn.continues_until_complete ? 'deep' : '—')
                }
                status={continuousGatherLearn.maintenance_only ? 'healthy' : 'warn'}
                hint={
                  continuousGatherLearn.estimated_completion_days != null
                    ? `ETA ~${continuousGatherLearn.estimated_completion_days}d`
                    : 'Queue always ready'
                }
              />
            </div>
            {Array.isArray(continuousGatherLearn.company_scorecards) && continuousGatherLearn.company_scorecards.length > 0 ? (
              <Glass className="overflow-x-auto">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">
                  Knowledge density · Hard / Soft / Overall
                </p>
                <table className="w-full min-w-[640px] text-left text-xs text-[var(--io-ink)]">
                  <thead className="text-[var(--io-muted)]">
                    <tr>
                      <th className="py-1 pr-3 font-medium">Company</th>
                      <th className="py-1 pr-3 font-medium">Years</th>
                      <th className="py-1 pr-3 font-medium">Hard</th>
                      <th className="py-1 pr-3 font-medium">Soft</th>
                      <th className="py-1 pr-3 font-medium">Overall</th>
                      <th className="py-1 pr-3 font-medium">Docs</th>
                      <th className="py-1 pr-3 font-medium">Extracts</th>
                      <th className="py-1 pr-3 font-medium">Embeds</th>
                      <th className="py-1 font-medium">Density</th>
                    </tr>
                  </thead>
                  <tbody>
                    {continuousGatherLearn.company_scorecards.slice(0, 8).map((row) => (
                      <tr key={row.company} className="border-t border-[var(--io-line)]/40">
                        <td className="py-1.5 pr-3 font-semibold">{row.company}</td>
                        <td className="py-1.5 pr-3">{row.years ?? '—'}</td>
                        <td className="py-1.5 pr-3">{row.hard_pct != null ? `${row.hard_pct}%` : '—'}</td>
                        <td className="py-1.5 pr-3">{row.soft_pct != null ? `${row.soft_pct}%` : '—'}</td>
                        <td className="py-1.5 pr-3">{row.overall_pct != null ? `${row.overall_pct}%` : '—'}</td>
                        <td className="py-1.5 pr-3">{row.documents ?? '—'}</td>
                        <td className="py-1.5 pr-3">{row.extracts ?? '—'}</td>
                        <td className="py-1.5 pr-3">{row.embeddings ?? '—'}</td>
                        <td className="py-1.5">{row.density ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Glass>
            ) : null}
            <Glass className="text-xs text-[var(--io-muted)]">
              <p>
                Living universe: backlog may be empty but is never retired — new IPOs/listings auto-enqueue and
                reopen deep backfill. Soft gaps (transcripts, ESG) do not permanently mark a company incomplete.
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-caption)]">
                Freshness LIDI {continuousGatherLearn.freshness?.lidi || '—'} · KF HD{' '}
                {continuousGatherLearn.freshness?.kf_hd || '—'} · Remaining{' '}
                {continuousGatherLearn.companies_remaining ?? continuousGatherLearn.remaining_backlog ?? '—'} ·
                Collector success{' '}
                {continuousGatherLearn.collector_success_rate != null
                  ? `${continuousGatherLearn.collector_success_rate}%`
                  : '—'}
              </p>
            </Glass>

            {continuousGatherLearn.ops ? (
              <div className="space-y-3 pt-1">
                <Kicker>Historical Ops · Data plane (verified)</Kicker>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Stat
                    label="Scheduler"
                    value={continuousGatherLearn.ops.operational_status?.scheduler ?? '—'}
                    status={
                      continuousGatherLearn.ops.operational_status?.scheduler === 'misaligned'
                        ? 'warn'
                        : 'healthy'
                    }
                    hint={
                      continuousGatherLearn.ops.operational_status?.maintenance_allowed
                        ? 'Maintenance allowed'
                        : 'Deep backfill required'
                    }
                  />
                  <Stat
                    label="Verified Hard Coverage"
                    value={
                      continuousGatherLearn.ops.historical_coverage_verified?.verified_hard_coverage_pct !=
                      null
                        ? `${continuousGatherLearn.ops.historical_coverage_verified.verified_hard_coverage_pct}%`
                        : continuousGatherLearn.ops.historical_depth?.completeness_pct != null
                          ? `${continuousGatherLearn.ops.historical_depth.completeness_pct}%`
                          : '—'
                    }
                    hint="From stored datasets — not queue"
                  />
                  <Stat
                    label="OHLCV / Financials"
                    value={`${continuousGatherLearn.ops.historical_coverage_verified?.ohlcv_pct ?? '—'}% / ${
                      continuousGatherLearn.ops.historical_coverage_verified?.financials_pct ??
                      continuousGatherLearn.ops.financial_coverage?.coverage_pct ??
                      '—'
                    }%`}
                    hint="Data-plane coverage"
                  />
                  <Stat
                    label="Shareholding / IR"
                    value={`${
                      continuousGatherLearn.ops.historical_coverage_verified?.shareholding_pct ??
                      continuousGatherLearn.ops.shareholding_coverage?.coverage_pct ??
                      '—'
                    }% / ${
                      continuousGatherLearn.ops.historical_coverage_verified?.ir_pct ??
                      continuousGatherLearn.ops.ir_coverage?.coverage_pct ??
                      '—'
                    }%`}
                    hint="Required institutional sets"
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Stat
                    label="Completed Today"
                    value={continuousGatherLearn.ops.backfill_throughput?.companies_completed_today ?? '—'}
                    hint={`Years added ${continuousGatherLearn.ops.backfill_throughput?.average_years_added_today ?? '—'}`}
                  />
                  <Stat
                    label="Docs / Extracts Today"
                    value={`${continuousGatherLearn.ops.backfill_throughput?.documents_downloaded_today ?? 0} / ${continuousGatherLearn.ops.backfill_throughput?.knowledge_extracts_today ?? 0}`}
                    hint="Throughput"
                  />
                  <Stat
                    label="Verified Incomplete"
                    value={
                      continuousGatherLearn.ops.historical_coverage_verified?.incomplete ??
                      continuousGatherLearn.ops.coverage_reconcile?.incomplete ??
                      '—'
                    }
                    hint={`Repair ${continuousGatherLearn.ops.repair_queue ?? '—'}`}
                  />
                  <Stat
                    label="Degraded Collectors"
                    value={continuousGatherLearn.ops.degraded_collectors ?? '—'}
                    status={
                      (continuousGatherLearn.ops.degraded_collectors || 0) > 0 ? 'warn' : 'healthy'
                    }
                    hint="Collector plane"
                  />
                </div>

                {Array.isArray(
                  continuousGatherLearn.ops.evidence_backlog ||
                    continuousGatherLearn.ops.evidence_based_completion?.backlog ||
                    continuousGatherLearn.ops.coverage_reconcile?.evidence_backlog ||
                    continuousGatherLearn.ops.coverage_reconcile?.incomplete_preview
                ) &&
                (
                  continuousGatherLearn.ops.evidence_backlog ||
                  continuousGatherLearn.ops.evidence_based_completion?.backlog ||
                  continuousGatherLearn.ops.coverage_reconcile?.evidence_backlog ||
                  continuousGatherLearn.ops.coverage_reconcile?.incomplete_preview ||
                  []
                ).length > 0 ? (
                  <Glass className="overflow-x-auto">
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">
                      Evidence-based completion · why still in backlog
                    </p>
                    <p className="mb-2 text-[11px] text-[var(--io-muted)]">
                      Completion is derived from stored evidence (not queue state). Hard coverage is the
                      share of required datasets present.
                    </p>
                    <table className="w-full min-w-[860px] text-left text-xs text-[var(--io-ink)]">
                      <thead className="text-[var(--io-muted)]">
                        <tr>
                          <th className="py-1 pr-3 font-medium">Company</th>
                          <th className="py-1 pr-3 font-medium">Hard %</th>
                          <th className="py-1 pr-3 font-medium">Complete</th>
                          <th className="py-1 pr-3 font-medium">Evidence</th>
                          <th className="py-1 font-medium">Why in backlog</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(
                          continuousGatherLearn.ops.evidence_backlog ||
                          continuousGatherLearn.ops.evidence_based_completion?.backlog ||
                          continuousGatherLearn.ops.coverage_reconcile?.evidence_backlog ||
                          continuousGatherLearn.ops.coverage_reconcile?.incomplete_preview ||
                          []
                        )
                          .slice(0, 24)
                          .map((row) => {
                            const evidence = row.evidence || {};
                            const checklist = Array.isArray(row.checklist) ? row.checklist : [];
                            const marks =
                              checklist.length > 0
                                ? checklist.map((c) => `${c.label} ${c.mark}`).join(' · ')
                                : Object.keys(evidence).length
                                  ? Object.entries(evidence)
                                      .map(([k, v]) => `${k} ${v}`)
                                      .join(' · ')
                                  : (row.missing_labels || row.missing || []).join(', ') || '—';
                            return (
                              <tr
                                key={row.company || marks}
                                className="border-t border-[var(--io-line)]/40 align-top"
                              >
                                <td className="py-1.5 pr-3 font-semibold">{row.company || '—'}</td>
                                <td className="py-1.5 pr-3 tabular-nums">
                                  {row.hard_coverage_pct != null
                                    ? `${row.hard_coverage_pct}%`
                                    : row.hard_pct != null
                                      ? `${row.hard_pct}%`
                                      : '—'}
                                </td>
                                <td className="py-1.5 pr-3 font-semibold text-amber-300">
                                  {row.complete ? 'YES' : 'NO'}
                                </td>
                                <td className="py-1.5 pr-3 text-[11px] text-[var(--io-muted)]">{marks}</td>
                                <td className="py-1.5 text-[11px]">
                                  {row.why_in_backlog || row.why_incomplete || 'Incomplete evidence'}
                                </td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </Glass>
                ) : null}

                {Array.isArray(continuousGatherLearn.ops.collector_health) &&
                continuousGatherLearn.ops.collector_health.length > 0 ? (
                  <Glass className="overflow-x-auto">
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">
                      Collector health
                    </p>
                    <table className="w-full min-w-[720px] text-left text-xs text-[var(--io-ink)]">
                      <thead className="text-[var(--io-muted)]">
                        <tr>
                          <th className="py-1 pr-3 font-medium">Collector</th>
                          <th className="py-1 pr-3 font-medium">Success</th>
                          <th className="py-1 pr-3 font-medium">Last Run</th>
                          <th className="py-1 pr-3 font-medium">Latency</th>
                          <th className="py-1 pr-3 font-medium">Queue</th>
                          <th className="py-1 font-medium">Error Rate</th>
                        </tr>
                      </thead>
                      <tbody>
                        {continuousGatherLearn.ops.collector_health.map((row) => (
                          <tr key={row.collector} className="border-t border-[var(--io-line)]/40">
                            <td className="py-1.5 pr-3 font-semibold">{row.collector}</td>
                            <td className="py-1.5 pr-3">
                              {row.success === 'ok' ? 'OK' : row.success === 'warn' ? 'Warn' : row.success === 'error' ? 'Fail' : '—'}
                            </td>
                            <td className="py-1.5 pr-3">
                              {row.last_run ? String(row.last_run).slice(11, 16) || String(row.last_run).slice(0, 16) : '—'}
                            </td>
                            <td className="py-1.5 pr-3">
                              {row.latency_s != null ? `${row.latency_s}s` : '—'}
                            </td>
                            <td className="py-1.5 pr-3">{row.queue ?? 0}</td>
                            <td className="py-1.5">{row.error_rate_pct != null ? `${row.error_rate_pct}%` : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </Glass>
                ) : null}

                <div className="grid gap-3 lg:grid-cols-3">
                  {Array.isArray(continuousGatherLearn.ops.coverage_heat_map) &&
                  continuousGatherLearn.ops.coverage_heat_map.length > 0 ? (
                    <Glass className="overflow-x-auto lg:col-span-1">
                      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">
                        Coverage heat map
                      </p>
                      <table className="w-full text-left text-xs text-[var(--io-ink)]">
                        <thead className="text-[var(--io-muted)]">
                          <tr>
                            <th className="py-1 pr-3 font-medium">Dataset</th>
                            <th className="py-1 font-medium">Coverage</th>
                          </tr>
                        </thead>
                        <tbody>
                          {continuousGatherLearn.ops.coverage_heat_map.map((row) => (
                            <tr key={row.dataset} className="border-t border-[var(--io-line)]/40">
                              <td className="py-1.5 pr-3">{row.dataset}</td>
                              <td className="py-1.5 font-semibold">{row.coverage_pct}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </Glass>
                  ) : null}

                  {Array.isArray(continuousGatherLearn.ops.source_reliability) &&
                  continuousGatherLearn.ops.source_reliability.length > 0 ? (
                    <Glass className="overflow-x-auto lg:col-span-1">
                      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">
                        Source reliability
                      </p>
                      <table className="w-full text-left text-xs text-[var(--io-ink)]">
                        <thead className="text-[var(--io-muted)]">
                          <tr>
                            <th className="py-1 pr-3 font-medium">Source</th>
                            <th className="py-1 font-medium">Reliability</th>
                          </tr>
                        </thead>
                        <tbody>
                          {continuousGatherLearn.ops.source_reliability.map((row) => (
                            <tr key={row.source} className="border-t border-[var(--io-line)]/40">
                              <td className="py-1.5 pr-3">{row.source}</td>
                              <td className="py-1.5 font-semibold">
                                {row.reliability_pct != null ? `${row.reliability_pct}%` : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </Glass>
                  ) : null}

                  {Array.isArray(continuousGatherLearn.ops.coverage_by_index) &&
                  continuousGatherLearn.ops.coverage_by_index.length > 0 ? (
                    <Glass className="overflow-x-auto lg:col-span-1">
                      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--io-caption)]">
                        Coverage by index
                      </p>
                      <table className="w-full text-left text-xs text-[var(--io-ink)]">
                        <thead className="text-[var(--io-muted)]">
                          <tr>
                            <th className="py-1 pr-3 font-medium">Index</th>
                            <th className="py-1 font-medium">Coverage</th>
                          </tr>
                        </thead>
                        <tbody>
                          {continuousGatherLearn.ops.coverage_by_index
                            .filter((row) => (row.universe || 0) > 0 || row.index?.startsWith('NIFTY'))
                            .map((row) => (
                              <tr key={row.index} className="border-t border-[var(--io-line)]/40">
                                <td className="py-1.5 pr-3">{row.index}</td>
                                <td className="py-1.5 font-semibold">
                                  {row.coverage_pct}%{' '}
                                  <span className="font-normal text-[var(--io-muted)]">
                                    ({row.covered}/{row.universe})
                                  </span>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </Glass>
                  ) : null}
                </div>

                {continuousGatherLearn.ops.coverage_audit?.counts ? (
                  <Glass className="text-xs text-[var(--io-muted)]">
                    <p className="font-semibold text-[var(--io-ink)]">Weekly coverage audit</p>
                    <p className="mt-1">
                      Missing periods {continuousGatherLearn.ops.coverage_audit.counts.missing_historical_periods ?? 0} ·
                      Incomplete financials{' '}
                      {continuousGatherLearn.ops.coverage_audit.counts.incomplete_financials ?? 0} · Missing
                      embeddings {continuousGatherLearn.ops.coverage_audit.counts.missing_embeddings ?? 0} · QA
                      failures {continuousGatherLearn.ops.coverage_audit.counts.qa_failures ?? 0} · Repair queue{' '}
                      {continuousGatherLearn.ops.coverage_audit.counts.repair_queue ?? 0}
                      {continuousGatherLearn.ops.coverage_audit.skipped
                        ? ' · fresh (<7d)'
                        : continuousGatherLearn.ops.coverage_audit.generated_at
                          ? ` · ${String(continuousGatherLearn.ops.coverage_audit.generated_at).slice(0, 10)}`
                          : ''}
                    </p>
                  </Glass>
                ) : null}

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Stat
                    label="Financial Coverage"
                    value={
                      continuousGatherLearn.ops.financial_coverage?.coverage_pct != null
                        ? `${continuousGatherLearn.ops.financial_coverage.coverage_pct}%`
                        : '—'
                    }
                    hint="Institutional statements"
                  />
                  <Stat
                    label="Shareholding Coverage"
                    value={
                      continuousGatherLearn.ops.shareholding_coverage?.coverage_pct != null
                        ? `${continuousGatherLearn.ops.shareholding_coverage.coverage_pct}%`
                        : '—'
                    }
                    hint="Promoter/FII/DII"
                  />
                  <Stat
                    label="IR Coverage"
                    value={
                      continuousGatherLearn.ops.ir_coverage?.coverage_pct != null
                        ? `${continuousGatherLearn.ops.ir_coverage.coverage_pct}%`
                        : '—'
                    }
                    hint="Discovered documents"
                  />
                  <Stat
                    label="Repair Queue"
                    value={continuousGatherLearn.ops.repair_queue ?? continuousGatherLearn.ops.kpis?.repair_queue_size ?? '—'}
                    hint="Auto-heal backlog"
                  />
                </div>

                <Glass className="text-xs text-[var(--io-muted)]">
                  <p className="font-semibold text-[var(--io-ink)]">Persistence & checkpoints</p>
                  <p className="mt-1">
                    Queue {continuousGatherLearn.ops.persistent_queue ? 'durable' : '—'} · Checkpoints{' '}
                    {continuousGatherLearn.ops.checkpoint_status?.checkpoints?.length ?? 0} · Storage{' '}
                    {continuousGatherLearn.ops.storage_usage?.mb != null
                      ? `${continuousGatherLearn.ops.storage_usage.mb} MB`
                      : '—'}{' '}
                    · Recovered stuck{' '}
                    {continuousGatherLearn.ops.recovery?.stuck_running_reset ?? 0}
                    {continuousGatherLearn.ops.living_universe_ops?.new_listings != null
                      ? ` · New listings ${Array.isArray(continuousGatherLearn.ops.living_universe_ops.new_listings) ? continuousGatherLearn.ops.living_universe_ops.new_listings.length : continuousGatherLearn.ops.living_universe_ops.new_listings}`
                      : ''}
                  </p>
                </Glass>
              </div>
            ) : null}
          </section>
        ) : null}

        {v4Present ? (
          <section className="space-y-3">
            <Kicker>AGI v4.0 · Investment Office OS</Kicker>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <Stat
                label="Thesis Office"
                value={v4Office.thesis?.status || (v4Office.thesis ? 'ready' : '—')}
                hint={v4Office.thesis?.version || 'ITE'}
              />
              <Stat
                label="Decision Office"
                value={v4Office.decision?.status || (v4Office.decision ? 'ready' : '—')}
                hint={v4Office.decision?.version || 'IDO'}
              />
              <Stat
                label="Portfolio Ideas"
                value={v4Office.portfolio?.n_ideas ?? (v4Office.portfolio ? 'ready' : '—')}
                hint="ideas ≠ positions"
              />
              <Stat
                label="Monitoring"
                value={v4Office.monitoring?.n_events ?? (v4Office.monitoring ? 'ready' : '—')}
                hint={
                  v4Office.monitoring?.requires_review != null
                    ? `${v4Office.monitoring.requires_review} review`
                    : 'events recommend review'
                }
              />
              <Stat
                label="Learning"
                value={v4Office.learning?.n_learnings ?? (v4Office.learning ? 'ready' : '—')}
                hint="process memory"
              />
            </div>
          </section>
        ) : null}

        {/* SECTION 2 */}
        <section className="space-y-3">
          <Kicker>Section 2 · Platform Status</Kicker>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredPlatforms.map((p) => (
              <button
                key={p.name}
                type="button"
                onClick={() => setSelectedPlatform(p)}
                className="text-left"
              >
                <Glass className="hover:border-[var(--io-gold)] transition">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-[var(--io-ink)]">{p.name}</p>
                    <span className={`text-[11px] font-bold ${statusColour(p.current_status)}`}>
                      {p.current_status}
                    </span>
                  </div>
                  <p className="mt-2 text-[11px] text-[var(--io-muted)]">
                    Errors {p.error_count ?? 0} · Warnings {p.warnings ?? 0}
                    {p.knowledge_count != null ? ` · Knowledge ${p.knowledge_count}` : ''}
                  </p>
                  <p className="mt-1 text-[10px] text-[var(--io-caption)]">
                    {(p.dependencies || []).slice(0, 4).join(' · ') || '—'}
                  </p>
                </Glass>
              </button>
            ))}
          </div>
          {selectedPlatform ? (
            <Glass>
              <div className="flex justify-between gap-3">
                <h3 className="io-title text-xl">{selectedPlatform.name} diagnostics</h3>
                <button type="button" className="text-xs text-[var(--io-gold)]" onClick={() => setSelectedPlatform(null)}>
                  Close
                </button>
              </div>
              <pre className="mt-3 max-h-64 overflow-auto text-[11px] text-[var(--io-ink-soft)]">
                {JSON.stringify(selectedPlatform, null, 2)}
              </pre>
            </Glass>
          ) : null}
        </section>

        {/* SECTION 3 + 4 */}
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <Kicker>Section 3 · Engine Status</Kicker>
            <Glass>
              <ul className="space-y-2 max-h-80 overflow-auto">
                {engines.map((e) => (
                  <li key={e.name} className="flex items-center justify-between border-b border-[var(--io-border)] pb-2 text-sm">
                    <span className="font-medium text-[var(--io-ink)]">{e.name}</span>
                    <span className={statusColour(e.status)}>{e.status}</span>
                  </li>
                ))}
              </ul>
            </Glass>
          </div>
          <div className="space-y-3">
            <Kicker>Section 4 · API Status</Kicker>
            <Glass>
              <ul className="space-y-2 max-h-80 overflow-auto">
                {apis
                  .filter((p) => !query || JSON.stringify(p).toLowerCase().includes(query.toLowerCase()))
                  .slice(0, 24)
                  .map((p) => (
                    <li key={p.name} className="border-b border-[var(--io-border)] pb-2 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-[var(--io-ink)]">{p.name}</span>
                        <span className={statusColour(p.status)}>
                          {p.colour || p.status}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                        {p.last_error ? `Last error: ${p.last_error}` : p.provider_confidence || '—'}
                        {p.circuit_state ? ` · circuit ${p.circuit_state}` : ''}
                      </p>
                    </li>
                  ))}
              </ul>
            </Glass>
          </div>
        </section>

        {/* What intelligence learned — last 5 days */}
        <section className="space-y-3">
          <Kicker>Learning digest · Last 5 days</Kicker>
          <Glass>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="max-w-3xl">
                <p className="text-sm leading-relaxed text-[var(--io-ink-soft)]">
                  {learning5d?.summary ||
                    knowledge.last_5_days_summary ||
                    'Learning digest will appear after CMS article learning runs.'}
                </p>
                <p className="mt-2 text-[11px] text-[var(--io-caption)]">
                  Window {learning5d?.days || 5}d · {learning5d?.timezone || 'Asia/Kolkata'} · articles{' '}
                  {learning5d?.articles_learned ?? knowledge.research_learned ?? '—'} · pending{' '}
                  {learning5d?.pending_count ?? '—'}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 text-right text-sm">
                <div>
                  <p className="text-[10px] uppercase text-[var(--io-caption)]">Learned</p>
                  <p className="text-xl font-semibold text-emerald-400 tabular-nums">
                    {learning5d?.articles_learned ?? '—'}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-[var(--io-caption)]">Failed</p>
                  <p className="text-xl font-semibold text-[var(--io-ink)] tabular-nums">
                    {learning5d?.failed ?? 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              <div>
                <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">By day</p>
                <ul className="mt-2 space-y-1.5 text-sm max-h-48 overflow-auto">
                  {(learning5d?.by_day || knowledge.last_5_days || []).map((d) => (
                    <li
                      key={d.learning_date}
                      className="flex items-start justify-between gap-3 border-b border-[var(--io-border)] pb-1.5"
                    >
                      <div>
                        <p className="font-medium text-[var(--io-ink)]">{d.learning_date}</p>
                        {(d.titles || []).length ? (
                          <p className="text-[11px] text-[var(--io-muted)] line-clamp-2">
                            {d.titles.slice(0, 3).join(' · ')}
                          </p>
                        ) : null}
                      </div>
                      <p className="shrink-0 tabular-nums text-emerald-400">
                        {d.articles_learned ?? d.learned ?? 0}
                      </p>
                    </li>
                  ))}
                  {!(learning5d?.by_day || knowledge.last_5_days || []).length ? (
                    <li className="text-[var(--io-muted)]">No dated learning events in this window.</li>
                  ) : null}
                </ul>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">Highlights</p>
                <ul className="mt-2 space-y-1.5 text-sm max-h-48 overflow-auto text-[var(--io-ink-soft)]">
                  {(learning5d?.highlights || knowledge.last_5_days_highlights || []).map((title) => (
                    <li key={title} className="border-b border-[var(--io-border)] pb-1.5">
                      {title}
                    </li>
                  ))}
                  {!(learning5d?.highlights || knowledge.last_5_days_highlights || []).length ? (
                    <li className="text-[var(--io-muted)]">No article highlights yet.</li>
                  ) : null}
                </ul>
                {(learning5d?.corpus?.learned_today || []).length ? (
                  <div className="mt-3">
                    <p className="text-[11px] uppercase tracking-wide text-[var(--io-caption)]">
                      Corpus notes
                    </p>
                    <ul className="mt-1 space-y-1 text-xs text-[var(--io-muted)]">
                      {learning5d.corpus.learned_today.slice(0, 4).map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            </div>
          </Glass>
        </section>

        {/* SECTION 5 + 6 */}
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <Kicker>Section 5 · Knowledge Growth</Kicker>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="CMS Articles · 5d" value={knowledge.research_learned ?? learning5d?.articles_learned} />
              <Stat label="Books Learned" value={knowledge.books_learned} />
              <Stat label="Concepts" value={knowledge.concepts_added} />
              <Stat label="Frameworks" value={knowledge.frameworks_added} />
              <Stat label="Formulas" value={knowledge.formulas_added} />
              <Stat label="Companies Updated" value={knowledge.companies_updated} />
              <Stat label="HV Reviews" value={knowledge.house_view_reviews} />
            </div>
          </div>
          <div className="space-y-3">
            <Kicker>Section 6 · Coverage</Kicker>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Overall" value={coverage.overall_coverage != null ? `${coverage.overall_coverage}%` : '—'} />
              <Stat label="Financial" value={coverage.financial_coverage != null ? `${coverage.financial_coverage}%` : '—'} />
              <Stat label="Academy" value={coverage.academy_coverage != null ? `${coverage.academy_coverage}%` : '—'} />
              <Stat label="Research" value={coverage.research_coverage ?? '—'} />
            </div>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Below threshold (first)</p>
              <ul className="mt-2 space-y-1 text-sm max-h-40 overflow-auto">
                {(coverage.below_threshold || []).slice(0, 8).map((b, idx) => (
                  <li key={b.ticker || idx} className="text-[var(--io-ink-soft)]">
                    <span className="font-semibold text-[var(--io-ink)]">{b.ticker || '—'}</span> — {b.reason || 'coverage'}
                  </li>
                ))}
                {!(coverage.below_threshold || []).length ? (
                  <li className="text-[var(--io-muted)]">No below-threshold rows surfaced.</li>
                ) : null}
              </ul>
            </Glass>
          </div>
        </section>

        {/* SECTION 6b · Institutional Evidence Retrieval (IERE) */}
        <section className="space-y-3">
          <Kicker>Section 6b · Evidence Retrieval (IERE)</Kicker>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <Stat
              label="Status"
              value={evidenceRetrieval?.status || '—'}
              status={evidenceRetrieval?.status}
            />
            <Stat
              label="Evidence Coverage"
              value={
                evidenceRetrieval?.evidence_coverage?.ranked_count != null
                  ? evidenceRetrieval.evidence_coverage.ranked_count
                  : '—'
              }
              hint="Ranked items (last run)"
            />
            <Stat
              label="Freshness"
              value={
                evidenceRetrieval?.evidence_freshness != null
                  ? evidenceRetrieval.evidence_freshness
                  : '—'
              }
            />
            <Stat
              label="Latency"
              value={
                evidenceRetrieval?.retrieval_latency_ms != null
                  ? `${evidenceRetrieval.retrieval_latency_ms} ms`
                  : '—'
              }
            />
            <Stat
              label="Citation Coverage"
              value={
                evidenceRetrieval?.citation_coverage != null
                  ? `${Math.round(Number(evidenceRetrieval.citation_coverage) * 100)}%`
                  : '—'
              }
            />
            <Stat
              label="Replay Health"
              value={
                evidenceRetrieval?.replay_health?.ok === false
                  ? 'Leak'
                  : evidenceRetrieval?.replay_health?.ok
                    ? 'OK'
                    : '—'
              }
              status={evidenceRetrieval?.replay_health?.ok ? 'Healthy' : evidenceRetrieval ? 'Warning' : undefined}
            />
            <Stat
              label="Confidence"
              value={
                evidenceRetrieval?.evidence_confidence != null
                  ? evidenceRetrieval.evidence_confidence
                  : '—'
              }
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Documents (IDI)</p>
              <p className="mt-2 text-sm text-[var(--io-ink-soft)]">
                {institutionalDocs
                  ? `${institutionalDocs.documents ?? '—'} docs · ${institutionalDocs.knowledge_objects_created ?? '—'} objects`
                  : 'Unavailable'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Live Data (LIDI)</p>
              <p className="mt-2 text-sm text-[var(--io-ink-soft)]">
                {liveDataBoard
                  ? `${liveDataBoard.collectors_operational ?? '—'}/${liveDataBoard.collectors_total ?? '—'} collectors · ${liveDataBoard.state || '—'}`
                  : 'Unavailable'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">North star</p>
              <p className="mt-2 text-sm text-[var(--io-ink-soft)]">
                {evidenceRetrieval?.north_star ||
                  'Every AGIB question retrieves ranked institutional evidence packs'}
              </p>
            </Glass>
          </div>
        </section>

        {/* Financial Statements Engine · FDO ops */}
        <section className="space-y-3">
          <Kicker>Financial Statements · Data Operations (FDO)</Kicker>
          <p className="text-sm text-[var(--io-muted)]">
            Soft-wire coverage, completeness, throughput and source health over the existing FSE
            pipeline. Success = coverage · freshness · reliability — not new engines.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">FSE</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(fseBoard?.status)}`}>
                {fseBoard?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                {fseBoard?.version || 'financial_statements_engine'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Coverage %</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--io-ink)]">
                {fdoBoard?.coverage_pct ?? '—'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Completeness {fdoBoard?.completeness_pct ?? '—'}%
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Queue / DLQ</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--io-ink)]">
                {fdoBoard?.queue_depth ?? '—'} / {fdoBoard?.dlq_size ?? '—'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Throughput {fdoBoard?.workflow_throughput ?? '—'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Raw evidence</p>
              <p className="mt-2 text-2xl font-semibold text-[var(--io-ink)]">
                {fdoBoard?.raw_evidence_files ?? '—'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Annual {fdoBoard?.annual_filings ?? '—'} · Qtr {fdoBoard?.quarterly_filings ?? '—'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Sources / alerts</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(fseSourceBoard?.status)}`}>
                {fseSourceBoard?.sources_n ?? '—'} sources
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Alerts {fdoBoard?.alerts_n ?? '—'} ·{' '}
                {(fdoBoard?.top_missing_companies || [])
                  .slice(0, 2)
                  .map((c) => c.ticker)
                  .join(', ') || 'no gaps listed'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">FIRE-01</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(fireBoard?.status)}`}>
                {fireBoard?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Narrative & trends · no BUY/SELL ·{' '}
                {fireBoard?.version || 'financial_intelligence'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">FIRE-02 Drivers</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(fireDriversBoard?.status)}`}>
                {fireDriversBoard?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Relationships {fireDriversBoard?.relationship_findings ?? '—'} · cash warn{' '}
                {fireDriversBoard?.cash_quality_warnings ?? '—'} · WC warn{' '}
                {fireDriversBoard?.working_capital_warnings ?? '—'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">FKB-01 Knowledge</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(fkbBoard?.status)}`}>
                {fkbBoard?.validation_status || fkbBoard?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Metrics {fkbBoard?.metrics_loaded ?? '—'} · Ratios {fkbBoard?.ratios_loaded ?? '—'} ·
                Rel {fkbBoard?.relationships_loaded ?? '—'}
              </p>
            </Glass>
          </div>
        </section>

        {/* Research-centric intelligence stack (Phases 10–12 + RIH v4.0) */}
        <section className="space-y-3">
          <Kicker>Intelligence Stack · Research-Centric Graph</Kicker>
          <p className="text-sm text-[var(--io-muted)]">
            Research notes are the primary knowledge object. Market / Sector / Macro intelligence
            soft-wire into every Intelligence Hub.
          </p>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Research Hub (RIH)</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(researchHub?.status)}`}>
                {researchHub?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Hubs {researchHub?.hub_count ?? '—'} · phase {researchHub?.phase || '4.0'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Market Forecast (MKFI)</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(marketForecast?.status)}`}>
                {marketForecast?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Scenarios {marketForecast?.scenarios ?? '—'} · conf{' '}
                {marketForecast?.confidence_pct ?? '—'}%
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Sector Forecast (SFI)</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(sectorForecast?.status)}`}>
                {sectorForecast?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Scenarios {sectorForecast?.scenarios ?? '—'} · phase {sectorForecast?.phase || '11.5'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Market Knowledge (CMKTP)</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(marketKnowledge?.status)}`}>
                {marketKnowledge?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Regime {marketKnowledge?.current_market_regime || '—'} · health{' '}
                {marketKnowledge?.market_health_score ?? '—'}
              </p>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Market Analogues (HMKAI)</p>
              <p className={`mt-2 text-sm font-semibold ${statusColour(marketAnalogues?.status)}`}>
                {marketAnalogues?.status || 'Unavailable'}
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-muted)]">
                Matches {marketAnalogues?.top_matches ?? '—'} · phase {marketAnalogues?.phase || '12.4'}
              </p>
            </Glass>
          </div>
        </section>

        {/* Observation Center — IO-01 Institutional Observation Engine */}
        <section className="space-y-3">
          <Kicker>Observation Center · IO-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Proactive institutional monitoring — material changes with hysteresis, decision
            re-evaluation triggers, and structured alerts. Soft board only.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat
              label="Today"
              value={observationCenter?.todays_observations ?? '—'}
              status={observationCenter?.status}
            />
            <Stat
              label="Critical"
              value={observationCenter?.critical_observations ?? '—'}
              status="Critical"
            />
            <Stat label="Decision changes" value={observationCenter?.decision_changes ?? '—'} />
            <Stat label="Pending reviews" value={observationCenter?.pending_reviews ?? '—'} />
            <Stat
              label="Throughput"
              value={observationCenter?.observation_throughput ?? '—'}
              hint={
                observationCenter?.observation_latency_ms != null
                  ? `Latency ${observationCenter.observation_latency_ms} ms`
                  : observationCenter
                    ? 'Hysteresis on'
                    : 'Unavailable'
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Recent critical</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(observationCenter?.recent_critical || []).slice(0, 8).map((o) => (
                <li key={o.observation_id || `${o.ticker}-${o.timestamp}`}>
                  {o.ticker || o.company}: {o.category} [{o.severity}] — {o.recommended_action}
                </li>
              ))}
              {!observationCenter ? (
                <li>Observation Center soft slice unavailable.</li>
              ) : null}
              {observationCenter && !(observationCenter.recent_critical || []).length ? (
                <li>No critical observations in memory yet.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Risk Center — PRE-01 */}
        <section className="space-y-3">
          <Kicker>Risk Center · PRE-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Authoritative portfolio risk — concentration, liquidity, stress impact, correlation
            drift, and coverage. Consumed by CIO-01; not a metrics dashboard.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Portfolio risk"
              value={portfolioRiskCenter?.overall_risk || '—'}
              status={portfolioRiskCenter?.status}
            />
            <Stat
              label="Highest concentration"
              value={
                portfolioRiskCenter?.highest_concentration?.ticker
                  ? `${portfolioRiskCenter.highest_concentration.ticker}`
                  : '—'
              }
              hint={
                portfolioRiskCenter?.highest_concentration?.weight != null
                  ? `${(Number(portfolioRiskCenter.highest_concentration.weight) * 100).toFixed(0)}% · ${portfolioRiskCenter.highest_concentration.level || ''}`
                  : undefined
              }
            />
            <Stat
              label="Liquidity warning"
              value={
                portfolioRiskCenter?.liquidity_warning
                  ? portfolioRiskCenter?.liquidity_level || 'Yes'
                  : portfolioRiskCenter?.liquidity_level || '—'
              }
            />
            <Stat
              label="Stress impact"
              value={
                portfolioRiskCenter?.stress_impact?.portfolio_impact_pct != null
                  ? `${Number(portfolioRiskCenter.stress_impact.portfolio_impact_pct).toFixed(1)}%`
                  : '—'
              }
              hint={portfolioRiskCenter?.stress_impact?.label}
            />
            <Stat
              label="Correlation drift"
              value={portfolioRiskCenter?.correlation_drift?.level || '—'}
              hint={
                portfolioRiskCenter?.correlation_drift?.average_correlation != null
                  ? `avg ${Number(portfolioRiskCenter.correlation_drift.average_correlation).toFixed(2)}`
                  : undefined
              }
            />
            <Stat label="Coverage" value={portfolioRiskCenter?.coverage ?? '—'} />
          </div>
          {!portfolioRiskCenter ? (
            <Glass>
              <p className="text-xs text-[var(--io-muted)]">Risk Center soft slice unavailable.</p>
            </Glass>
          ) : null}
        </section>

        {/* Policy Center — PCE-01 */}
        <section className="space-y-3">
          <Kicker>Policy Center · PCE-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Mandate compliance — active violations, compliance score, portfolios out of mandate,
            and constraints nearing limits. Governs CIO-01 recommendations.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat
              label="Active violations"
              value={policyCenter?.active_violations ?? '—'}
              status={policyCenter?.status}
            />
            <Stat label="Compliance score" value={policyCenter?.compliance_score ?? '—'} />
            <Stat
              label="New violations today"
              value={policyCenter?.new_violations_today ?? '—'}
            />
            <Stat
              label="Out of mandate"
              value={(policyCenter?.portfolios_out_of_mandate || []).length || '—'}
            />
            <Stat
              label="Nearing limits"
              value={policyCenter?.constraints_nearing_limits ?? '—'}
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">
              Status {policyCenter?.overall_status || '—'} · profile{' '}
              {policyCenter?.profile_id || '—'}
            </p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(policyCenter?.portfolios_out_of_mandate || []).slice(0, 6).map((p) => (
                <li key={`oom-${p}`}>Out of mandate: {p}</li>
              ))}
              {(policyCenter?.policy_assessment?.required_actions || []).slice(0, 6).map((a) => (
                <li key={`pa-${a}`}>Action: {a}</li>
              ))}
              {!policyCenter ? <li>Policy Center soft slice unavailable.</li> : null}
              {policyCenter &&
              !(policyCenter.portfolios_out_of_mandate || []).length &&
              !(policyCenter.policy_assessment?.required_actions || []).length ? (
                <li>Run a policy check to populate the Policy Center.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Orchestration Center — UAG-01 */}
        <section className="space-y-3">
          <Kicker>Orchestration Center · UAG-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Universal Ask AGI — active queries, planner latency, object coverage, failed plans, and
            missing registrations. Orchestration only; domain engines remain systems of record.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Active queries"
              value={orchestrationCenter?.active_queries ?? '—'}
              status={orchestrationCenter?.status}
            />
            <Stat
              label="Avg latency"
              value={
                orchestrationCenter?.average_latency != null
                  ? `${Number(orchestrationCenter.average_latency).toFixed(0)}ms`
                  : '—'
              }
            />
            <Stat
              label="Object coverage"
              value={orchestrationCenter?.object_coverage ?? '—'}
              hint={
                orchestrationCenter?.registered_object_count != null
                  ? `${orchestrationCenter.registered_object_count} registered`
                  : undefined
              }
            />
            <Stat label="Failed plans" value={orchestrationCenter?.failed_plans ?? '—'} />
            <Stat
              label="Missing registrations"
              value={(orchestrationCenter?.missing_registrations || []).length || '—'}
            />
            <Stat
              label="Queries run"
              value={orchestrationCenter?.planner_performance?.query_count ?? '—'}
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Recent orchestrated queries</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(orchestrationCenter?.recent_queries || []).slice(0, 6).map((q) => (
                <li key={q.query_id}>
                  [{q.intent}] {q.question}
                </li>
              ))}
              {!orchestrationCenter ? <li>Orchestration Center soft slice unavailable.</li> : null}
              {orchestrationCenter && !(orchestrationCenter.recent_queries || []).length ? (
                <li>Run a Universal Ask query to populate the center.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Institutional Coverage — ICF-01 */}
        <section className="space-y-3">
          <Kicker>Institutional Coverage · ICF-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Coverage Factory drives companies to Institutional Coverage Complete — not shallow crawl
            throughput. Daily target is companies entering ICC (configurable). Priority: Top 20 →
            Nifty 50 → Nifty 100 → Universe.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Stat
              label="ICC today"
              value={
                coverageFactory?.icc_entered_today != null
                  ? `${coverageFactory.icc_entered_today}`
                  : '—'
              }
              status={coverageFactory?.status}
            />
            <Stat
              label="Daily ICC target"
              value={
                coverageFactory?.daily_icc_target != null
                  ? `${coverageFactory.daily_icc_target}`
                  : coverageFactory?.max_companies_per_day != null
                    ? `${coverageFactory.max_companies_per_day}`
                    : '—'
              }
            />
            <Stat
              label="Capacity left"
              value={
                coverageFactory?.remaining_capacity_today != null
                  ? `${coverageFactory.remaining_capacity_today}`
                  : '—'
              }
            />
            <Stat
              label="Top-20 size"
              value={coverageFactory?.top20_size != null ? `${coverageFactory.top20_size}` : '20'}
            />
            <Stat
              label="Tick (min)"
              value={
                coverageFactory?.tick_interval_minutes != null
                  ? `${coverageFactory.tick_interval_minutes}`
                  : '15'
              }
            />
            <Stat label="ICF" value={coverageFactory?.version || 'icf-01'} />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">
              Universe → Planner → Acquire → Normalize → Validate → Registry → Memory → KG →
              Readiness → ICC
            </p>
            <p className="mt-2 text-xs text-[var(--io-ink-soft)]">
              {coverageFactory?.mission ||
                coverageFactory?.north_star ||
                'Companies entering Institutional Coverage Complete per day.'}
            </p>
            {!coverageFactory ? (
              <p className="mt-2 text-xs text-[var(--io-muted)]">
                Coverage Factory soft slice unavailable.
              </p>
            ) : null}
          </Glass>
        </section>

        {/* Knowledge Health — KIL-01 */}
        <section className="space-y-3">
          <Kicker>Knowledge Health · KIL-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Knowledge Integration Layer — AGI v1.1.2. CGL gathers; KIL transforms into canonical
            evidence; IEP validates and versions. One institutional knowledge pipeline. Nifty 500
            expansion unlocks only after Top-20 Institutional Coverage Complete.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Stat
              label="Knowledge ver"
              value={
                knowledgeHealth?.latest_knowledge_version ||
                evidenceCenter?.latest_knowledge_version ||
                '—'
              }
              status={knowledgeHealth?.status || evidenceCenter?.status}
            />
            <Stat
              label="CGL coverage"
              value={
                knowledgeHealth?.cgl?.hard_coverage_pct != null
                  ? `${knowledgeHealth.cgl.hard_coverage_pct}%`
                  : '—'
              }
            />
            <Stat
              label="CGL covered"
              value={
                knowledgeHealth?.cgl?.covered_companies != null &&
                knowledgeHealth?.cgl?.total_companies != null
                  ? `${knowledgeHealth.cgl.covered_companies}/${knowledgeHealth.cgl.total_companies}`
                  : '—'
              }
            />
            <Stat
              label="Collector OK"
              value={
                knowledgeHealth?.cgl?.collector_success != null
                  ? `${knowledgeHealth.cgl.collector_success}%`
                  : '—'
              }
            />
            <Stat
              label="Demo set"
              value={
                Array.isArray(knowledgeHealth?.phase1_demo)
                  ? `${knowledgeHealth.phase1_demo.length}`
                  : '5'
              }
            />
            <Stat label="KIL" value={knowledgeHealth?.version || 'kil-01'} />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">
              CGL → KIL → Canonical Evidence → Registry → Memory → Eligibility → Research Pack
            </p>
            <p className="mt-2 text-xs text-[var(--io-ink-soft)]">
              {knowledgeHealth?.kil?.mission ||
                evidenceCenter?.mission ||
                'Research is generated from continuously maintained institutional knowledge.'}
            </p>
            {!knowledgeHealth && !evidenceCenter ? (
              <p className="mt-2 text-xs text-[var(--io-muted)]">
                Knowledge Health soft slice unavailable.
              </p>
            ) : null}
          </Glass>
        </section>

        {/* Evidence Center — IEP-01 */}
        <section className="space-y-3">
          <Kicker>Evidence Center · IEP-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Institutional Knowledge OS — validates, versions, and preserves canonical knowledge from
            KIL. Intelligence engines consume durable knowledge; they do not substitute for it.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Stat
              label="Phase-1 ready"
              value={
                evidenceCenter?.research_ready_pct != null
                  ? `${evidenceCenter.research_ready_pct}%`
                  : '—'
              }
              status={evidenceCenter?.status}
            />
            <Stat
              label="Canonical FS"
              value={evidenceCenter?.companies_with_canonical_statements ?? '—'}
            />
            <Stat
              label="Complete evidence"
              value={evidenceCenter?.companies_with_complete_evidence ?? '—'}
            />
            <Stat
              label="Ready count"
              value={
                evidenceCenter?.research_ready_count != null && evidenceCenter?.phase1_total != null
                  ? `${evidenceCenter.research_ready_count}/${evidenceCenter.phase1_total}`
                  : '—'
              }
            />
            <Stat
              label="Block rate"
              value={
                evidenceCenter?.recommendation_block_rate_proxy_pct != null
                  ? `${evidenceCenter.recommendation_block_rate_proxy_pct}%`
                  : '—'
              }
            />
            <Stat
              label="Threshold"
              value={evidenceCenter?.threshold != null ? `${evidenceCenter.threshold}` : '—'}
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">
              Provider → Governance → Acquire → Canonical → Quality → Memory/Timeline → Claims →
              Eligibility → Decision → Lifecycle
            </p>
            <p className="mt-2 text-xs text-[var(--io-ink-soft)]">
              {evidenceCenter?.mission ||
                evidenceCenter?.guiding_principle ||
                'AGI is a knowledge platform — durable institutional knowledge, engines as consumers.'}
            </p>
            {!evidenceCenter ? (
              <p className="mt-2 text-xs text-[var(--io-muted)]">
                Evidence Center soft slice unavailable.
              </p>
            ) : null}
          </Glass>
        </section>

        {/* Acceptance Center — PAT-01 */}
        <section className="space-y-3">
          <Kicker>Acceptance Center · PAT-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Break AGIB before onboarding users — full-platform production acceptance across boot,
            data, intelligence, Ask, workspace, publishing, security, performance, and failure
            recovery. Architecture stays frozen.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <Stat
              label="Cases"
              value={
                acceptanceCenter?.total_cases != null
                  ? `${acceptanceCenter.passed ?? 0}/${acceptanceCenter.total_cases}`
                  : '—'
              }
              status={acceptanceCenter?.status}
            />
            <Stat
              label="Pass rate"
              value={
                acceptanceCenter?.pass_rate_pct != null
                  ? `${acceptanceCenter.pass_rate_pct}%`
                  : '—'
              }
            />
            <Stat
              label="Critical fails"
              value={acceptanceCenter?.critical_failures ?? '—'}
            />
            <Stat
              label="Arch score"
              value={acceptanceCenter?.architecture_score ?? '—'}
            />
            <Stat
              label="Security"
              value={
                acceptanceCenter?.security_violations != null
                  ? acceptanceCenter.security_violations === 0
                    ? 'Clean'
                    : `${acceptanceCenter.security_violations}`
                  : '—'
              }
            />
            <Stat
              label="Memory leaks"
              value={acceptanceCenter?.memory_leaks ?? '—'}
            />
            <Stat
              label="Certified"
              value={
                acceptanceCenter?.certified == null
                  ? acceptanceCenter?.overall_result || '—'
                  : acceptanceCenter.certified
                    ? 'Yes'
                    : 'No'
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">
              Next: closed beta (5–10 analysts)
            </p>
            <p className="mt-2 text-xs text-[var(--io-ink-soft)]">
              {acceptanceCenter?.closed_beta_recommendation ||
                'After PAT passes, run a closed beta with experienced finance professionals before v1.1.'}
            </p>
            {!acceptanceCenter ? (
              <p className="mt-2 text-xs text-[var(--io-muted)]">
                Acceptance Center soft slice unavailable.
              </p>
            ) : null}
          </Glass>
        </section>

        {/* Launch Center — L-01 */}
        <section className="space-y-3">
          <Kicker>Launch Center · L-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Usage validation before v1.1 — adoption, Ask performance, SLA status, user feedback, and
            gated feature flags. Driven by real workflows, not architectural expansion.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <Stat
              label="DAU"
              value={launchCenter?.daily_active_users ?? '—'}
              status={launchCenter?.status}
            />
            <Stat label="WAU" value={launchCenter?.weekly_active_users ?? '—'} />
            <Stat label="Ask / day" value={launchCenter?.ask_questions ?? '—'} />
            <Stat
              label="Ask P95"
              value={
                launchCenter?.ask_p95_ms != null ? `${launchCenter.ask_p95_ms}ms` : '—'
              }
            />
            <Stat label="Pubs" value={launchCenter?.publication_generated ?? '—'} />
            <Stat
              label="Helpful"
              value={
                launchCenter?.helpful_rate != null
                  ? `${Math.round(Number(launchCenter.helpful_rate) * 100)}%`
                  : '—'
              }
              hint={
                launchCenter?.feedback_total != null
                  ? `${launchCenter.feedback_total} responses`
                  : undefined
              }
            />
            <Stat
              label="SLAs"
              value={
                launchCenter?.sla_all_met == null
                  ? '—'
                  : launchCenter.sla_all_met
                    ? 'Met'
                    : `${launchCenter.sla_breach_count ?? 0} breach`
              }
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">SLA checks</p>
              <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
                {(launchCenter?.sla_checks || []).map((c) => (
                  <li key={c.metric}>
                    {c.status === 'met' ? '✓' : c.status === 'breach' ? '✗' : '·'} {c.metric}:{' '}
                    {c.actual ?? '—'} / {c.target}
                  </li>
                ))}
                {!launchCenter ? <li>Launch Center soft slice unavailable.</li> : null}
              </ul>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Feedback &amp; rollout</p>
              <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
                <li>
                  v1.1 flags gated:{' '}
                  {launchCenter?.feature_flags_all_disabled == null
                    ? '—'
                    : launchCenter.feature_flags_all_disabled
                      ? 'Yes'
                      : 'Partial'}
                </li>
                <li>
                  Ready for v1.1:{' '}
                  {launchCenter?.ready_for_v11 == null
                    ? '—'
                    : launchCenter.ready_for_v11
                      ? 'Yes'
                      : 'Not yet'}
                </li>
                {(launchCenter?.recent_feedback || []).slice(0, 4).map((f) => (
                  <li key={f.feedback_id}>
                    [{f.reaction}] {f.screen}
                    {f.comment ? ` — ${f.comment}` : ''}
                  </li>
                ))}
                {launchCenter && !(launchCenter.recent_feedback || []).length ? (
                  <li>No feedback yet — collect 👍/👎 on Ask, Workspace, Publications.</li>
                ) : null}
              </ul>
            </Glass>
          </div>
        </section>

        {/* Architecture Center — RC-01 */}
        <section className="space-y-3">
          <Kicker>Architecture Center · RC-01 · AGIB v1.0 GA</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            AGIB v1.0 is General Availability. Continuous quality gate — invariants, violations,
            layer dependencies, import graph, context propagation, lineage health, and architecture
            score. Architecture remains frozen; every merge must preserve v1.0 contracts.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <Stat
              label="Release"
              value={
                architectureCenter?.agib_general_availability ||
                architectureCenter?.agib_release_status === 'GENERAL_AVAILABILITY'
                  ? 'GA'
                  : architectureCenter?.release_candidate_ready
                    ? 'RC'
                    : '—'
              }
              status={architectureCenter?.status}
              hint="v1.0.0"
            />
            <Stat
              label="Score"
              value={
                architectureCenter?.architecture_score != null
                  ? `${architectureCenter.architecture_score}`
                  : '—'
              }
              hint={architectureCenter?.architecture_grade}
            />
            <Stat
              label="Invariants"
              value={
                architectureCenter?.invariant_total != null
                  ? `${architectureCenter.invariant_passed ?? 0}/${architectureCenter.invariant_total}`
                  : '—'
              }
            />
            <Stat label="Violations" value={architectureCenter?.violation_count ?? '—'} />
            <Stat
              label="Import graph"
              value={
                architectureCenter?.import_graph?.nodes != null
                  ? `${architectureCenter.import_graph.nodes}n/${architectureCenter.import_graph.edges ?? 0}e`
                  : '—'
              }
            />
            <Stat
              label="Contexts"
              value={
                architectureCenter?.context_propagation
                  ? Object.values(architectureCenter.context_propagation).filter(Boolean).length
                  : '—'
              }
              hint="Exec · Sec · Obs"
            />
            <Stat
              label="Frozen"
              value={architectureCenter?.architecture_frozen == null ? '—' : architectureCenter.architecture_frozen ? 'Yes' : 'No'}
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Invariants</p>
              <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
                {(architectureCenter?.invariants || []).slice(0, 10).map((inv) => (
                  <li key={inv.id}>
                    {inv.ok ? '✓' : '✗'} [{inv.group}] {inv.message}
                  </li>
                ))}
                {!architectureCenter ? <li>Architecture Center soft slice unavailable.</li> : null}
              </ul>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Violations</p>
              <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
                {(architectureCenter?.violations || []).slice(0, 8).map((v, i) => (
                  <li key={`${v.section || v.kind}-${i}`}>
                    [{v.section || v.kind}] {v.message || JSON.stringify(v)}
                  </li>
                ))}
                {architectureCenter && !(architectureCenter.violations || []).length ? (
                  <li>No violations — architecture principles preserved.</li>
                ) : null}
              </ul>
            </Glass>
          </div>
        </section>

        {/* Operations Center — PRP-03 */}
        <section className="space-y-3">
          <Kicker>Operations Center · PRP-03</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            End-to-end operability — live request rate, active traces, P95/P99 latency, error rate,
            queue/cache health, worker utilization, dependency status, and alert timeline.
            Observability explains behavior; it never changes it.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
            <Stat
              label="Req / min"
              value={operationsCenter?.live_request_rate ?? '—'}
              status={operationsCenter?.status || operationsCenter?.overall_health}
            />
            <Stat label="Active traces" value={operationsCenter?.active_traces ?? '—'} />
            <Stat
              label="P95"
              value={
                operationsCenter?.p95_latency_ms != null
                  ? `${operationsCenter.p95_latency_ms}ms`
                  : '—'
              }
            />
            <Stat
              label="P99"
              value={
                operationsCenter?.p99_latency_ms != null
                  ? `${operationsCenter.p99_latency_ms}ms`
                  : '—'
              }
            />
            <Stat
              label="Error rate"
              value={
                operationsCenter?.error_rate != null
                  ? `${Math.round(Number(operationsCenter.error_rate) * 100)}%`
                  : '—'
              }
            />
            <Stat
              label="Queue"
              value={operationsCenter?.queue_health?.depth ?? '—'}
              hint={operationsCenter?.queue_health?.status}
            />
            <Stat
              label="Cache hit"
              value={
                operationsCenter?.cache_health?.hit_rate != null
                  ? `${Math.round(Number(operationsCenter.cache_health.hit_rate) * 100)}%`
                  : '—'
              }
            />
            <Stat
              label="Workers"
              value={
                operationsCenter?.worker_utilization != null
                  ? `${Math.round(Number(operationsCenter.worker_utilization) * 100)}%`
                  : '—'
              }
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Alert timeline</p>
              <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
                {(operationsCenter?.alert_timeline || []).slice(0, 6).map((a) => (
                  <li key={a.alert_id}>
                    [{a.severity}] {a.rule}: {a.message}
                  </li>
                ))}
                {!operationsCenter ? <li>Operations Center soft slice unavailable.</li> : null}
                {operationsCenter && !(operationsCenter.alert_timeline || []).length ? (
                  <li>No alerts — platform metrics within thresholds.</li>
                ) : null}
              </ul>
            </Glass>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Service topology</p>
              <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
                {(operationsCenter?.service_topology?.nodes || []).slice(0, 10).map((n) => (
                  <li key={n.id}>
                    {n.id} · {n.status || 'unknown'} · {n.kind || 'service'}
                  </li>
                ))}
                {operationsCenter && !(operationsCenter.service_topology?.nodes || []).length ? (
                  <li>Service map empty.</li>
                ) : null}
              </ul>
            </Glass>
          </div>
        </section>

        {/* Security Center — PRP-02 */}
        <section className="space-y-3">
          <Kicker>Security Center · PRP-02</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Enterprise controls — active sessions, login failures, API key usage, permission
            changes, audit volume, tenants, and revoked tokens. Security decides who; intelligence
            decides what. Never enters the intelligence layer.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
            <Stat
              label="Sessions"
              value={securityCenter?.active_sessions ?? '—'}
              status={securityCenter?.status}
            />
            <Stat label="Login fails" value={securityCenter?.login_failures ?? '—'} />
            <Stat label="API key use" value={securityCenter?.api_key_usage ?? '—'} />
            <Stat label="Perm changes" value={securityCenter?.permission_changes ?? '—'} />
            <Stat label="Audit volume" value={securityCenter?.audit_volume ?? '—'} />
            <Stat label="Tenants" value={securityCenter?.tenant_count ?? '—'} />
            <Stat label="Revoked" value={securityCenter?.revoked_tokens ?? '—'} />
            <Stat
              label="Auth latency"
              value={
                securityCenter?.authentication_latency_ms != null
                  ? `${securityCenter.authentication_latency_ms}ms`
                  : '—'
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Recent audit</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(securityCenter?.recent_audit || []).slice(0, 6).map((a) => (
                <li key={a.event_id}>
                  [{a.action}] {a.resource}
                  {a.resource_id ? `:${a.resource_id}` : ''} → {a.outcome}
                  {a.correlation_id ? ` · ${a.correlation_id}` : ''}
                </li>
              ))}
              {!securityCenter ? <li>Security Center soft slice unavailable.</li> : null}
              {securityCenter && !(securityCenter.recent_audit || []).length ? (
                <li>Login or run a gated Ask/publication to populate audit.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Performance Center — PRP-01 */}
        <section className="space-y-3">
          <Kicker>Performance Center · PRP-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Production readiness — cache hit rate, P95 latency, slow queries, queue depth, and active
            workers. Targets: Ask AGI &lt; 2s cached, workspace &lt; 1s, async publications. No new
            intelligence engines; AGIB v1.0 architecture is frozen.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Cache hit rate"
              value={
                performanceCenter?.cache_hit_rate != null
                  ? `${Math.round(Number(performanceCenter.cache_hit_rate) * 100)}%`
                  : '—'
              }
              status={performanceCenter?.status}
            />
            <Stat
              label="P95 latency"
              value={
                performanceCenter?.p95_latency_seconds != null
                  ? `${performanceCenter.p95_latency_seconds}s`
                  : '—'
              }
            />
            <Stat
              label="Slow queries"
              value={(performanceCenter?.slow_queries || []).length}
            />
            <Stat label="Queue depth" value={performanceCenter?.queue_depth ?? '—'} />
            <Stat label="Active workers" value={performanceCenter?.active_workers ?? '—'} />
            <Stat
              label="Jobs done"
              value={performanceCenter?.jobs_completed ?? '—'}
              hint={
                performanceCenter?.redis_enabled
                  ? 'Redis connected'
                  : performanceCenter
                    ? 'Memory cache'
                    : undefined
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Slow queries</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(performanceCenter?.slow_queries || []).slice(0, 6).map((q, i) => (
                <li key={`${q.operation}-${q.ts || i}`}>
                  [{q.operation}] {q.seconds}s{q.cached ? ' (cached)' : ''}
                </li>
              ))}
              {!performanceCenter ? <li>Performance Center soft slice unavailable.</li> : null}
              {performanceCenter && !(performanceCenter.slow_queries || []).length ? (
                <li>No slow queries recorded yet — run Ask or workspace loads to sample latency.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Platform Operations Center — MPC-01 */}
        <section className="space-y-3">
          <Kicker>Platform Operations · MPC-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Multi-portfolio tenancy — active workspaces, portfolio/client counts, publication queue,
            permission changes, workspace health, distribution status, and audit events. Intelligence
            stays global; mandates and permissions are local.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Workspaces"
              value={platformOps?.active_workspaces ?? '—'}
              status={platformOps?.status}
            />
            <Stat label="Portfolios" value={platformOps?.portfolio_count ?? '—'} />
            <Stat label="Clients" value={platformOps?.client_count ?? '—'} />
            <Stat label="Pub queue" value={platformOps?.publication_queue ?? '—'} />
            <Stat label="Perm changes" value={platformOps?.permission_changes ?? '—'} />
            <Stat
              label="Workspace health"
              value={platformOps?.workspace_health ?? '—'}
              hint={
                platformOps?.audit_events != null
                  ? `${platformOps.audit_events} audit events`
                  : undefined
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Recent audit</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(platformOps?.recent_audit || []).slice(0, 6).map((a) => (
                <li key={a.event_id}>
                  [{a.kind}] {a.detail}
                </li>
              ))}
              {!platformOps ? <li>Platform Operations soft slice unavailable.</li> : null}
              {platformOps && !(platformOps.recent_audit || []).length ? (
                <li>Resolve a workspace or grant permissions to populate audit.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Publication Center — PUB-01 */}
        <section className="space-y-3">
          <Kicker>Publication Center · PUB-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Publishing &amp; distribution — success rate, generation latency, template coverage,
            distribution status, failed renders, version integrity, and missing lineage. Compose
            only; manifests are the audit record.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Success rate"
              value={
                publicationCenter?.publication_success_rate != null
                  ? `${Math.round(Number(publicationCenter.publication_success_rate) * 100)}%`
                  : '—'
              }
              status={publicationCenter?.status}
            />
            <Stat
              label="Gen. latency"
              value={
                publicationCenter?.generation_latency != null
                  ? `${Number(publicationCenter.generation_latency).toFixed(0)}ms`
                  : '—'
              }
            />
            <Stat
              label="Template coverage"
              value={publicationCenter?.template_coverage ?? '—'}
              hint={
                publicationCenter?.types_generated != null
                  ? `${publicationCenter.types_generated} generated`
                  : undefined
              }
            />
            <Stat
              label="Distributed"
              value={publicationCenter?.distribution_status?.distributed_count ?? '—'}
            />
            <Stat label="Failed renders" value={publicationCenter?.failed_renders ?? '—'} />
            <Stat
              label="Version integrity"
              value={
                publicationCenter?.version_integrity == null
                  ? '—'
                  : publicationCenter.version_integrity
                    ? 'OK'
                    : 'Gaps'
              }
              hint={
                publicationCenter?.missing_lineage != null
                  ? `${publicationCenter.missing_lineage} missing lineage`
                  : undefined
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Publication diagnostics</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {!publicationCenter ? <li>Publication Center soft slice unavailable.</li> : null}
              {publicationCenter ? (
                <li>
                  {publicationCenter.product || 'PUB-01'} · compose only ·{' '}
                  {(publicationCenter.renderers || []).join(', ') || 'markdown/html/pdf/json'}
                </li>
              ) : null}
              {publicationCenter && (publicationCenter.publications_cached || 0) === 0 ? (
                <li>Generate a publication to populate the center.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Relationship Center — CCI-01 */}
        <section className="space-y-3">
          <Kicker>Relationship Center · CCI-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Cross-company relationship intelligence over KG-01 — coverage, missing links, strongest
            hubs, propagation latency, graph integrity (delegated), and cluster health. CCI reasons;
            KG owns the graph.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Coverage"
              value={relationshipCenter?.relationship_coverage ?? '—'}
              status={relationshipCenter?.status}
            />
            <Stat label="Missing links" value={relationshipCenter?.missing_links ?? '—'} />
            <Stat
              label="Strongest hubs"
              value={(relationshipCenter?.strongest_hubs || []).length || '—'}
              hint={
                (relationshipCenter?.strongest_hubs || [])[0]?.entity
                  ? String((relationshipCenter.strongest_hubs || [])[0].entity)
                  : undefined
              }
            />
            <Stat
              label="Prop. latency"
              value={
                relationshipCenter?.propagation_latency != null
                  ? `${Number(relationshipCenter.propagation_latency).toFixed(0)}ms`
                  : '—'
              }
            />
            <Stat
              label="Graph integrity"
              value={relationshipCenter?.graph_integrity || 'KG-01'}
            />
            <Stat
              label="Cluster health"
              value={relationshipCenter?.cluster_health ?? '—'}
              hint={
                relationshipCenter?.provider_count != null
                  ? `${relationshipCenter.provider_count} providers`
                  : undefined
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Hubs & providers</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(relationshipCenter?.strongest_hubs || []).slice(0, 6).map((h) => (
                <li key={h.entity}>
                  {h.entity} · degree {h.degree}
                </li>
              ))}
              {!relationshipCenter ? <li>Relationship Center soft slice unavailable.</li> : null}
              {relationshipCenter && !(relationshipCenter.strongest_hubs || []).length ? (
                <li>Query company or macro relationships to populate hubs.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Workspace Health — RW-01 */}
        <section className="space-y-3">
          <Kicker>Workspace Health · RW-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Institutional Research Workspace integrity — missing links, missing evidence, broken
            lineage, timeline gaps, orphaned notes, and navigation integrity. Presentation layer
            only; analyst notes never mutate system intelligence.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Missing links"
              value={workspaceHealth?.objects_with_missing_links ?? '—'}
              status={workspaceHealth?.status}
            />
            <Stat label="Missing evidence" value={workspaceHealth?.missing_evidence ?? '—'} />
            <Stat label="Broken lineage" value={workspaceHealth?.broken_lineage ?? '—'} />
            <Stat label="Timeline gaps" value={workspaceHealth?.timeline_gaps ?? '—'} />
            <Stat label="Orphaned notes" value={workspaceHealth?.orphaned_notes ?? '—'} />
            <Stat
              label="Nav integrity"
              value={
                workspaceHealth?.navigation_integrity == null
                  ? '—'
                  : workspaceHealth.navigation_integrity
                    ? 'OK'
                    : 'Check'
              }
              hint={
                workspaceHealth?.workspaces_cached != null
                  ? `${workspaceHealth.workspaces_cached} cached`
                  : undefined
              }
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Workspace diagnostics</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {!workspaceHealth ? <li>Workspace Health soft slice unavailable.</li> : null}
              {workspaceHealth ? (
                <li>
                  Status {workspaceHealth.status || '—'} · {workspaceHealth.product || 'RW-01'} ·
                  presentation only
                </li>
              ) : null}
              {workspaceHealth && (workspaceHealth.objects_with_missing_links || 0) === 0 ? (
                <li>Open a company or portfolio workspace to populate health signals.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Committee Center — ICE-01 */}
        <section className="space-y-3">
          <Kicker>Committee Center · ICE-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Investment committee governance — pending reviews, policy escalations, deferred
            decisions, upcoming meetings, and open action items. Advisory only; does not mutate
            upstream risk, policy, or company decisions.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <Stat
              label="Pending reviews"
              value={committeeCenter?.pending_reviews ?? '—'}
              status={committeeCenter?.status}
            />
            <Stat
              label="Policy escalations"
              value={committeeCenter?.policy_escalations ?? '—'}
            />
            <Stat
              label="Deferred decisions"
              value={committeeCenter?.deferred_decisions ?? '—'}
            />
            <Stat
              label="Upcoming meetings"
              value={(committeeCenter?.upcoming_meetings || []).length || '—'}
            />
            <Stat
              label="Open action items"
              value={committeeCenter?.open_action_items ?? '—'}
            />
            <Stat label="Overdue reviews" value={committeeCenter?.overdue_reviews ?? '—'} />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">
              Latest {committeeCenter?.latest_resolution?.status || '—'} ·{' '}
              {committeeCenter?.latest_resolution?.decision_recommendation || 'no resolution'}
            </p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(committeeCenter?.upcoming_meetings || []).slice(0, 6).map((m) => (
                <li key={`um-${m}`}>Meeting / follow-up: {m}</li>
              ))}
              {(committeeCenter?.latest_resolution?.required_actions || [])
                .slice(0, 4)
                .map((a) => (
                  <li key={`ca-${a.action_id || a.title}`}>Action: {a.title || a.detail}</li>
                ))}
              {!committeeCenter ? <li>Committee Center soft slice unavailable.</li> : null}
              {committeeCenter &&
              !(committeeCenter.upcoming_meetings || []).length &&
              !(committeeCenter.latest_resolution?.required_actions || []).length ? (
                <li>Run a committee review to populate the Committee Center.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Portfolio Command Center — CIO-01 */}
        <section className="space-y-3">
          <Kicker>Portfolio Command Center · CIO-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Deterministic portfolio decisions — allocation drift, exposure drift, critical holdings,
            and upcoming reviews. Company decisions remain immutable references.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat
              label="Decision"
              value={portfolioCommand?.portfolio_decision?.recommendation || '—'}
              status={portfolioCommand?.status}
              hint={
                portfolioCommand?.portfolio_decision?.confidence != null
                  ? `Confidence ${portfolioCommand.portfolio_decision.confidence}`
                  : 'No decision cached'
              }
            />
            <Stat label="Allocation drift" value={portfolioCommand?.allocation_drift ?? '—'} />
            <Stat label="Exposure drift" value={portfolioCommand?.exposure_drift ?? '—'} />
            <Stat
              label="Critical holdings"
              value={(portfolioCommand?.critical_holdings || []).length || '—'}
            />
            <Stat
              label="Upcoming reviews"
              value={(portfolioCommand?.upcoming_reviews || []).length || '—'}
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Critical holdings / reviews</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(portfolioCommand?.critical_holdings || []).slice(0, 6).map((t) => (
                <li key={`ch-${t}`}>Holding: {t}</li>
              ))}
              {(portfolioCommand?.upcoming_reviews || []).slice(0, 6).map((t) => (
                <li key={`ur-${t}`}>Review: {t}</li>
              ))}
              {!portfolioCommand ? <li>Portfolio Command Center soft slice unavailable.</li> : null}
              {portfolioCommand &&
              !(portfolioCommand.critical_holdings || []).length &&
              !(portfolioCommand.upcoming_reviews || []).length ? (
                <li>Run a portfolio decision to populate the command center.</li>
              ) : null}
            </ul>
          </Glass>
        </section>

        {/* Portfolio Knowledge Graph — PKG-01 / Phase 4.1 */}
        <section className="space-y-3">
          <Kicker>Portfolio Knowledge Graph · PKG-01</Kicker>
          <p className="text-sm text-[var(--io-muted)] max-w-3xl">
            Phase 4.1 — Portfolio → Companies → Relationships. Soft board for Investment Office
            portfolio intelligence (distinct from Portfolio Office holdings state).
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat
              label="Status"
              value={portfolioKnowledge?.status || '—'}
              status={portfolioKnowledge?.status}
            />
            <Stat label="Entities" value={portfolioKnowledge?.entity_count ?? '—'} />
            <Stat label="Relationships" value={portfolioKnowledge?.relationship_count ?? '—'} />
            <Stat label="Holdings" value={portfolioKnowledge?.holding_count ?? '—'} />
            <Stat
              label="Avg ρ"
              value={
                portfolioKnowledge?.average_correlation != null
                  ? Number(portfolioKnowledge.average_correlation).toFixed(2)
                  : '—'
              }
              hint={portfolioKnowledge?.portfolio_name || 'No portfolio cached'}
            />
          </div>
          <Glass>
            <p className="text-[11px] uppercase text-[var(--io-caption)]">Sector exposures</p>
            <ul className="mt-2 space-y-1 text-xs max-h-36 overflow-auto text-[var(--io-ink-soft)]">
              {(portfolioKnowledge?.sector_exposures || []).slice(0, 8).map((e) => (
                <li key={e.name}>
                  {e.name}: {e.weight != null ? `${(Number(e.weight) * 100).toFixed(0)}%` : '—'}
                </li>
              ))}
              {!portfolioKnowledge ? <li>Portfolio Knowledge Graph soft slice unavailable.</li> : null}
              {portfolioKnowledge && !(portfolioKnowledge.sector_exposures || []).length ? (
                <li>Build a portfolio graph to populate exposures.</li>              ) : null}
            </ul>
          </Glass>
        </section>

        {/* SECTION 7 + 8 + 9 */}
        <section className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-3">
            <Kicker>Section 7 · Company Monitor</Kicker>
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Monitored" value={monitor.companies_monitored} />
              <Stat label="Critical" value={monitor.critical_alerts} status="Critical" />
              <Stat label="High" value={monitor.high_alerts} status="Warning" />
              <Stat label="Need Review" value={monitor.companies_needing_review} />
            </div>
            <Glass>
              <p className="text-[11px] uppercase text-[var(--io-caption)]">Latest changes</p>
              <ul className="mt-2 space-y-1 text-xs max-h-40 overflow-auto text-[var(--io-ink-soft)]">
                {(monitor.latest_company_changes || []).slice(0, 8).map((c, idx) => (
                  <li key={`${c.ticker}-${idx}`}>
                    {c.ticker}: {c.detail || c.change_type} ({c.significance})
                  </li>
                ))}
              </ul>
            </Glass>
          </div>
          <div className="space-y-3">
            <Kicker>Section 8 · Research Pipeline</Kicker>
            <Stat label="Queue" value={(pipeline.research_queue || []).length} />
            <Glass>
              <ul className="space-y-1 text-sm max-h-56 overflow-auto">
                {(pipeline.research_queue || []).slice(0, 8).map((t) => (
                  <li key={t.id || t.title}>
                    <span className="font-medium text-[var(--io-ink)]">{t.title}</span>
                    <p className="text-[11px] text-[var(--io-muted)]">
                      {t.priority} · {t.suggested_owner}
                    </p>
                  </li>
                ))}
              </ul>
            </Glass>
          </div>
          <div className="space-y-3">
            <Kicker>Section 9 · Predictions</Kicker>
            <Stat label="Due" value={(preds.predictions_due || []).length} />
            <Stat label="HV Reviews" value={(preds.house_view_reviews || []).length} />
            <Stat label="Accuracy" value={preds.prediction_accuracy ?? '—'} />
          </div>
        </section>

        {/* SECTION 10–13 */}
        <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
          <Glass>
            <Kicker>Section 10 · Data Quality</Kicker>
            <ul className="mt-3 space-y-1 text-sm text-[var(--io-ink-soft)]">
              <li>Research: {dq.research_grade}</li>
              <li>Knowledge: {dq.knowledge_grade}</li>
              <li>Market data: {dq.market_data_grade}</li>
              <li>Academy: {dq.academy_grade}</li>
              <li>Sector: {String(dq.sector_intelligence_grade)}</li>
            </ul>
          </Glass>
          <Glass>
            <Kicker>Section 11 · Company Analysis</Kicker>
            <ul className="mt-3 space-y-1 text-sm text-[var(--io-ink-soft)]">
              <li>Analysed: {ca.companies_analysed ?? '—'}</li>
              <li>BQ complete: {ca.business_quality_complete ?? '—'}</li>
              <li>Reports: {(ca.latest_reports || []).length}</li>
            </ul>
          </Glass>
          <Glass>
            <Kicker>Section 12 · Academy</Kicker>
            <ul className="mt-3 space-y-1 text-sm text-[var(--io-ink-soft)]">
              <li>Books: {academy.books}</li>
              <li>Concepts: {academy.concepts}</li>
              <li>Frameworks: {academy.frameworks}</li>
              <li>Formulas: {academy.formulas}</li>
              <li>Graph edges: {academy.graph_relationships}</li>
            </ul>
          </Glass>
          <Glass>
            <Kicker>Section 13 · CID</Kicker>
            <ul className="mt-3 space-y-1 text-sm text-[var(--io-ink-soft)]">
              <li>Enabled: {String(cid.enabled)}</li>
              <li>Coverage: {cid.coverage}</li>
              <li>Dossiers: {cid.company_dossiers}</li>
            </ul>
          </Glass>
        </section>

        {/* SECTION 14 + 15 */}
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <Kicker>Section 14 · System Health (IOC)</Kicker>
            <Glass>
              <ul className="grid grid-cols-2 gap-2 text-sm">
                {[
                  ['FastAPI', sys.fastapi],
                  ['Frontend', sys.frontend],
                  ['Backend', sys.backend],
                  ['Database', sys.database],
                  ['Auth', sys.authentication],
                  ['Email', sys.email],
                  ['Scheduler', sys.scheduler],
                  ['Cache', sys.cache],
                ].map(([label, value]) => (
                  <li key={label} className="flex justify-between border-b border-[var(--io-border)] pb-1">
                    <span className="text-[var(--io-muted)]">{label}</span>
                    <span className={statusColour(value)}>{value || '—'}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[11px] text-[var(--io-caption)]">{sys.note}</p>
            </Glass>
          </div>
          <div className="space-y-3">
            <Kicker>Section 15 · Live Event Stream</Kicker>
            <Glass>
              <ul className="space-y-2 max-h-72 overflow-auto text-sm">
                {events.map((e, idx) => (
                  <li key={`${e.at}-${idx}`} className="border-b border-[var(--io-border)] pb-2">
                    <p className="text-[10px] font-bold uppercase text-[var(--io-gold)]">
                      {(e.at || '').slice(11, 19) || '—'} · {e.type}
                    </p>
                    <p className="text-[var(--io-ink-soft)]">{e.message}</p>
                  </li>
                ))}
                {!events.length ? <li className="text-[var(--io-muted)]">No events yet — run CMS / learning cycles.</li> : null}
              </ul>
            </Glass>
          </div>
        </section>

        {/* SECTION 16 + 17 */}
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <Kicker>Section 16 · Executive Copilot</Kicker>
            <Glass>
              <ul className="space-y-3">
                {(copilot.prompts || []).map((p) => (
                  <li key={p}>
                    <p className="text-xs font-semibold text-[var(--io-ink)]">{p}</p>
                    <p className="mt-1 text-[11px] text-[var(--io-muted)]">{copilot.answers?.[p]}</p>
                  </li>
                ))}
              </ul>
            </Glass>
          </div>
          <div className="space-y-3">
            <Kicker>Section 17 · Architecture Map</Kicker>
            <Glass>
              <div className="flex flex-wrap gap-2">
                {(arch.nodes || []).map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => setSelectedNode(n)}
                    className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${
                      n.colour === 'Green'
                        ? 'border-emerald-500/40 text-emerald-300'
                        : n.colour === 'Red'
                          ? 'border-rose-500/40 text-rose-300'
                          : 'border-amber-500/40 text-amber-200'
                    }`}
                  >
                    {n.label}
                  </button>
                ))}
              </div>
              {selectedNode ? (
                <pre className="mt-3 max-h-40 overflow-auto text-[11px] text-[var(--io-ink-soft)]">
                  {JSON.stringify(selectedNode, null, 2)}
                </pre>
              ) : (
                <p className="mt-3 text-[11px] text-[var(--io-caption)]">Click a node for diagnostics.</p>
              )}
            </Glass>
          </div>
        </section>

        <section className="space-y-3">
          <Kicker>Agents · Working status</Kicker>
          <Glass className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm text-[var(--io-ink)]">
                Inventory of CIO desk agents, IAF specialists, FAA / LIDI collectors, offices, and learning modules.
              </p>
              <p className="mt-1 text-[11px] text-[var(--io-caption)]">
                Shows whether each agent is working, soft-wire, off, or orphan — plus data sources.
              </p>
            </div>
            <Button onClick={() => setAgentMapOpen(true)} className="bg-[var(--io-gold)] text-black hover:bg-[var(--io-gold)]/90">
              <Bot className="h-4 w-4 mr-2" />
              Open Agent Map
            </Button>
          </Glass>
        </section>

        {/* SECTION 18–20 */}
        <section className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-3">
            <Kicker>Section 18 · Alerts Centre</Kicker>
            <Glass>
              <ul className="space-y-2 max-h-72 overflow-auto text-sm">
                {alerts.slice(0, 20).map((a) => (
                  <li key={a.id} className="border-b border-[var(--io-border)] pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-[10px] font-bold uppercase text-[var(--io-gold)]">{a.category}</p>
                        <p className="text-[var(--io-ink-soft)]">
                          {a.ticker ? `${a.ticker}: ` : ''}
                          {a.message}
                        </p>
                      </div>
                      {!a.acknowledged ? (
                        <button
                          type="button"
                          onClick={() => onAck(a.id)}
                          className="shrink-0 text-[10px] font-bold uppercase text-[var(--io-gold)]"
                        >
                          Ack
                        </button>
                      ) : (
                        <span className="text-[10px] text-[var(--io-caption)]">ACK</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </Glass>
          </div>
          <div className="space-y-3">
            <Kicker>Section 19 · Deployment</Kicker>
            <Glass className="text-sm text-[var(--io-ink-soft)] space-y-1">
              <p>Version: {deploy.current_version}</p>
              <p>Commit: {deploy.git_commit || '—'}</p>
              <p>Branch: {deploy.current_branch || '—'}</p>
              <p>Environment: {deploy.environment}</p>
              <p className="text-[11px] text-[var(--io-caption)]">{deploy.note}</p>
            </Glass>
          </div>
          <div className="space-y-3">
            <Kicker>Section 20 · Performance</Kicker>
            <Glass className="text-sm text-[var(--io-ink-soft)] space-y-1">
              <p>Daily learning: {perf.daily_learning ?? '—'}</p>
              <p>Daily research: {perf.daily_research ?? '—'}</p>
              <p>Ask AGI avg: {perf.average_ask_agi_response ?? '—'}</p>
              <p className="text-[11px] text-[var(--io-caption)]">{perf.note}</p>
            </Glass>
          </div>
        </section>
      </div>

      <AgentMapPanel open={agentMapOpen} onClose={() => setAgentMapOpen(false)} />
    </div>
  );
}
