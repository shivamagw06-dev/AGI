import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  Bookmark,
  BookOpen,
  Building2,
  FileSpreadsheet,
  FileText,
  Home,
  Layers,
  LineChart,
  Moon,
  Search,
  Settings,
  Share2,
  Shield,
  Sparkles,
  Star,
  TrendingUp,
} from 'lucide-react';
import { Line, LineChart as RLineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Sparkline from '@/office/Sparkline';
import { mapSearchPack } from '@/components/AskAgi/adapters/mapSearchPack';
import '@/components/AskAgi/researchWorkspace.css';

const NAV = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/ask', label: 'Ask AGI', icon: Sparkles },
  { to: '/research', label: 'Research', icon: BookOpen },
  { to: '/markets', label: 'Markets', icon: LineChart },
  { to: '/company-updates', label: 'Companies', icon: Building2 },
  { to: '/sectors/it-services', label: 'Sectors', icon: Layers },
  { to: '/themes', label: 'Themes', icon: Activity },
  { to: '/portfolio', label: 'Portfolio', icon: TrendingUp },
  { to: '/workspace', label: 'Watchlists', icon: Star },
  { to: '/admin/academy', label: 'Academy', icon: BookOpen },
  { to: '/admin/knowledge', label: 'Knowledge', icon: Layers, admin: true },
  { to: '/admin/mission-control', label: 'Mission Control', icon: Shield, admin: true },
  { to: '/admin/system', label: 'System Health', icon: Activity, admin: true },
  { to: '/admin', label: 'Settings', icon: Settings, admin: true },
];

function Section({ id, kicker, title, children, className = '' }) {
  return (
    <section id={id} className={`rw-card scroll-mt-24 ${className}`}>
      {kicker ? <p className="rw-kicker">{kicker}</p> : null}
      {title ? <h2 className="rw-title">{title}</h2> : null}
      {children}
    </section>
  );
}

const DEFAULT_OWNER_LABELS = {
  cio: 'Chief Investment Officer',
  committee: 'Investment Committee',
  business: 'Business Analyst',
  financial: 'Financial Analyst',
  valuation: 'Valuation Analyst',
  market: 'Market Analyst',
  sector: 'Sector Analyst',
  macro: 'Macro Analyst',
  risk: 'Risk Analyst',
  management: 'Management Analyst',
  ownership: 'Ownership Analyst',
  recommendation_gate: 'Recommendation Gate',
};

function ownerKicker(vm, sectionKey, fallback) {
  if (!vm?.iafEnabled) return fallback;
  const owner = vm.sectionOwners?.[sectionKey];
  if (!owner) return fallback;
  return vm.publicOwnerLabels?.[owner] || DEFAULT_OWNER_LABELS[owner] || fallback;
}

function pctLabel(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  const pct = n <= 1 ? n * 100 : n;
  return `${Math.round(pct)}%`;
}

