import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  RefreshCw,
  Download,
  Sparkles,
  ArrowLeft,
  AlertTriangle,
  ExternalLink,
  Library,
  LineChart,
  Briefcase,
  Clock,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';
import Forbidden403 from '@/components/admin/Forbidden403';
import {
  getInvestmentOfficeOverview,
  refreshInvestmentOfficeMorning,
  generateInvestmentOfficeMorningBrief,
} from '@/lib/intelligenceApi';
import './investmentOffice.css';

function fmt(v) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(1);
  return String(v);
}

function Badge({ children, tone }) {
  return <span className={`io-badge ${String(tone || 'monitor').toLowerCase()}`}>{children}</span>;
}

function Kpi({ label, value }) {
  return (
    <div className="io-kpi">
      <div className="label">{label}</div>
      <div className="value">{fmt(value)}</div>
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div className="io-meta">
      <div className="label">{label}</div>
      <div className="value">{fmt(value)}</div>
    </div>
  );
}

function Section({ id, title, lede, children, style }) {
  return (
    <section id={id} className="io-section" style={style}>
      <p className="io-kicker">Institutional desk</p>
      <h2>{title}</h2>
      {lede ? <p className="lede">{lede}</p> : null}
      {children}
    </section>
  );
}

function flattenMarketGroup(group) {
  if (!group || typeof group !== 'object') return [];
  if (Array.isArray(group)) {
    return group.slice(0, 8).map((row) => ({
      symbol: row.symbol || row.name || row.ticker || '—',
      value: row.value ?? row.last ?? row.level ?? row.change ?? '—',
    }));
  }
  const nested = [];
  for (const [k, v] of Object.entries(group)) {
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      nested.push({
        symbol: k.replace(/_/g, ' ').toUpperCase(),
        value: v.last ?? v.value ?? v.level ?? v.change ?? '—',
      });
    } else if (v != null && typeof v !== 'object') {
      nested.push({ symbol: k.replace(/_/g, ' ').toUpperCase(), value: v });
    }
  }
  return nested.slice(0, 8);
}

const DEFAULT_MARKETS = {
  india: [
    { symbol: 'NIFTY', value: '—' },
    { symbol: 'BANK NIFTY', value: '—' },
    { symbol: 'SENSEX', value: '—' },
    { symbol: 'VIX', value: '—' },
  ],
  global: [
    { symbol: 'S&P500', value: '—' },
    { symbol: 'NASDAQ', value: '—' },
    { symbol: 'DOW', value: '—' },
    { symbol: 'FTSE', value: '—' },
    { symbol: 'DAX', value: '—' },
    { symbol: 'NIKKEI', value: '—' },
    { symbol: 'HANG SENG', value: '—' },
  ],
  commodities: [
    { symbol: 'GOLD', value: '—' },
    { symbol: 'SILVER', value: '—' },
    { symbol: 'BRENT', value: '—' },
    { symbol: 'NATURAL GAS', value: '—' },
  ],
  currencies: [
    { symbol: 'USDINR', value: '—' },
    { symbol: 'EURUSD', value: '—' },
    { symbol: 'GBPUSD', value: '—' },
    { symbol: 'US10Y', value: '—' },
  ],
};

