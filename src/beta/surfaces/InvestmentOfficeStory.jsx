import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, InsightCard, EmptyState } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import {
  packageInvestmentOffice,
  runInvestmentOffice,
  runInvestmentOfficeScenario,
} from '@/lib/intelligenceApi';

const TABS = [
  "Today's Brief",
  'Research Queue',
  'Investment Calendar',
  'Scenario Center',
  'Decision Journal',
  'Knowledge Graph',
  'Playbooks',
  'Portfolio Office',
  'CIO Summary',
];

const SCENARIOS = [
  'What happens if oil reaches $100?',
  'What if RBI cuts rates?',
  'What if inflation rises?',
  'What if China slows?',
];

function PriorityBand({ label, items }) {
  if (!items?.length) return <EmptyState title={`No ${label.toLowerCase()} items`} />;
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <InsightCard
          key={item.item_id || item.title}
          meta={`${item.priority} · confidence ${item.confidence ?? '—'}`}
          title={item.symbol ? `${item.symbol} — ${item.title}` : item.title}
          body={item.reason}
        />
      ))}
    </div>
  );
}

export default function InvestmentOfficeStory() {
  const { isExplain } = useBetaDepth();
  const [tab, setTab] = useState("Today's Brief");
  const [pack, setPack] = useState(null);
  const [run, setRun] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [watchlistText, setWatchlistText] = useState('INFY, RELIANCE, HDFCBANK, TCS, ICICIBANK');

  const queue = pack?.research_queue || [];
  const high = useMemo(() => queue.filter((q) => q.priority === 'high'), [queue]);
  const medium = useMemo(() => queue.filter((q) => q.priority === 'medium'), [queue]);
  const low = useMemo(() => queue.filter((q) => q.priority === 'low'), [queue]);
  const graph = pack?.knowledge_graph || {};
  const brief = pack?.daily_brief || {};

  function payloadFromForm() {
    const watchlist = watchlistText
      .split(/[\s,]+/)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    return {
      query: 'Investment Office daily package',
      watchlist,
      symbols: watchlist,
      portfolio: {
        name: 'Linked model book',
        source: 'model',
        model_id: 'balanced_india',
        client_id: 'io-demo',
      },
      prior_runs: [
        {
          run_id: 'demo_forecast',
          desk: 'equity',
          symbols: ['INFY'],
          metadata: { forecast_changed: true },
          report: { confidence: { score: 38 }, executive_summary: 'Demo prior research' },
          cio_thesis: 'Prior Infosys research with soft confidence.',
        },
      ],
    };
  }

  useEffect(() => {
    let active = true;
    setBusy(true);
    packageInvestmentOffice(payloadFromForm())
      .then((data) => {
        if (active) setPack(data);
      })
      .catch((err) => {
        if (active) setError(err.message || 'Investment Office unavailable');
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshPackage() {
    setBusy(true);
    setError('');
    try {
      const data = await packageInvestmentOffice(payloadFromForm());
      setPack(data);
      setRun(null);
    } catch (err) {
      setError(err.message || 'Package failed');
    } finally {
      setBusy(false);
    }
  }

  async function onCioRun() {
    setBusy(true);
    setError('');
    try {
      const result = await runInvestmentOffice(payloadFromForm());
      setRun(result);
      if (result?.investment_office) setPack(result.investment_office);
      setTab('CIO Summary');
    } catch (err) {
      setError(err.message || 'Investment Office run failed');
    } finally {
      setBusy(false);
    }
  }

  async function onScenario(q) {
    setBusy(true);
    setError('');
    try {
      const result = await runInvestmentOfficeScenario({
        question: q,
        office: payloadFromForm(),
        portfolio: payloadFromForm().portfolio,
      });
      setScenario(result);
      setTab('Scenario Center');
    } catch (err) {
      setError(err.message || 'Scenario failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <SurfaceChrome askPlaceholder="What deserves my attention today?">
      <div className="beta-story-stack">
        <header className="relative overflow-hidden border-b border-[var(--beta-border)] pb-10 pt-2">
          <div
            className="pointer-events-none absolute -left-20 -top-24 h-72 w-72 rounded-full opacity-40"
            style={{ background: 'radial-gradient(circle, rgba(10,30,56,0.14), transparent 70%)' }}
          />
          <div
            className="pointer-events-none absolute right-0 top-0 h-56 w-56 opacity-30"
            style={{ background: 'radial-gradient(circle, rgba(15,122,74,0.16), transparent 68%)' }}
          />
          <p className="beta-kicker relative">Investment Office</p>
          <h1 className="beta-h1 relative mt-3">AGI</h1>
          <p className="relative mt-3 max-w-2xl text-lg text-[var(--beta-ink-soft)]">
            Your AI Chief Investment Officer — what changed, what deserves attention, what to research next.
            Never executes trades.
          </p>
          <div className="relative mt-6 flex flex-wrap gap-3">
            <button type="button" className="beta-btn beta-btn-primary" onClick={onCioRun} disabled={busy}>
              {busy ? 'Working…' : 'Run CIO Summary'}
            </button>
            <button type="button" className="beta-btn beta-btn-ghost" onClick={refreshPackage} disabled={busy}>
              Refresh brief
            </button>
            <Link to="/beta/portfolio" className="beta-btn beta-btn-ghost">
              Open Portfolio Office →
            </Link>
          </div>
        </header>

        {error && (
          <p className="rounded-xl border border-[var(--beta-red)]/30 bg-[var(--beta-red-bg)] px-4 py-3 text-sm text-[var(--beta-red)]">
            {error}
          </p>
        )}

        <StorySection title="Context">
          <label className="beta-caption block">Watchlist / symbols</label>
          <input
            className="mt-2 w-full max-w-xl rounded-xl border border-[var(--beta-border)] bg-white px-3 py-2 text-sm"
            value={watchlistText}
            onChange={(e) => setWatchlistText(e.target.value)}
          />
        </StorySection>

        <div className="flex gap-2 overflow-x-auto pb-1">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              className={`shrink-0 rounded-full border px-3 py-1.5 text-[12px] font-semibold ${
                tab === t
                  ? 'border-[var(--beta-navy)] bg-[var(--beta-navy)] text-white'
                  : 'border-[var(--beta-border)] bg-white text-[var(--beta-ink-soft)]'
              }`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>

        {!pack && !busy && <EmptyState title="No office package" detail="Refresh to build the daily package." />}

        {pack && tab === "Today's Brief" && (
          <StorySection title="Daily CIO Brief">
            <InsightCard title="Executive summary" body={brief.executive_summary} lede />
            <InsightCard
              title="Today's market story"
              body={
                typeof brief.todays_market_story === 'string'
                  ? brief.todays_market_story
                  : brief.todays_market_story?.note || 'Withheld'
              }
            />
            <div className="mt-8 grid gap-8 md:grid-cols-2">
              <div>
                <p className="beta-kicker mb-3">Top opportunities</p>
                {(brief.top_opportunities || []).slice(0, isExplain ? 2 : 4).map((o) => (
                  <InsightCard key={o.title || o.symbol} title={o.title || o.symbol} body={o.reason} meta={`confidence ${o.confidence ?? '—'}`} />
                ))}
              </div>
              <div>
                <p className="beta-kicker mb-3">Top risks</p>
                {(brief.top_risks || []).slice(0, isExplain ? 2 : 4).map((r) => (
                  <InsightCard key={r.title} title={r.title} body={r.reason || r.level} />
                ))}
              </div>
            </div>
            <InsightCard
              title="Research priorities"
              body={(brief.research_priorities || []).join(' · ') || 'None yet'}
            />
            <InsightCard
              title="Forecast changes"
              body={brief.forecast_changes?.note || 'Withheld without Forecast Layer'}
            />
          </StorySection>
        )}

        {pack && tab === 'Research Queue' && (
          <StorySection title="Research Queue">
            <p className="beta-caption mb-6">Automatically prioritised — High / Medium / Low</p>
            <div className="space-y-10">
              <div>
                <p className="beta-kicker mb-3">High priority</p>
                <PriorityBand label="High" items={high} />
              </div>
              <div>
                <p className="beta-kicker mb-3">Medium priority</p>
                <PriorityBand label="Medium" items={medium} />
              </div>
              <div>
                <p className="beta-kicker mb-3">Low priority</p>
                <PriorityBand label="Low" items={low} />
              </div>
            </div>
          </StorySection>
        )}

        {pack && tab === 'Investment Calendar' && (
          <StorySection title="Investment Calendar">
            {(pack.calendar || []).slice(0, isExplain ? 8 : 20).map((ev) => (
              <InsightCard
                key={ev.event_id || ev.title}
                meta={`${ev.category} · ${ev.status}${ev.date ? ` · ${ev.date}` : ''}`}
                title={ev.title}
                body={ev.note || (ev.status === 'withheld' ? 'Date withheld — not invented.' : '')}
              />
            ))}
          </StorySection>
        )}

        {pack && tab === 'Scenario Center' && (
          <StorySection title="Scenario Center">
            <p className="beta-body mb-4 max-w-2xl">
              Reuses Forecast, Portfolio, Macro, and Research. Outcomes are withheld without evidenced engines.
            </p>
            <div className="flex flex-wrap gap-2">
              {SCENARIOS.map((q) => (
                <button key={q} type="button" className="beta-btn beta-btn-ghost" onClick={() => onScenario(q)}>
                  {q}
                </button>
              ))}
            </div>
            {scenario && (
              <div className="mt-6 space-y-4">
                <InsightCard meta={scenario.status} title={scenario.question} body={scenario.disclaimer} />
                <InsightCard title="Assumptions" body={(scenario.assumptions || []).join(' · ')} />
                {(scenario.impact_notes || []).map((n) => (
                  <InsightCard key={n} title="Note" body={n} />
                ))}
              </div>
            )}
          </StorySection>
        )}

        {pack && tab === 'Decision Journal' && (
          <StorySection title="Decision Journal">
            {(pack.decision_journal || []).length ? (
              (pack.decision_journal || []).slice(0, isExplain ? 5 : 16).map((e) => (
                <InsightCard
                  key={e.entry_id}
                  meta={`${e.kind}${e.ts ? ` · ${e.ts}` : ''}`}
                  title={e.title}
                  body={e.detail}
                />
              ))
            ) : (
              <EmptyState title="Journal empty" detail="Prior research runs will appear here." />
            )}
            {(pack.research_timeline || []).length > 0 && (
              <div className="mt-10">
                <p className="beta-kicker mb-4">Research timeline</p>
                {(pack.research_timeline || []).map((t) => (
                  <InsightCard key={t.period} meta={t.period} title={t.label} body={(t.events || []).join(' · ')} />
                ))}
              </div>
            )}
          </StorySection>
        )}

        {pack && tab === 'Knowledge Graph' && (
          <StorySection title="Market Knowledge Graph">
            <p className="beta-caption mb-4">
              {(graph.nodes || []).length} nodes · {(graph.edges || []).length} edges — {graph.note}
            </p>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <p className="beta-kicker mb-3">Nodes</p>
                {(graph.nodes || []).slice(0, isExplain ? 8 : 18).map((n) => (
                  <InsightCard key={n.node_id} meta={n.kind} title={n.label} body={n.node_id} />
                ))}
              </div>
              <div>
                <p className="beta-kicker mb-3">Relationships</p>
                {(graph.edges || []).slice(0, isExplain ? 8 : 18).map((e, idx) => (
                  <InsightCard
                    key={`${e.source}-${e.target}-${idx}`}
                    title={e.relation}
                    body={`${e.source} → ${e.target}`}
                  />
                ))}
              </div>
            </div>
          </StorySection>
        )}

        {pack && tab === 'Playbooks' && (
          <StorySection title="Investment Playbooks">
            {(pack.playbooks || []).map((pb) => (
              <InsightCard
                key={pb.id}
                meta="Playbook"
                title={pb.title}
                body={`${pb.industry_overview} KPIs: ${(pb.kpis || []).slice(0, 4).join(', ')}. Leaders: ${(pb.leading_companies || []).join(', ')}.`}
              />
            ))}
          </StorySection>
        )}

        {pack && tab === 'Portfolio Office' && (
          <StorySection title="Portfolio Office">
            <InsightCard
              title={pack.portfolio_office_link?.name || 'Portfolio link'}
              body={
                pack.portfolio_office_link?.status === 'attached'
                  ? `Health ${pack.portfolio_office_link.health_score ?? '—'} · ${pack.portfolio_office_link.recommendation_count ?? 0} recommendations`
                  : pack.portfolio_office_link?.note || 'Not attached'
              }
            />
            <Link to="/beta/portfolio" className="beta-btn beta-btn-primary mt-4 inline-flex">
              Open Portfolio Office
            </Link>
          </StorySection>
        )}

        {pack && tab === 'CIO Summary' && (
          <StorySection title="CIO Summary">
            {run?.report?.executive_summary || run?.cio_thesis ? (
              <InsightCard
                meta={`Status ${run.status} · confidence ${run.report?.confidence?.score ?? '—'}`}
                title={run.report?.title || 'Investment Office CIO'}
                body={run.report?.executive_summary || run.cio_thesis}
                lede
              />
            ) : (
              <EmptyState title="No CIO run yet" detail="Click Run CIO Summary to synthesize." />
            )}
            {(run?.report?.action_items || []).map((item) => (
              <p key={item} className="border-t border-[var(--beta-border)] pt-2 text-sm">
                {item}
              </p>
            ))}
          </StorySection>
        )}

        {isExplain && pack?.components_reused?.length > 0 && (
          <StorySection title="Orchestrates">
            <p className="beta-body max-w-3xl">{pack.components_reused.join(' · ')}</p>
          </StorySection>
        )}
      </div>
    </SurfaceChrome>
  );
}