function fmtNum(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  if (Math.abs(n) >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return String(Math.round(n * 100) / 100);
}

function Donut({ value = 72 }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const r = 54;
  const c = 2 * Math.PI * r;
  const offset = c - (v / 100) * c;
  return (
    <div className="relative mx-auto h-[140px] w-[140px]">
      <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
        <circle cx="70" cy="70" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="12" />
        <circle
          cx="70"
          cy="70"
          r={r}
          fill="none"
          stroke="var(--rw-pos)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-3xl font-bold tabular-nums">{v}%</p>
        <p className="text-[10px] uppercase tracking-wide text-[var(--rw-caption)]">Overall</p>
      </div>
    </div>
  );
}

export default function ResearchWorkspace({
  pack,
  loading = false,
  error = null,
  question = '',
  onAsk,
  onSave,
  savedFlash = false,
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [draft, setDraft] = useState(question || '');
  const vm = useMemo(() => mapSearchPack(pack), [pack]);

  useEffect(() => {
    setDraft(question || '');
  }, [question]);

  const submit = (q) => {
    const next = String(q || draft || '').trim();
    if (!next) return;
    onAsk?.(next);
  };

  const isActive = (to) => {
    if (to === '/ask') return location.pathname === '/ask';
    if (to === '/') return location.pathname === '/';
    return location.pathname === to || location.pathname.startsWith(`${to}/`);
  };

  const exportJson = () => {
    if (!pack) return;
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agi-research-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const chartData = useMemo(() => {
    const points = vm?.valuationChart?.points;
    if (!Array.isArray(points)) return [];
    return points
      .map((p, i) => ({
        name: p.label || p.date || String(i + 1),
        value: Number(p.value),
      }))
      .filter((p) => Number.isFinite(p.value));
  }, [vm]);

  return (
    <div className="agi-research">
      <div className="rw-shell">
        <aside className="rw-sidebar">
          <div className="rw-brand">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--rw-blue-soft)] text-[var(--rw-blue)] font-bold">
              AGI
            </div>
            <div>
              <strong>AGI</strong>
              <span>Intelligence Platform</span>
            </div>
          </div>

          <div>
            <p className="rw-nav-label">Intelligence Platform</p>
            <nav className="rw-nav space-y-0.5">
              {NAV.filter((n) => !n.admin).map((item) => {
                const Icon = item.icon;
                return (
                  <Link key={item.to} to={item.to} className={isActive(item.to) ? 'active' : ''}>
                    <Icon size={15} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div>
            <p className="rw-nav-label">Admin</p>
            <nav className="rw-nav space-y-0.5">
              {NAV.filter((n) => n.admin).map((item) => {
                const Icon = item.icon;
                return (
                  <Link key={item.to} to={item.to}>
                    <Icon size={15} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="rw-side-foot">
            <p>AGI Platform v2.0.0</p>
            <p className="ok mt-1">● All Systems Operational</p>
          </div>
        </aside>

        <div className="rw-main">
          <header className="rw-topbar">
            <div className="logo">AGI | ASK AGI</div>
            <form
              className="rw-search"
              onSubmit={(e) => {
                e.preventDefault();
                submit(draft);
              }}
            >
              <Search size={16} className="text-[var(--rw-caption)]" />
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Ask anything about markets, companies, sectors, macro..."
              />
            </form>
            <div className="rw-actions">
              <button type="button" className="rw-iconbtn" onClick={onSave} title="Save">
                <Bookmark size={15} />
                <span className="label">{savedFlash ? 'Saved' : 'Save'}</span>
              </button>
              <button type="button" className="rw-iconbtn" onClick={onSave} title="Bookmark">
                <Star size={15} />
                <span className="label">Bookmark</span>
              </button>
              <button type="button" className="rw-iconbtn" onClick={exportJson} title="Export PDF">
                <FileText size={15} />
                <span className="label">PDF</span>
              </button>
              <button type="button" className="rw-iconbtn" onClick={exportJson} title="Export Excel">
                <FileSpreadsheet size={15} />
                <span className="label">Excel</span>
              </button>
              <button
                type="button"
                className="rw-iconbtn"
                title="Share"
                onClick={() => navigator.clipboard?.writeText(window.location.href)}
              >
                <Share2 size={15} />
                <span className="label">Share</span>
              </button>
              <button type="button" className="rw-iconbtn" title="Dark mode">
                <Moon size={15} />
              </button>
              <button type="button" className="rw-iconbtn rw-avatar" title="Profile">
                AD
              </button>
            </div>
          </header>

          <div className="rw-content">
            {!question && !loading && (
              <Section kicker="Ask AGI" title="Institutional Investment Research Workspace">
                <p className="rw-body">
                  Ask any institutional question. Every answer opens as a research note — executive
                  summary, house view, financial intelligence, valuation, risks and catalysts —
                  constructed from AGI&apos;s validated intelligence stack.
                </p>
                <div className="rw-explore mt-4">
                  {[
                    'How is the Indian IT Services sector doing?',
                    'Should I invest in HDFC Bank?',
                    'What changed in Indian banks this quarter?',
                    'Is Nifty IT expensive versus history?',
                  ].map((q) => (
                    <button key={q} type="button" onClick={() => submit(q)}>
                      {q}
                    </button>
                  ))}
                </div>
              </Section>
            )}

            {loading && (
              <div className="rw-loading" aria-busy="true">
                <div className="rw-skel h-28" />
                <div className="rw-skel h-40" />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="rw-skel" />
                  <div className="rw-skel" />
                  <div className="rw-skel" />
                  <div className="rw-skel" />
                </div>
              </div>
            )}

            {error && !loading && (
              <Section kicker="Desk status" title="Temporarily unavailable">
                <p className="rw-body">
                  The research desk could not complete this briefing. Your question was preserved —
                  try again in a moment.
                </p>
              </Section>
            )}

            {vm && !loading && (
              <>
                <div className="rw-qhead">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h1>{vm.question}</h1>
                    <button type="button" className="rw-iconbtn" onClick={onSave}>
                      <Star size={14} /> Follow
                    </button>
                  </div>
                  <div className="rw-chips">
                    <span className="rw-chip blue">{vm.intent}</span>
                    <span className="rw-chip blue">{vm.category}</span>
                    {vm.ticker ? <span className="rw-chip muted">{vm.ticker}</span> : null}
                    {vm.acEnabled ? <span className="rw-chip muted">Institutional Brief</span> : null}
                    {vm.reasoningEnabled ? (
                      <span className="rw-chip muted">
                        {vm.reasoningSource?.includes('ic_case')
                          ? 'IC Reasoning'
                          : vm.contradictionEnabled
                            ? 'Contradiction Desk'
                            : 'Institutional Reasoning'}
                      </span>
                    ) : null}
                    {vm.booksEnabled ? <span className="rw-chip muted">Academy Books</span> : null}
                    {vm.editorialEnabled ? <span className="rw-chip muted">Gemini Editorial</span> : null}
                    {vm.iafEnabled ? <span className="rw-chip muted">Analyst Desk</span> : null}
                    {vm.irwEnabled ? <span className="rw-chip muted">Research Note</span> : null}
                    {vm.ideEnabled ? <span className="rw-chip muted">Decision Stack</span> : null}
                  </div>
                  <p className="rw-meta">
                    Last research refresh: {vm.freshness}
                    {vm.ticker ? ` · Focus: ${vm.ticker}` : ''}
                  </p>
                </div>

                <div className="rw-grid-2">
                  <Section
                    id="executive"
                    kicker={ownerKicker(vm, 'executive_summary', 'Section 1')}
                    title={vm.editorialEnabled ? 'Plain-English Summary' : 'Executive Summary'}
                  >
                    <p className="rw-body whitespace-pre-line text-[17px] leading-7">
                      {vm.executive ||
                        vm.institutionalAnswer?.reason ||
                        'Institutional summary assembling…'}
                    </p>
                    {vm.reasoningOwnsExecutive ? (
                      <p className="rw-mini mt-3">
                        AGIB reasoning owns this summary
                        {vm.reasoningFamily ? ` · ${vm.reasoningFamily}` : ''}
                        {vm.reasoningMode ? ` · ${vm.reasoningMode}` : ''}
                        {vm.noveltyBand ? ` · novelty ${vm.noveltyBand}` : ''}
                        {vm.ecrScore != null ? ` · ECR ${vm.ecrScore}` : ''}
                        {' · Not investment advice'}
                      </p>
                    ) : null}
                    {vm.bookFrameworks?.length ? (
                      <p className="rw-mini mt-2">
                        Academy framework lens: {vm.bookFrameworks.slice(0, 4).join(' · ')}
                      </p>
                    ) : null}
                    {vm.editorialEnabled ? (
                      <p className="rw-mini mt-3">
                        Editorial rewrite of AGIB intelligence · Not investment advice
                        {vm.editorialFallback ? ' · template fallback' : ''}
                      </p>
                    ) : null}
                  </Section>
                  <Section
                    id="view"
                    kicker={ownerKicker(vm, 'institutional_view', 'Section 2')}
                    title="Institutional View"
                  >
                    <div className="grid grid-cols-2 gap-3">
                      {vm.institutionalAnswer?.recommendation ? (
                        <div className="col-span-2">
                          <p className="rw-mini">AGIB Assessment</p>
                          <p className={`rw-view-value tone-${vm.stanceTone}`}>
                            {vm.institutionalAnswer.recommendation}
                            {vm.institutionalAnswer.conviction
                              ? ` · ${vm.institutionalAnswer.conviction}`
                              : ''}
                          </p>
                          {vm.institutionalAnswer.horizon ? (
                            <p className="rw-mini mt-1">Horizon: {vm.institutionalAnswer.horizon}</p>
                          ) : null}
                          {vm.institutionalAnswer.risk ? (
                            <p className="rw-body mt-2">{vm.institutionalAnswer.risk}</p>
                          ) : null}
                        </div>
                      ) : null}
                      <div>
                        <p className="rw-mini">Current View</p>
                        <p className={`rw-view-value tone-${vm.stanceTone}`}>{vm.stance}</p>
                      </div>
                      <div>
                        <p className="rw-mini">Confidence</p>
                        <p className="rw-view-value">{vm.confidence}%</p>
                        <p className="rw-mini">{vm.conviction} conviction</p>
                      </div>
                      <div>
                        <p className="rw-mini">Time Horizon</p>
                        <p className="font-semibold">{vm.horizon}</p>
                      </div>
                      <div>
                        <p className="rw-mini">Change vs Previous</p>
                        <p className="font-semibold tone-pos">{vm.changeVsPrevious}</p>
                      </div>
                      <div className="col-span-2">
                        <p className="rw-mini">Assessment Readiness</p>
                        <p className="font-semibold">
                          {vm.institutionalView?.readiness || vm.readiness}
                        </p>
                      </div>
                    </div>
                    {vm.institutionalView?.stance ? (
                      <p className="rw-body mt-4">
                        Committee: {vm.institutionalView.stance}
                        {vm.institutionalView.conviction
                          ? ` · ${vm.institutionalView.conviction} conviction`
                          : ''}
                        {vm.institutionalView.voteTally
                          ? ` · Vote ${vm.institutionalView.voteTally}`
                          : ''}
                        {vm.institutionalView.reason ? ` — ${vm.institutionalView.reason}` : ''}
                      </p>
                    ) : vm.institutionalView?.summary ? (
                      <p className="rw-body mt-4">{vm.institutionalView.summary}</p>
                    ) : null}
                    {vm.institutionalView?.decision ? (
                      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                        {[
                          ['Business Quality', vm.institutionalView.decision.business_quality],
                          ['Financials', vm.institutionalView.decision.financials],
                          ['Valuation', vm.institutionalView.decision.valuation],
                          ['Risk', vm.institutionalView.decision.risk],
                        ]
                          .filter(([, v]) => v)
                          .map(([label, value]) => (
                            <div key={label} className="rw-why-card">
                              <h4>{label}</h4>
                              <p>{value}</p>
                            </div>
                          ))}
                      </div>
                    ) : null}
                    {vm.institutionalView?.disagreementMatrix?.analyst_stances ? (
                      <div className="mt-4">
                        <p className="rw-mini mb-2">Disagreement Matrix</p>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {Object.entries(vm.institutionalView.disagreementMatrix.analyst_stances)
                            .slice(0, 9)
                            .map(([analyst, stance]) => (
                              <div key={analyst} className="rw-why-card">
                                <h4>{analyst}</h4>
                                <p>{stance}</p>
                              </div>
                            ))}
                        </div>
                      </div>
                    ) : null}
                    {vm.institutionalView?.stage2?.length ? (
                      <div className="mt-4">
                        <p className="rw-mini mb-2">Conflicts</p>
                        <ul className="space-y-2 text-sm text-[var(--rw-soft)]">
                          {vm.institutionalView.stage2.slice(0, 3).map((c) => (
                            <li key={c.topic || c.tension} className="border-b border-[var(--rw-border)] pb-2">
                              {c.tension || c.topic}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {vm.institutionalView?.challenges?.length ? (
                      <div className="mt-4">
                        <p className="rw-mini mb-2">Evidence challenges</p>
                        <ul className="space-y-2 text-sm text-[var(--rw-soft)]">
                          {vm.institutionalView.challenges.slice(0, 3).map((c) => (
                            <li
                              key={c.challenge || c.claim}
                              className="border-b border-[var(--rw-border)] pb-2"
                            >
                              {c.challenge}
                              {c.need ? ` Need: ${c.need}` : ''}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {vm.institutionalView?.stage3?.length ? (
                      <div className="mt-4">
                        <p className="rw-mini mb-2">Before increasing conviction, the committee would like</p>
                        <ul className="space-y-1 text-sm text-[var(--rw-muted)]">
                          {vm.institutionalView.stage3.slice(0, 4).map((m) => (
                            <li key={m}>• {m}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {vm.institutionalView?.minority?.length ? (
                      <div className="mt-4">
                        <p className="rw-mini mb-2">Minority view</p>
                        <ul className="space-y-1 text-sm text-[var(--rw-muted)]">
                          {vm.institutionalView.minority.map((m) => (
                            <li key={m}>• {m}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {vm.institutionalView?.minutes ? (
                      <div className="mt-4">
                        <p className="rw-mini mb-2">Investment Committee Minutes</p>
                        <p className="text-sm text-[var(--rw-soft)]">
                          Business {vm.institutionalView.minutes.business} · Financials{' '}
                          {vm.institutionalView.minutes.financials} · Valuation{' '}
                          {vm.institutionalView.minutes.valuation} · Macro{' '}
                          {vm.institutionalView.minutes.macro}
                        </p>
                        <p className="rw-body mt-2">
                          {vm.institutionalView.minutes.decision}{' '}
                          {vm.institutionalView.minutes.follow_up}
                        </p>
                      </div>
                    ) : null}
                  </Section>
                </div>

                {vm.investmentOfficeOs ? (
                  <Section
                    id="investment-office-os"
                    kicker="AGI v4.0"
                    title="Investment Office"
                  >
                    <p className="rw-mini mb-3">
                      {vm.investmentOfficeOs.release} · Thesis → Decision → Portfolio Idea → Monitoring →
                      Learning · Ideas are not positions
                    </p>
                    <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-5">
                      <div className="rw-why-card">
                        <h4>Thesis</h4>
                        <p>{vm.investmentOfficeOs.thesisId || '—'}</p>
                      </div>
                      <div className="rw-why-card">
                        <h4>Decision</h4>
                        <p>
                          {vm.investmentOfficeOs.decision || '—'}
                          {vm.investmentOfficeOs.decisionStatus
                            ? ` · ${vm.investmentOfficeOs.decisionStatus}`
                            : ''}
                        </p>
                      </div>
                      <div className="rw-why-card">
                        <h4>Portfolio idea</h4>
                        <p>
                          {vm.investmentOfficeOs.expectedRole || '—'}
                          {vm.investmentOfficeOs.relativeRank != null
                            ? ` · rank ${vm.investmentOfficeOs.relativeRank}`
                            : ''}
                        </p>
                      </div>
                      <div className="rw-why-card">
                        <h4>Monitoring</h4>
                        <p>
                          {vm.investmentOfficeOs.monitoringEvents != null
                            ? `${vm.investmentOfficeOs.monitoringEvents} events`
                            : '—'}
                          {vm.investmentOfficeOs.requiresReview != null
                            ? ` · ${vm.investmentOfficeOs.requiresReview} review`
                            : ''}
                        </p>
                      </div>
                      <div className="rw-why-card">
                        <h4>Learning</h4>
                        <p>
                          {vm.investmentOfficeOs.learningOutcome || '—'}
                          {vm.investmentOfficeOs.learningCategory
                            ? ` · ${vm.investmentOfficeOs.learningCategory}`
                            : ''}
                        </p>
                      </div>
                    </div>
                  </Section>
                ) : null}

                {vm.decisionEngine?.readinessGate || vm.recommendationStatus?.blocked ? (
                  <Section
                    id="institutional-gate"
                    kicker="Institutional Gate"
                    title="Evidence Readiness"
                  >
                    <p className="rw-body mb-3">
                      {(vm.decisionEngine?.readinessGate?.status_mark ||
                        (vm.recommendationStatus?.blocked ? '❌ FAILED' : '✓ PASSED')) +
                        ' · ' +
                        (vm.decisionEngine?.investmentThesisStatus ||
                          vm.recommendationStatus?.investmentThesisStatus ||
                          (vm.recommendationStatus?.blocked ? 'INCONCLUSIVE' : 'FORMED'))}
                    </p>
                    <p className="rw-body mb-4 text-[var(--rw-soft)]">
                      {vm.decisionEngine?.readinessGate?.reason ||
                        vm.recommendationStatus?.summary ||
                        'Evidence coverage decides whether a conviction call is allowed.'}
                      {vm.decisionEngine?.notANegativeView || vm.recommendationStatus?.notANegativeView
                        ? ' This is not a negative view of the company.'
                        : ''}
                    </p>
                    <div className="rw-grid-3 mb-4">
                      {[
                        ['Company Quality', vm.decisionEngine?.companyQuality10, '/10'],
                        ['Market Opportunity', vm.decisionEngine?.marketOpportunity10, '/10'],
                        [
                          'Evidence Confidence',
                          vm.decisionEngine?.evidenceConfidence ??
                            vm.recommendationStatus?.evidenceConfidence,
                          '%',
                        ],
                      ].map(([label, value, suffix]) => (
                        <div key={label} className="rw-why-card">
                          <h4>{label}</h4>
                          <p className="tabular-nums text-[var(--rw-ink)] font-semibold">
                            {value == null || Number.isNaN(Number(value))
                              ? '—'
                              : `${value}${suffix}`}
                          </p>
                        </div>
                      ))}
                    </div>
                    {vm.decisionEngine?.readinessGate?.coverage ||
                    vm.recommendationStatus?.coverage ? (
                      <div className="rw-decision-metrics mb-4">
                        {Object.entries(
                          vm.decisionEngine?.readinessGate?.coverage ||
                            vm.recommendationStatus?.coverage ||
                            {}
                        ).map(([k, v]) => (
                          <div key={k} className="rw-why-card">
                            <h4>{k.replace(/_/g, ' ')}</h4>
                            <p className="tabular-nums text-[var(--rw-ink)] font-semibold">{v}%</p>
                          </div>
                        ))}
                      </div>
                    ) : null}
                    {(vm.decisionEngine?.readinessGate?.checklist ||
                      vm.recommendationStatus?.checklist ||
                      []).length ? (
                      <ul className="mt-2 space-y-1 text-sm text-[var(--rw-soft)]">
                        {(
                          vm.decisionEngine?.readinessGate?.checklist ||
                          vm.recommendationStatus?.checklist ||
                          []
                        ).map((c) => (
                          <li key={c.label || c}>
                            {c.mark || (c.present ? '✓' : '⚠')} {c.label || c}
                            {c.detail ? ` — ${c.detail}` : ''}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {(vm.recommendationStatus?.additionalEvidenceRequired || []).length ? (
                      <p className="rw-body mt-3 text-[var(--rw-soft)]">
                        Additional evidence required:{' '}
                        {vm.recommendationStatus.additionalEvidenceRequired.join('; ')}.
                      </p>
                    ) : null}
                  </Section>
                ) : null}

                {vm.decisionEngine ? (
                  <Section id="decision-scorecard" kicker="Decision Framework" title="Investment Decision Scorecard">
                    <p className="rw-body mb-4">
                      Ownership questions are answered through a layered institutional stack — macro through
                      expected return — before any investment conclusion. No layer is skipped. Data
                      completeness is never treated as company quality.
                    </p>
                    <div className="rw-decision-scorecard">
                      <div className="rw-decision-hero">
                        <p className="rw-mini">Overall Score</p>
                        <p className="rw-decision-score">
                          {vm.decisionEngine.overallScore != null ? vm.decisionEngine.overallScore : '—'}
                          <span>/100</span>
                        </p>
                        <p className="rw-decision-grade">
                          Grade {vm.decisionEngine.investmentGrade || '—'} · Evidence{' '}
                          {vm.decisionEngine.evidenceConfidence != null
                            ? `${vm.decisionEngine.evidenceConfidence}%`
                            : `${vm.decisionEngine.confidence ?? '—'}%`}
                        </p>
                        {vm.decisionEngine.action ? (
                          <p className="rw-body mt-2 text-[var(--rw-soft)]">{vm.decisionEngine.action}</p>
                        ) : null}
                      </div>
                      <div className="rw-decision-metrics">
                        {[
                          ['Expected Return (12m)', vm.decisionEngine.expectedReturn12m, '%'],
                          ['Bull Case', vm.decisionEngine.bullCase, '%'],
                          ['Base Case', vm.decisionEngine.baseCase, '%'],
                          ['Bear Case', vm.decisionEngine.bearCase, '%'],
                          ['Prob. Weighted', vm.decisionEngine.probabilityWeighted, '%'],
                          ['Risk / Reward', vm.decisionEngine.riskReward, ''],
                        ].map(([label, value, suffix]) => (
                          <div key={label} className="rw-why-card">
                            <h4>{label}</h4>
                            <p className="tabular-nums text-[var(--rw-ink)] font-semibold">
                              {value == null || Number.isNaN(Number(value))
                                ? '—'
                                : `${Number(value) > 0 && suffix === '%' ? '+' : ''}${value}${suffix}`}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                    {vm.decisionEngine.stackLayers?.length ? (
                      <div className="mt-4 space-y-3">
                        {vm.decisionEngine.stackLayers
                          .filter((l) => l.id !== 'decision')
                          .slice(0, 4)
                          .map((layer) => (
                            <div key={layer.id} className="rw-why-card">
                              <h4>
                                {layer.title}{' '}
                                {layer.score != null ? (
                                  <span className="tabular-nums font-semibold">
                                    {layer.score}/100
                                  </span>
                                ) : null}
                              </h4>
                              {(layer.strengths || []).length ? (
                                <p className="text-sm text-[var(--rw-soft)]">
                                  Strengths: {(layer.strengths || []).slice(0, 3).join(' · ')}
                                </p>
                              ) : null}
                              {(layer.weaknesses || []).length ? (
                                <p className="text-sm text-[var(--rw-soft)]">
                                  Watch: {(layer.weaknesses || []).slice(0, 3).join(' · ')}
                                </p>
                              ) : null}
                              {layer.evidence_quality_score != null ? (
                                <p className="text-sm text-[var(--rw-soft)]">
                                  Evidence quality {layer.evidence_quality_score}/100 (separate from
                                  company quality)
                                </p>
                              ) : null}
                            </div>
                          ))}
                      </div>
                    ) : null}
                    {vm.decisionEngine.preQuestions?.length ? (
                      <ol className="rw-preq mt-4">
                        {vm.decisionEngine.preQuestions.map((q) => (
                          <li key={q}>{q}</li>
                        ))}
                      </ol>
                    ) : null}
                  </Section>
                ) : null}

                {vm.kpis?.length ? (
                  <Section id="dashboard" kicker="Section 3" title="Executive Dashboard">
                    <div className="rw-grid-4">
                      {vm.kpis.map((k) => (
                        <div key={k.label} className={`rw-kpi tone-${k.tone}`}>
                          <p className="label">{k.label}</p>
                          <p className="value">{k.value}</p>
                          <p className="hint">{k.hint}</p>
                          <div className="spark">
                            <Sparkline points={k.spark} up={k.tone !== 'neg'} width={88} height={24} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </Section>
                ) : null}

                <div className="rw-grid-2">
                  <Section
                    id="thesis"
                    kicker={ownerKicker(vm, 'executive_summary', 'Section 4')}
                    title="Investment Thesis"
                  >
                    <p className="rw-body">{vm.thesis}</p>
                    {vm.why.length ? (
                      <ul className="mt-3 space-y-2 text-sm text-[var(--rw-soft)]">
                        {vm.why.slice(0, 5).map((w) => (
                          <li key={w} className="border-b border-[var(--rw-border)] pb-2">
                            {w}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </Section>
                  <Section id="why" kicker="Section 5" title="Why This View">
                    <div className="grid grid-cols-2 gap-2">
                      {vm.whyCards.map((c) => (
                        <div key={c.key} className="rw-why-card">
                          <h4>{c.label}</h4>
                          <p>{c.text}</p>
                        </div>
                      ))}
                    </div>
                  </Section>
                </div>

                {vm.intelligenceLayer?.enabled ? (
                  <Section id="living-intel" kicker="Living Intelligence" title="Company Dossier · Thesis · Forecast">
                    <div className="rw-grid-3 mb-4">
                      <div className="rw-kpi tone-neu">
                        <p className="label">Dossier</p>
                        <p className="value text-[18px]">
                          {vm.intelligenceLayer.ticker || '—'}
                          {vm.intelligenceLayer.dossierVersion != null
                            ? ` · v${vm.intelligenceLayer.dossierVersion}`
                            : ''}
                        </p>
                        <p className="hint">{vm.intelligenceLayer.company || 'Living institutional dossier'}</p>
                      </div>
                      <div className="rw-kpi tone-neu">
                        <p className="label">Bull / Base / Bear</p>
                        <p className="value text-[18px]">
                          {pctLabel(vm.intelligenceLayer.thesis?.bull)} /{' '}
                          {pctLabel(vm.intelligenceLayer.thesis?.base)} /{' '}
                          {pctLabel(vm.intelligenceLayer.thesis?.bear)}
                        </p>
                        <p className="hint">Explainable thesis probabilities</p>
                      </div>
                      <div className="rw-kpi tone-neu">
                        <p className="label">Forecast confidence</p>
                        <p className="value text-[18px]">
                          {pctLabel(vm.intelligenceLayer.forecastConfidence)}
                        </p>
                        <p className="hint">
                          {vm.intelligenceLayer.forecastId
                            ? `Prediction ${vm.intelligenceLayer.forecastId}`
                            : 'Distributional forecast'}
                        </p>
                      </div>
                    </div>
                    {vm.intelligenceLayer.distributions?.length ? (
                      <div className="overflow-x-auto mb-4">
                        <table className="rw-table">
                          <thead>
                            <tr>
                              <th>Metric</th>
                              <th>P10</th>
                              <th>P50</th>
                              <th>P90</th>
                            </tr>
                          </thead>
                          <tbody>
                            {vm.intelligenceLayer.distributions.map((d) => (
                              <tr key={d.metric}>
                                <td className="font-semibold text-[var(--rw-ink)]">
                                  {d.metric}
                                  {d.unit ? ` (${d.unit})` : ''}
                                </td>
                                <td>{fmtNum(d.p10)}</td>
                                <td>{fmtNum(d.p50)}</td>
                                <td>{fmtNum(d.p90)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : null}
                    {vm.intelligenceLayer.hints?.length ? (
                      <ul className="mb-3 space-y-2 text-sm text-[var(--rw-soft)]">
                        {vm.intelligenceLayer.hints.map((h) => (
                          <li key={h} className="border-b border-[var(--rw-border)] pb-2">
                            {h}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    <p className="rw-empty">
                      Evidence IDs: {(vm.intelligenceLayer.supportingEvidenceIds || []).slice(0, 4).join(', ') || '—'}
                      {vm.intelligenceLayer.auditId ? ` · Audit ${vm.intelligenceLayer.auditId}` : ''}
                      {vm.intelligenceLayer.graphCount != null
                        ? ` · Graph links ${vm.intelligenceLayer.graphCount}`
                        : ''}
                    </p>
                  </Section>
                ) : null}

                <Section id="changed" kicker="Section 6" title="What's Changed">
                  {vm.whatChanged?.length ? (
                    <ul className="mb-4 space-y-2 text-sm text-[var(--rw-soft)]">
                      {vm.whatChanged.map((item) => (
                        <li key={item} className="border-b border-[var(--rw-border)] pb-2">
                          {item}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {vm.changedRows.length ? (
                    <div className="overflow-x-auto">
                      <table className="rw-table">
                        <thead>
                          <tr>
                            <th>Metric</th>
                            <th>Previous</th>
                            <th>Current</th>
                            <th>Change</th>
                          </tr>
                        </thead>
                        <tbody>
                          {vm.changedRows.map((r) => (
                            <tr key={`${r.metric}-${r.current}`}>
                              <td className="font-semibold text-[var(--rw-ink)]">{r.metric}</td>
                              <td>{r.previous}</td>
                              <td>{r.current}</td>
                              <td className="tone-pos">{r.change}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : !vm.whatChanged?.length ? (
                    <p className="rw-empty">No material period-over-period changes surfaced yet.</p>
                  ) : null}
                </Section>

                <Section
                  id="financials"
                  kicker={ownerKicker(vm, 'financial_intelligence', 'Section 7')}
                  title="Financial Intelligence"
                >
                  <p className="rw-body mb-4">{vm.financialNarrative}</p>
                  {vm.financialCards?.length ? (
                    <div className="rw-grid-3">
                      {vm.financialCards.map((c) => (
                        <div key={c.label} className={`rw-kpi tone-${c.tone}`}>
                          <p className="label">{c.label}</p>
                          <p className="value text-[18px]">{c.display}</p>
                          <p className="hint">{c.status}</p>
                          <div className="spark">
                            <Sparkline points={c.spark} up={c.tone === 'pos'} width={90} height={24} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </Section>

                <Section
                  id="valuation"
                  kicker={ownerKicker(vm, 'valuation_intelligence', 'Section 8')}
                  title="Valuation Intelligence"
                >
                  <p className="rw-body mb-4">{vm.valuationNarrative}</p>
                  {vm.valuationCards?.length ? (
                    <div className="rw-grid-3 mb-4">
                      {vm.valuationCards.map((c) => (
                        <div key={c.label} className={`rw-kpi tone-${c.tone || 'neu'}`}>
                          <p className="label">{c.label}</p>
                          <p className="value text-[18px]">{c.value}</p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {chartData.length >= 2 ? (
                    <div className="h-56 rounded-xl border border-[var(--rw-border)] bg-[var(--rw-panel-2)] p-3">
                      <ResponsiveContainer width="100%" height="100%">
                        <RLineChart data={chartData}>
                          <XAxis dataKey="name" hide />
                          <YAxis stroke="var(--rw-caption)" fontSize={11} width={40} />
                          <Tooltip
                            contentStyle={{
                              background: '#151b27',
                              border: '1px solid rgba(255,255,255,0.1)',
                              borderRadius: 8,
                            }}
                          />
                          <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
                        </RLineChart>
                      </ResponsiveContainer>
                    </div>
                  ) : null}
                </Section>

                <div className="rw-grid-2">
                  <Section
                    id="business"
                    kicker={ownerKicker(vm, 'business_intelligence', 'Section 9')}
                    title="Business Intelligence"
                  >
                    <p className="rw-body">
                      {vm.businessModel ||
                        vm.businessIntelligence?.narrative ||
                        'The equity debate starts with how the company earns money, where it has advantage, and whether that advantage can compound.'}
                    </p>
                    <div className="mt-3 grid grid-cols-1 gap-2">
                      {[
                        ['Competitive advantages', vm.businessIntelligence?.competitive_advantages],
                        ['Revenue drivers', vm.businessIntelligence?.revenue_drivers],
                        ['Operating metrics', vm.businessIntelligence?.operating_metrics],
                        ['Long-term growth', vm.businessIntelligence?.long_term_growth],
                      ]
                        .filter(([, text]) => text)
                        .map(([title, text]) => (
                          <div key={title} className="rw-why-card">
                            <h4>{title}</h4>
                            <p>{text}</p>
                          </div>
                        ))}
                    </div>
                  </Section>
                  <Section
                    id="market"
                    kicker={ownerKicker(vm, 'market_intelligence', 'Section 10')}
                    title="Market Intelligence"
                  >
                    <p className="rw-body">
                      {vm.marketNarrative ||
                        'Market context frames entry timing and risk appetite — it does not replace business or valuation analysis.'}
                    </p>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                      {(vm.marketCards?.length
                        ? vm.marketCards.map((c) => [c.label, c.value])
                        : [
                            ['Price', vm.marketSnapshot.current_price],
                            ['52W High', vm.marketSnapshot.fifty_two_week_high],
                            ['52W Low', vm.marketSnapshot.fifty_two_week_low],
                            ['Market Cap', vm.marketSnapshot.market_cap],
                          ]
                      )
                        .filter(([, value]) => value != null && value !== '' && value !== '—')
                        .map(([label, value]) => (
                          <div key={label} className="rw-why-card">
                            <h4>{label}</h4>
                            <p>{String(value)}</p>
                          </div>
                        ))}
                    </div>
                  </Section>
                </div>

                <div className="rw-grid-2">
                  <Section
                    id="sector"
                    kicker={ownerKicker(vm, 'sector_intelligence', 'Section 11')}
                    title="Sector Intelligence"
                  >
                    <p className="rw-body">
                      {vm.sectorNarrative ||
                        'Industry structure matters because it shapes pricing power, capital intensity and the durability of returns.'}
                    </p>
                    {vm.sectorDrivers.length ? (
                      <ul className="mt-3 space-y-1 text-sm text-[var(--rw-muted)]">
                        {vm.sectorDrivers.map((d) => (
                          <li key={d}>• {String(d).replace(/_/g, ' ')}</li>
                        ))}
                      </ul>
                    ) : null}
                  </Section>
                  <Section
                    id="macro"
                    kicker={ownerKicker(vm, 'macro_intelligence', 'Section 12')}
                    title="Macro Intelligence"
                  >
                    <p className="rw-body mb-3">
                      {vm.macroNarrative ||
                        'Macro conditions matter for discount rates, risk appetite and cyclical demand — they should frame the company debate rather than replace it.'}
                    </p>
                    {vm.macroDrivers.length ? (
                      <ul className="space-y-2 text-sm text-[var(--rw-soft)]">
                        {vm.macroDrivers.map((d) => (
                          <li key={d} className="border-b border-[var(--rw-border)] pb-2">
                            {d}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </Section>
                </div>

                {vm.institutionalStack ? (
                  <Section
                    id="institutional-stack"
                    kicker="Institutional Stack"
                    title="Filing · Trust · Accounting · Portfolio Fit · Peers"
                  >
                    <div className="rw-grid-2">
                      <div>
                        <p className="rw-mini">Management DNA</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.managementDna || '—'}
                        </p>
                        <p className="rw-mini mt-2">Management trust</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.managementConfidence ?? '—'}
                        </p>
                        <p className="rw-mini mt-2">Accounting behaviour</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.accountingBehaviour || '—'}
                        </p>
                        <p className="rw-mini mt-2">Accounting quality</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.accountingQuality ?? '—'}
                          {vm.institutionalStack.manipulationRisk
                            ? ` · manip. ${vm.institutionalStack.manipulationRisk}`
                            : ''}
                        </p>
                      </div>
                      <div>
                        <p className="rw-mini">Portfolio book</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.portfolioId || '—'}
                          {vm.institutionalStack.portfolioGrade
                            ? ` · grade ${vm.institutionalStack.portfolioGrade}`
                            : ''}
                        </p>
                        <p className="rw-mini mt-2">Portfolio quality (PQE)</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.portfolioQuality ?? '—'}
                        </p>
                        <p className="rw-mini mt-2">Candidate portfolio effect</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.portfolioNetEffect || '—'}
                          {vm.institutionalStack.portfolioFit
                            ? ` · fit ${vm.institutionalStack.portfolioFit}`
                            : ''}
                        </p>
                        <p className="rw-mini mt-2">Filing / what-changed</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.filingFound ? 'Filings present' : 'Sparse'}
                          {vm.institutionalStack.materialChangeSignal ? ' · FDI active' : ''}
                        </p>
                        <p className="rw-mini mt-2">Causal why</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.causalWhy || '—'}
                          {vm.institutionalStack.causalConfidence != null
                            ? ` · conf ${vm.institutionalStack.causalConfidence}`
                            : ''}
                        </p>
                        {Array.isArray(vm.institutionalStack.causalUpstream) &&
                        vm.institutionalStack.causalUpstream.length ? (
                          <>
                            <p className="rw-mini mt-2">Upstream drivers</p>
                            <p className="font-semibold">
                              {vm.institutionalStack.causalUpstream.slice(0, 4).join(' → ')}
                            </p>
                          </>
                        ) : null}
                        <p className="rw-mini mt-2">Most likely scenario</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.forecastMostLikely || '—'}
                          {vm.institutionalStack.forecastConfidence != null
                            ? ` · conf ${vm.institutionalStack.forecastConfidence}`
                            : ''}
                        </p>
                        {vm.institutionalStack.forecastSummary ? (
                          <p className="text-xs text-slate-500 mt-2">
                            {vm.institutionalStack.forecastSummary}
                          </p>
                        ) : null}
                        <p className="rw-mini mt-2">Knowledge connections</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.knowledgeRelationshipCount ?? '—'}
                          {vm.institutionalStack.knowledgeCanonicalId
                            ? ` · ${vm.institutionalStack.knowledgeCanonicalId}`
                            : ''}
                          {vm.institutionalStack.knowledgeConfidence != null
                            ? ` · conf ${vm.institutionalStack.knowledgeConfidence}`
                            : ''}
                        </p>
                        {vm.institutionalStack.knowledgeSummary ? (
                          <p className="text-xs text-slate-500 mt-2">
                            {vm.institutionalStack.knowledgeSummary}
                          </p>
                        ) : null}
                        <p className="rw-mini mt-2">Institutional learning</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.memoryLessonCount != null
                            ? `${vm.institutionalStack.memoryLessonCount} lessons`
                            : '—'}
                          {vm.institutionalStack.memoryMistakeCount != null
                            ? ` · ${vm.institutionalStack.memoryMistakeCount} mistakes`
                            : ''}
                          {vm.institutionalStack.memoryThinkingImproved != null
                            ? ` · thinking ${vm.institutionalStack.memoryThinkingImproved ? 'improved' : 'not yet'}`
                            : ''}
                        </p>
                        {vm.institutionalStack.memorySummary ? (
                          <p className="text-xs text-slate-500 mt-2">
                            {vm.institutionalStack.memorySummary}
                          </p>
                        ) : null}
                        <p className="rw-mini mt-2">Simulation lab</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.simulationScenarioId || '—'}
                          {vm.institutionalStack.simulationExpectedReturn != null
                            ? ` · E[r] ${vm.institutionalStack.simulationExpectedReturn}`
                            : ''}
                          {vm.institutionalStack.simulationConfidence != null
                            ? ` · conf ${vm.institutionalStack.simulationConfidence}`
                            : ''}
                        </p>
                        {vm.institutionalStack.simulationSummary ? (
                          <p className="text-xs text-slate-500 mt-2">
                            {vm.institutionalStack.simulationSummary}
                          </p>
                        ) : null}
                        <p className="rw-mini mt-2">Constitutional decision</p>
                        <p className="font-semibold">
                          {vm.institutionalStack.decisionStatus || '—'}
                          {vm.institutionalStack.decisionConfidence != null
                            ? ` · conf ${vm.institutionalStack.decisionConfidence}`
                            : ''}
                          {vm.institutionalStack.decisionAuditId
                            ? ` · audit ${String(vm.institutionalStack.decisionAuditId).slice(0, 8)}`
                            : ''}
                        </p>
                        {vm.institutionalStack.decisionSummary ? (
                          <p className="text-xs text-slate-500 mt-2">
                            {vm.institutionalStack.decisionSummary}
                          </p>
                        ) : null}
                      </div>
                    </div>
                    {vm.institutionalStack.openConcerns?.length ? (
                      <ul className="rw-list mt-3">
                        {vm.institutionalStack.openConcerns.map((c) => (
                          <li key={c}>{c}</li>
                        ))}
                      </ul>
                    ) : null}
                  </Section>
                ) : null}

                {(vm.managementNarrative || vm.ownershipNarrative || vm.institutionalStack) && (
                  <div className="rw-grid-2">
                    <Section
                      id="management"
                      kicker={ownerKicker(vm, 'management', 'Management')}
                      title="Management"
                    >
                      <p className="rw-body">
                        {vm.managementNarrative ||
                          'Governance, capital allocation and communication consistency determine whether franchise quality converts into owner outcomes.'}
                      </p>
                    </Section>
                    <Section
                      id="ownership"
                      kicker={ownerKicker(vm, 'ownership', 'Ownership')}
                      title="Ownership"
                    >
                      <p className="rw-body">
                        {vm.ownershipNarrative ||
                          'Ownership structure and sequential stake changes signal alignment and free-float dynamics.'}
                      </p>
                    </Section>
                  </div>
                )}

                {vm.leaders.length ? (
                  <Section id="leaders" kicker="Section 13" title="Sector Leaders">
                    <div className="overflow-x-auto">
                      <table className="rw-table">
                        <thead>
                          <tr>
                            <th>Company</th>
                            <th>View</th>
                            <th>Financial</th>
                            <th>Valuation</th>
                            <th>Quality</th>
                            <th>Confidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {vm.leaders.map((row) => (
                            <tr key={row.company}>
                              <td className="font-semibold text-[var(--rw-ink)]">{row.company}</td>
                              <td className={`tone-${vm.stanceTone}`}>{row.view}</td>
                              <td>{row.financial}</td>
                              <td>{row.valuation}</td>
                              <td>{row.quality}</td>
                              <td>{row.confidence}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Section>
                ) : null}

                <Section
                  id="scenarios"
                  kicker={ownerKicker(vm, 'scenarios', 'Section 14')}
                  title="Bull · Base · Bear"
                >
                  <div className="rw-grid-3">
                    {[
                      {
                        key: 'bull',
                        title: 'Bull',
                        items: vm.bull,
                        prob:
                          vm.decisionEngine?.bullCase != null
                            ? `${vm.decisionEngine.bullCase}% ret`
                            : '35%',
                      },
                      {
                        key: 'base',
                        title: 'Base',
                        items: vm.base,
                        prob:
                          vm.decisionEngine?.baseCase != null
                            ? `${vm.decisionEngine.baseCase}% ret`
                            : '45%',
                      },
                      {
                        key: 'bear',
                        title: 'Bear',
                        items: vm.bear,
                        prob:
                          vm.decisionEngine?.bearCase != null
                            ? `${vm.decisionEngine.bearCase}% ret`
                            : '20%',
                      },
                    ].map((s) => (
                      <div key={s.key} className={`rw-scenario ${s.key}`}>
                        <div className="flex items-center justify-between">
                          <h3 className="font-bold">{s.title}</h3>
                          <span className="rw-mini">Prob {s.prob}</span>
                        </div>
                        <ul className="mt-3 space-y-2 text-sm text-[var(--rw-soft)]">
                          {(s.items.length ? s.items : ['Scenario narrative pending richer evidence.']).map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </Section>

                <div className="rw-grid-2">
                  <Section id="risks" kicker={ownerKicker(vm, 'risks', 'Section 15')} title="Top Risks">
                    {vm.risks.length ? (
                      <div className="overflow-x-auto">
                        <table className="rw-table">
                          <thead>
                            <tr>
                              <th>Risk</th>
                              <th>Probability</th>
                              <th>Impact</th>
                              <th>Severity</th>
                              <th>Monitoring</th>
                            </tr>
                          </thead>
                          <tbody>
                            {vm.risks.map((r) => (
                              <tr key={r.risk}>
                                <td className="text-[var(--rw-ink)]">{r.risk}</td>
                                <td>{r.probability}</td>
                                <td>{r.impact}</td>
                                <td className={r.severity === 'Critical' ? 'tone-neg' : 'tone-warn'}>
                                  {r.severity}
                                </td>
                                <td className="tone-pos">{r.monitoring}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="rw-empty">No critical risks listed for this briefing.</p>
                    )}
                  </Section>
                  <Section id="confidence" kicker="Section 17" title="Confidence Assessment">
                    <div className="rw-donut-wrap">
                      <Donut value={vm.confidence} />
                      <ul className="space-y-2 text-sm text-[var(--rw-soft)]">
                        {[
                          ['Financials', Math.min(99, vm.confidence + 2)],
                          ['Business', Math.min(99, vm.confidence - 1)],
                          ['Valuation', Math.min(99, vm.confidence - 4)],
                          ['Sector', Math.min(99, vm.confidence)],
                          ['Knowledge', Math.min(99, vm.coverage)],
                        ].map(([label, value]) => (
                          <li key={label} className="flex justify-between border-b border-[var(--rw-border)] pb-1">
                            <span>{label}</span>
                            <span className="tabular-nums">{value}%</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </Section>
                </div>

                <Section id="catalysts" kicker="Section 16" title="Key Catalysts">
                  {vm.catalysts.length ? (
                    <div className="rw-timeline">
                      {vm.catalysts.map((c, idx) => (
                        <div key={c} className="rw-timeline-item">
                          <p className="rw-mini">T+{idx + 1}</p>
                          <p className="mt-1 text-sm font-semibold text-[var(--rw-ink)]">{c}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="rw-empty">Catalyst calendar will populate from corporate and research events.</p>
                  )}
                </Section>

                {vm.learned?.length ? (
                  <Section id="learned" kicker="Section 18" title="Research Takeaways">
                    <ul className="space-y-2 text-sm">
                      {vm.learned.map((item) => (
                        <li key={item} className="flex items-start gap-2 text-[var(--rw-soft)]">
                          <span className="tone-pos mt-0.5">✓</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </Section>
                ) : null}

                {vm.decisionEngine?.stackLayers?.length ? (
                  <Section id="decision-stack" kicker="Decision Stack" title="Layered Investment Analysis">
                    <p className="rw-body mb-4">
                      Each layer answers one institutional question with evidence. The investment decision
                      appears only after this stack is complete.
                    </p>
                    <div className="rw-stack">
                      {vm.decisionEngine.stackLayers.map((layer) => (
                        <article key={layer.id} className="rw-stack-layer">
                          <header>
                            <div>
                              <p className="rw-mini">
                                Layer {layer.index}
                                {layer.weight != null ? ` · Weight ${layer.weight}%` : ''}
                              </p>
                              <h3>{layer.title}</h3>
                              {layer.question ? <p className="rw-stack-q">{layer.question}</p> : null}
                            </div>
                            <div className="rw-stack-score">
                              {layer.score != null ? (
                                <>
                                  <strong>{layer.score}</strong>
                                  <span>{layer.grade || layer.status}</span>
                                </>
                              ) : (
                                <span className="rw-mini">{layer.status}</span>
                              )}
                            </div>
                          </header>
                          {layer.reasoning ? <p className="rw-body mt-3">{layer.reasoning}</p> : null}
                          {layer.evidence?.length ? (
                            <ul className="mt-2 space-y-1 text-sm text-[var(--rw-muted)]">
                              {layer.evidence.map((e) => (
                                <li key={e}>• {e}</li>
                              ))}
                            </ul>
                          ) : null}
                          {layer.positive?.length || layer.negative?.length ? (
                            <div className="rw-grid-2 mt-3">
                              {layer.positive?.length ? (
                                <div>
                                  <p className="rw-mini tone-pos">Positive</p>
                                  <ul className="mt-1 space-y-1 text-sm text-[var(--rw-soft)]">
                                    {layer.positive.map((e) => (
                                      <li key={e}>• {e}</li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}
                              {layer.negative?.length ? (
                                <div>
                                  <p className="rw-mini tone-neg">Negative</p>
                                  <ul className="mt-1 space-y-1 text-sm text-[var(--rw-soft)]">
                                    {layer.negative.map((e) => (
                                      <li key={e}>• {e}</li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}
                            </div>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  </Section>
                ) : null}

                <Section
                  id="conclusion"
                  kicker={ownerKicker(vm, 'conclusion', 'Section 19')}
                  title="Institutional Conclusion"
                >
                  <p className="rw-body">{vm.conclusion}</p>
                  {vm.decisionEngine ? (
                    <div className="rw-decision-final mt-4">
                      <p className="rw-mini">Layer 13 · Investment Decision</p>
                      <p className="rw-view-value text-[20px] mt-1">
                        {vm.decisionEngine.action || 'Committee conclusion pending fuller evidence'}
                      </p>
                      <div className="rw-grid-2 mt-3">
                        <div>
                          <p className="rw-mini tone-pos">Suitable for</p>
                          <ul className="mt-1 space-y-1 text-sm text-[var(--rw-soft)]">
                            {(vm.decisionEngine.suitableFor.length
                              ? vm.decisionEngine.suitableFor
                              : ['Watchlist']
                            ).map((item) => (
                              <li key={item}>✔ {item}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="rw-mini tone-neg">Not suitable for</p>
                          <ul className="mt-1 space-y-1 text-sm text-[var(--rw-soft)]">
                            {(vm.decisionEngine.unsuitableFor.length
                              ? vm.decisionEngine.unsuitableFor
                              : ['High-Leverage Positions']
                            ).map((item) => (
                              <li key={item}>✖ {item}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  ) : null}
                  <p className="rw-mini mt-3">
                    This briefing is institutional research context — not a brokerage order ticket.
                  </p>
                </Section>

                <Section
                  id="recommendation-status"
                  kicker={ownerKicker(vm, 'recommendation_status', 'Section 19b')}
                  title="Institutional Recommendation Status"
                >
                  <p className={`rw-view-value text-[22px] tone-${vm.recommendationStatus.blocked ? 'warn' : 'pos'}`}>
                    {vm.recommendationStatus.status}
                  </p>
                  <p className="rw-body mt-3">{vm.recommendationStatus.summary}</p>
                  {vm.recommendationStatus.detail ? (
                    <p className="rw-body mt-2">{vm.recommendationStatus.detail}</p>
                  ) : null}
                  {(vm.knowledgeGaps || []).length ? (
                    <div className="mt-4">
                      <p className="rw-mini mb-2">Current Knowledge Gaps</p>
                      <ul className="space-y-2 text-sm text-[var(--rw-soft)]">
                        {vm.knowledgeGaps.map((g) => (
                          <li key={g} className="border-b border-[var(--rw-border)] pb-2">
                            {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </Section>

                <Section id="explore" kicker="Section 20" title="Explore Further">
                  <div className="rw-explore">
                    {vm.explore.map((q) => (
                      <button key={q} type="button" onClick={() => submit(q)}>
                        {q}
                      </button>
                    ))}
                  </div>
                </Section>

                <div className="rw-footer">
                  <div className="flex flex-wrap gap-3">
                    <Link to="/admin/mission-control">Mission Control</Link>
                    <Link to="/admin/knowledge">Knowledge</Link>
                    <Link to="/research">Research</Link>
                    <button type="button" className="bg-transparent border-0 text-inherit cursor-pointer p-0" onClick={() => navigate('/markets')}>
                      Markets
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={12} className="opacity-50" />
                    <span>System Status: All Systems Operational</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