export default function InvestmentOfficeAdmin() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [desk, setDesk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [clock, setClock] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  const load = useCallback(async ({ silent } = {}) => {
    if (!silent) setLoading(true);
    setError('');
    try {
      const data = await getInvestmentOfficeOverview();
      setDesk(data);
      return data;
    } catch (err) {
      setError(err?.message || 'Failed to load Investment Office');
      return null;
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // While snapshot is building, poll the fast overview (no heavy recompute on server).
  useEffect(() => {
    if (!desk?.building) return undefined;
    const id = setInterval(() => {
      load({ silent: true });
    }, 4000);
    return () => clearInterval(id);
  }, [desk?.building, load]);

  const header = desk?.header || {};
  const date = header.date || {};
  const top = desk?.top_summary || {};
  const brief = desk?.executive_brief || {};
  const priorities = desk?.priorities || [];
  const overnight = desk?.overnight_activity || [];
  const queue = desk?.research_queue || {};
  const opportunities = desk?.opportunities || [];
  const market = desk?.market_summary || {};
  const macro = desk?.macro || {};
  const calendar = desk?.calendar || {};
  const portfolio = desk?.portfolio_monitor || {};
  const sectors = desk?.sector_monitor || [];
  const metrics = desk?.metrics || {};
  const workspace = desk?.analyst_workspace || {};
  const invCal = desk?.investment_calendar || {};
  const ai = desk?.ai_summary || {};

  const clockLabel = useMemo(
    () =>
      clock.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      }),
    [clock]
  );

  const openCompany = (ticker) => {
    if (!ticker) return;
    navigate(`/research/stocks/${encodeURIComponent(String(ticker).toUpperCase())}`);
  };

  const onRefresh = async () => {
    setBusy('refresh');
    setError('');
    try {
      const res = await refreshInvestmentOfficeMorning({ wait: false });
      // Keep serving current snapshot; mark building so poll picks up the new one.
      setDesk((prev) => ({
        ...(res?.overview || prev || {}),
        building: true,
        refresh_job: { job_id: res?.job_id, status: res?.status },
      }));
      setTimeout(() => load({ silent: true }), 2500);
    } catch (err) {
      setError(err?.message || 'Refresh failed');
    } finally {
      setBusy('');
    }
  };

  const onGenerateBrief = async () => {
    setBusy('brief');
    setError('');
    try {
      const res = await generateInvestmentOfficeMorningBrief();
      setDesk((prev) => ({
        ...(prev || {}),
        building: true,
        executive_brief: res.executive_brief || prev?.executive_brief,
        ai_summary: res.ai_summary || prev?.ai_summary,
        priorities: res.priorities || prev?.priorities,
        top_summary: res.top_summary || prev?.top_summary,
      }));
      setTimeout(() => load({ silent: true }), 2500);
    } catch (err) {
      setError(err?.message || 'Brief generation failed');
    } finally {
      setBusy('');
    }
  };

  const exportJson = () => {
    if (!desk) return;
    const blob = new Blob([JSON.stringify(desk, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `investment-office-${date.iso_date || 'brief'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportCsv = () => {
    const rows = [['Company', 'Priority', 'Reason', 'Impact', 'ETA', 'Owner']];
    priorities.forEach((p) => {
      rows.push([
        p.ticker || p.company || '',
        p.priority || '',
        (p.reason || '').replace(/,/g, ';'),
        p.expected_impact || '',
        p.eta_minutes != null ? `${p.eta_minutes} min` : '',
        p.owner || '',
      ]);
    });
    const blob = new Blob([rows.map((r) => r.join(',')).join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'investment-office-priorities.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isAdmin(user)) {
    return <Forbidden403 resource="Investment Office" />;
  }

  const indiaRows = flattenMarketGroup(market.india).length
    ? flattenMarketGroup(market.india)
    : DEFAULT_MARKETS.india;
  const globalRows = flattenMarketGroup(market.global).length
    ? flattenMarketGroup(market.global)
    : DEFAULT_MARKETS.global;
  const commodityRows = flattenMarketGroup(market.commodities).length
    ? flattenMarketGroup(market.commodities)
    : DEFAULT_MARKETS.commodities;
  const fxRows = flattenMarketGroup(market.currencies).length
    ? flattenMarketGroup(market.currencies)
    : DEFAULT_MARKETS.currencies;

  const nextEvent =
    header.next_event?.title ||
    header.next_event?.name ||
    header.next_event?.event ||
    (typeof header.next_event === 'string' ? header.next_event : null) ||
    '—';

  return (
    <div className="io-root">
      <div className="io-shell">
        <header className="io-masthead">
          <div>
            <p className="io-kicker">Admin only · AGI V1.3 · Monitoring only · No BUY / No SELL</p>
            <h1 className="io-greeting mt-2">{header.greeting || 'Good Morning'}</h1>
            <p className="io-date-line">
              {date.weekday || clock.toLocaleDateString('en-GB', { weekday: 'long' })}
              <br />
              {date.day || clock.getUTCDate()} {date.month || clock.toLocaleDateString('en-GB', { month: 'long' })}{' '}
              {date.year || clock.getUTCFullYear()}
            </p>
            <p className="io-title">{header.title || 'Investment Office'}</p>
            <p className="io-subtitle">{header.subtitle || 'Institutional Daily Briefing'}</p>
            <p className="mt-3 max-w-2xl text-sm text-[var(--io-muted)]">
              Morning command center for the research desk. Complements Knowledge Operations without
              duplicating the knowledge pipeline control room.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/" className="io-btn">
                <ArrowLeft className="h-3.5 w-3.5" /> Home
              </Link>
              <Link to="/admin/knowledge-operations" className="io-btn">
                <Library className="h-3.5 w-3.5" /> Knowledge Operations
              </Link>
              <button type="button" className="io-btn primary" onClick={load} disabled={loading}>
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
          <div className="io-meta-grid">
            <Meta label="Current Time" value={clockLabel} />
            <Meta label="Market Countdown" value={header.market_countdown || 'Pre-open'} />
            <Meta label="Next Event" value={nextEvent} />
            <Meta label="Research Queue" value={header.research_queue_count ?? top.research_queue} />
          </div>
        </header>

        {error ? (
          <div className="io-section flex items-start gap-2 border-[var(--io-red)] bg-[var(--io-red-bg)] text-sm text-[var(--io-red)]">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        {desk?.building ? (
          <div className="io-section text-sm text-[var(--io-muted)]">
            Preparing morning snapshot in the background (ICF/IEP/CGL off the request path). This page
            will update automatically.
          </div>
        ) : null}

        <div className="io-summary">
          <Kpi label="Market Mood" value={top.market_mood} />
          <Kpi label="Global Risk" value={top.global_risk} />
          <Kpi label="Research Queue" value={top.research_queue} />
          <Kpi label="Companies Updated Overnight" value={top.companies_updated_overnight} />
          <Kpi label="Reports Refreshed" value={top.reports_refreshed} />
          <Kpi label="Critical Alerts" value={top.critical_alerts} />
          <Kpi label="Macro Events Today" value={top.macro_events_today} />
          <Kpi label="Earnings Today" value={top.earnings_today} />
          <Kpi label="Research Ready" value={top.research_ready} />
          <Kpi label="Institutional Coverage Complete" value={top.institutional_coverage_complete} />
        </div>

        <Section
          id="executive-brief"
          title="Morning Executive Brief"
          lede="Automatically generated every morning from overnight knowledge, markets, and research queue."
          style={{ animationDelay: '0.08s' }}
        >
          <div className="io-brief">
            {(brief.bullets || []).length ? (
              (brief.bullets || []).map((line) => <p key={line}>{line}</p>)
            ) : (
              <p>{brief.narrative || (loading ? 'Preparing briefing…' : 'Desk is quiet this morning.')}</p>
            )}
            <p>
              Estimated analyst workload{' '}
              <strong>{fmt(brief.estimated_workload_hours)} hours</strong>.
            </p>
          </div>
        </Section>

        <div className="io-grid-2">
          <Section
            id="priorities"
            title="Today's Priorities"
            lede="Critical companies requiring analyst attention before the open."
          >
            {priorities.length ? (
              <table className="io-table">
                <thead>
                  <tr>
                    <th>Priority</th>
                    <th>Company</th>
                    <th>Reason</th>
                    <th>Impact</th>
                    <th>ETA</th>
                    <th>Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {priorities.map((p) => (
                    <tr key={`${p.ticker}-${p.reason}`} onClick={() => openCompany(p.ticker)}>
                      <td>
                        <Badge tone={p.priority}>{p.priority || 'Medium'}</Badge>
                      </td>
                      <td>
                        <strong>{p.ticker || p.company}</strong>
                      </td>
                      <td>{p.reason}</td>
                      <td>{p.expected_impact || 'Monitor'}</td>
                      <td>{p.eta_minutes != null ? `${p.eta_minutes} min` : '—'}</td>
                      <td>{p.owner || 'AI'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="io-empty">{loading ? 'Loading priorities…' : 'No critical priorities yet.'}</p>
            )}
          </Section>

          <Section
            id="overnight"
            title="Overnight Activity"
            lede="Timeline of institutional knowledge and corporate updates."
          >
            {overnight.length ? (
              <div className="io-timeline">
                {overnight.map((e, idx) => (
                  <div
                    key={`${e.timestamp || e.time}-${e.ticker}-${idx}`}
                    className="io-timeline-item"
                    onClick={() => openCompany(e.ticker)}
                    onKeyDown={() => {}}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="time">{e.time || '—'}</div>
                    <div className="body">
                      <strong>
                        {e.ticker || e.kind || 'Desk'} · {e.title}
                      </strong>
                      <div className="detail">
                        {e.detail || e.status}
                        {e.research_invalidated ? ' · Research invalidated' : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="io-empty">{loading ? 'Loading overnight timeline…' : 'No overnight events recorded.'}</p>
            )}
          </Section>
        </div>

        <Section
          id="research-queue"
          title="Research Queue"
          lede="Prioritized by impact across review, validation, publication, refresh, evidence, and claim safety."
        >
          <div className="io-stage-row">
            {Object.entries(queue.stages || {}).map(([stage, count]) => (
              <div key={stage} className="io-stage">
                {stage}
                <strong>{count}</strong>
              </div>
            ))}
          </div>
          {(queue.items || []).length ? (
            <table className="io-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Company</th>
                  <th>Priority</th>
                  <th>Reason</th>
                  <th>ETA</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {(queue.items || []).map((it, idx) => (
                  <tr key={`${it.ticker}-${idx}`} onClick={() => openCompany(it.ticker)}>
                    <td>{it.status}</td>
                    <td>
                      <strong>{it.ticker || '—'}</strong>
                    </td>
                    <td>
                      <Badge tone={it.priority}>{it.priority}</Badge>
                    </td>
                    <td>{it.reason || it.title}</td>
                    <td>{it.eta_minutes != null ? `${it.eta_minutes} min` : '—'}</td>
                    <td>
                      <span className="io-linkish">Open Report</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="io-empty">Queue is clear.</p>
          )}
        </Section>

        <Section
          id="opportunities"
          title="Morning Opportunities"
          lede="Companies requiring attention — monitoring only. Not recommendations."
        >
          <div className="io-cards">
            {opportunities.length ? (
              opportunities.map((o) => (
                <button
                  key={`${o.ticker}-${o.reason}`}
                  type="button"
                  className="io-card text-left"
                  onClick={() => openCompany(o.ticker)}
                >
                  <div className="ticker">{o.ticker || '—'}</div>
                  <div className="reason">{o.reason}</div>
                  <div className="meta">
                    Confidence {fmt(o.confidence)} · Affected research {fmt(o.affected_research)}
                  </div>
                  <div className="mt-2">
                    <span className="io-linkish">
                      Open Analysis <ExternalLink className="inline h-3 w-3" />
                    </span>
                  </div>
                </button>
              ))
            ) : (
              <p className="io-empty">No monitoring opportunities flagged.</p>
            )}
          </div>
        </Section>

        <Section
          id="markets"
          title="Market Dashboard"
          lede="Indian markets, global indices, commodities, and currencies. Soft live snapshot."
        >
          <div className="io-markets">
            {[
              ['Indian Markets', indiaRows],
              ['Global', globalRows],
              ['Commodities', commodityRows],
              ['Currencies', fxRows],
            ].map(([label, rows]) => (
              <div key={label} className="io-market-block">
                <h3>{label}</h3>
                {rows.map((r) => (
                  <div key={r.symbol} className="io-market-row">
                    <span className="sym">{r.symbol}</span>
                    <span>{fmt(r.value)}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </Section>

        <div className="io-grid-2">
          <Section id="macro" title="Macro Intelligence" lede="Today's events and economic calendar.">
            {(macro.todays_events || []).length ? (
              <table className="io-table">
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Source</th>
                    <th>Impact</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {(macro.todays_events || []).map((ev, idx) => (
                    <tr key={idx}>
                      <td>
                        <strong>{ev.title || ev.name || ev.event || 'Macro update'}</strong>
                        <div className="text-xs text-[var(--io-muted)]">{ev.summary || ev.detail || ''}</div>
                      </td>
                      <td>{ev.source || ev.region || '—'}</td>
                      <td>
                        <Badge tone={ev.impact || 'medium'}>{ev.impact || 'Medium'}</Badge>
                      </td>
                      <td>
                        <Link className="io-linkish" to="/macro-intelligence">
                          Open Analysis
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="io-empty">
                Sources monitored: {(macro.sources || []).join(' · ') || 'RBI · Fed · ECB · BoJ'}
              </p>
            )}
          </Section>

          <Section
            id="corporate-calendar"
            title="Corporate Calendar"
            lede="Earnings, AGMs, investor days, dividends, and corporate actions."
          >
            {(calendar.earnings_today || []).length ? (
              <table className="io-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Type</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {(calendar.earnings_today || []).slice(0, 12).map((row, idx) => (
                    <tr
                      key={idx}
                      onClick={() => openCompany(row.ticker || row.company)}
                    >
                      <td>
                        <strong>{row.ticker || row.company || row.name || '—'}</strong>
                      </td>
                      <td>{row.type || row.event || 'Earnings'}</td>
                      <td>
                        <span className="io-linkish">Open Research</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="io-empty">No earnings listed for today.</p>
            )}
            <div className="io-stage-row">
              <div className="io-stage">
                Upcoming earnings
                <strong>{(calendar.upcoming_earnings || []).length}</strong>
              </div>
              <div className="io-stage">
                Corporate actions
                <strong>{(calendar.corporate_actions || []).length}</strong>
              </div>
              <div className="io-stage">
                Dividends
                <strong>{(calendar.dividends || []).length}</strong>
              </div>
            </div>
          </Section>
        </div>

        <Section
          id="portfolio"
          title="Portfolio Monitoring"
          lede="Watchlists, stale research, large moves, and news/macro impact. No investment recommendations."
        >
          {(portfolio.companies_requiring_review || []).length ? (
            <div className="io-cards">
              {(portfolio.companies_requiring_review || []).slice(0, 8).map((c, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="io-card text-left"
                  onClick={() => openCompany(c.ticker || c.entity)}
                >
                  <div className="ticker">{c.ticker || c.entity || c.company || 'Watch'}</div>
                  <div className="reason">
                    {Array.isArray(c.reasons) ? c.reasons.join(', ') : c.reason || c.summary || 'Requires review'}
                  </div>
                  <div className="meta">Monitoring only</div>
                </button>
              ))}
            </div>
          ) : (
            <p className="io-empty">No portfolio review alerts.</p>
          )}
        </Section>

        <Section id="sectors" title="Sector Monitoring" lede="Performance, news, research updates, and coverage.">
          <div className="io-cards">
            {(sectors || []).slice(0, 10).map((s, idx) => (
              <div key={idx} className="io-card">
                <div className="ticker">{s.sector || s.name || s.ticker || 'Sector'}</div>
                <div className="reason">
                  Performance {fmt(s.performance)} · News {fmt(s.major_news)} · Updates{' '}
                  {fmt(s.research_updates)}
                </div>
                <div className="meta">
                  Coverage {fmt(s.coverage)} · Companies updated {fmt(s.companies_updated)}
                </div>
              </div>
            ))}
          </div>
        </Section>

        <div className="io-grid-2">
          <Section id="metrics" title="Daily Research Metrics" lede="Publication, refresh, readiness, and latency.">
            <div className="io-summary" style={{ marginTop: '0.85rem' }}>
              <Kpi label="Reports Published" value={metrics.reports_published} />
              <Kpi label="Reports Refreshed" value={metrics.reports_refreshed} />
              <Kpi label="Reports Waiting" value={metrics.reports_waiting} />
              <Kpi label="Research Ready" value={metrics.research_ready} />
              <Kpi label="Claim Safe" value={metrics.claim_safe} />
              <Kpi label="Avg Knowledge Confidence" value={metrics.avg_knowledge_confidence} />
              <Kpi label="Avg Institutional Coverage" value={metrics.avg_institutional_coverage} />
              <Kpi label="Research Latency" value={metrics.research_latency} />
              <Kpi label="Collector Success %" value={metrics.collector_success_pct} />
              <Kpi label="Queue" value={queue.count} />
            </div>
          </Section>

          <Section id="workspace" title="Analyst Workspace" lede="Assigned companies, reviews, and continue working.">
            <div className="io-stage-row">
              {(workspace.assigned_companies || []).map((t) => (
                <button key={t} type="button" className="io-stage" onClick={() => openCompany(t)}>
                  {t}
                </button>
              ))}
            </div>
            <p className="mt-3 text-sm text-[var(--io-muted)]">
              Pending reviews: {(workspace.pending_reviews || []).length} · Notes:{' '}
              {(workspace.notes || []).length} · Drafts: {(workspace.draft_reports || []).length}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link className="io-btn" to="/agi/ask">
                Continue Working
              </Link>
              <Link className="io-btn" to="/admin/knowledge-operations">
                Open Knowledge Ops
              </Link>
            </div>
          </Section>
        </div>

        <Section
          id="investment-calendar"
          title="Investment Calendar"
          lede="Today, this week, upcoming macro and earnings."
        >
          <div className="io-stage-row">
            <div className="io-stage">
              Today <strong>{(invCal.today || []).length}</strong>
            </div>
            <div className="io-stage">
              This week <strong>{(invCal.this_week || []).length}</strong>
            </div>
            <div className="io-stage">
              Macro <strong>{(invCal.macro || []).length}</strong>
            </div>
          </div>
        </Section>

        <Section
          id="ai-summary"
          title="Daily AI Summary"
          lede="Market summary, risks, opportunities to monitor, research priorities, and suggested workflow."
        >
          <div className="io-ai">{ai.text || brief.narrative || (loading ? 'Generating…' : '—')}</div>
          <div className="io-stage-row">
            {(ai.suggested_analyst_workflow || []).map((step) => (
              <div key={step} className="io-stage">
                <Clock className="mr-1 inline h-3 w-3" />
                {step}
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-[var(--io-caption)]">
            Estimated workload {fmt(ai.estimated_workload_hours)} hours · Issues recommendations: never
          </p>
        </Section>

        <div className="io-actions">
          <button type="button" className="io-btn primary" onClick={onRefresh} disabled={!!busy}>
            <RefreshCw className={`h-3.5 w-3.5 ${busy === 'refresh' ? 'animate-spin' : ''}`} />
            Refresh Morning Office
          </button>
          <button type="button" className="io-btn" onClick={onGenerateBrief} disabled={!!busy}>
            <Sparkles className="h-3.5 w-3.5" />
            Run Morning Brief
          </button>
          <Link to="/admin/knowledge-operations" className="io-btn">
            <Library className="h-3.5 w-3.5" /> Open Knowledge Operations
          </Link>
          <a href="#research-queue" className="io-btn">
            Open Research Queue
          </a>
          <Link to="/macro-intelligence" className="io-btn">
            <LineChart className="h-3.5 w-3.5" /> Open Macro Intelligence
          </Link>
          <Link to="/portfolio" className="io-btn">
            <Briefcase className="h-3.5 w-3.5" /> Open Portfolio Office
          </Link>
          <button type="button" className="io-btn" onClick={exportJson}>
            <Download className="h-3.5 w-3.5" /> Download JSON
          </button>
          <button type="button" className="io-btn" onClick={exportCsv}>
            <Download className="h-3.5 w-3.5" /> Export Excel/CSV
          </button>
        </div>

        <p className="mt-4 text-[11px] text-[var(--io-caption)]">
          {desk?.generated_at || '—'} · {desk?.version || 'io-v1.3.0'} · {desk?.workstream_id || 'IO-V1.3'} ·
          Monitoring only
        </p>
      </div>
    </div>
  );
}
