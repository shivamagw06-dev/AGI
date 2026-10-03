import { useEffect, useMemo, useState } from 'react';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, InsightCard, EmptyState } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import {
  normalizePortfolio,
  runPortfolioOffice,
  runPortfolioScenario,
} from '@/lib/intelligenceApi';

const TABS = [
  'Overview',
  'Portfolio',
  'Research',
  'Forecast',
  'Risk',
  'Events',
  'Action Center',
  'Timeline',
  'Reports',
  'CIO Summary',
];

const SAMPLE_CSV = `symbol,weight,sector
RELIANCE,0.18,Energy
TCS,0.16,IT
HDFCBANK,0.22,Banks
INFY,0.14,IT
ICICIBANK,0.18,Banks
ITC,0.12,FMCG`;

const SCENARIO_PROMPTS = [
  'What happens if oil rises 20%?',
  'What happens if RBI cuts rates?',
  'What happens if the IT sector falls?',
  'What happens if inflation increases?',
  'What happens if I reduce Banking exposure?',
];

function ScoreTile({ label, value, note }) {
  return (
    <div className="border-t border-[var(--beta-border)] pt-4">
      <p className="beta-kicker">{label}</p>
      <p className="beta-metric-hero mt-2">{value != null ? value : '—'}</p>
      {note && <p className="beta-caption mt-2 max-w-[14rem]">{note}</p>}
    </div>
  );
}

function PriorityList({ items, empty }) {
  if (!items?.length) return <EmptyState title={empty} detail="No items in this priority band." />;
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <InsightCard
          key={item.id || item.recommendation_id || item.title}
          meta={`${item.priority || ''} · ${item.verb || 'Review'} · confidence ${item.confidence ?? '—'}`}
          title={item.title}
          body={item.reason}
        />
      ))}
    </div>
  );
}

export default function PortfolioOfficeStory() {
  const { isExplain } = useBetaDepth();
  const [tab, setTab] = useState('Overview');
  const [view, setView] = useState('client'); // client | advisor
  const [csvText, setCsvText] = useState(SAMPLE_CSV);
  const [source, setSource] = useState('csv');
  const [modelId, setModelId] = useState('balanced_india');
  const [name, setName] = useState('Client Portfolio');
  const [pack, setPack] = useState(null);
  const [run, setRun] = useState(null);
  const [scenarioQ, setScenarioQ] = useState(SCENARIO_PROMPTS[0]);
  const [scenario, setScenario] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const action = pack?.action_center || {};
  const health = pack?.health_summary || {};
  const sectors = useMemo(() => Object.entries(pack?.sector_exposure || {}), [pack]);

  useEffect(() => {
    let active = true;
    setBusy(true);
    normalizePortfolio({
      name: 'Balanced India (model)',
      source: 'model',
      model_id: 'balanced_india',
      client_id: 'demo-client',
    })
      .then((data) => {
        if (active) setPack(data);
      })
      .catch((err) => {
        if (active) setError(err.message || 'Portfolio Office unavailable');
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function onIngest(e) {
    e?.preventDefault?.();
    setBusy(true);
    setError('');
    try {
      const payload =
        source === 'model'
          ? { name, source: 'model', model_id: modelId, client_id: 'demo-client' }
          : source === 'csv'
            ? { name, source: 'csv', csv_text: csvText, client_id: 'demo-client' }
            : {
                name,
                source: 'manual',
                client_id: 'demo-client',
                holdings: [
                  { symbol: 'HDFCBANK', weight: 0.35, sector: 'Banks' },
                  { symbol: 'TCS', weight: 0.35, sector: 'IT' },
                  { symbol: 'RELIANCE', weight: 0.3, sector: 'Energy' },
                ],
              };
      const data = await normalizePortfolio(payload);
      setPack(data);
      setRun(null);
      setTab('Overview');
    } catch (err) {
      setError(err.message || 'Ingest failed');
    } finally {
      setBusy(false);
    }
  }

  async function onCioRun() {
    if (!pack) return;
    setBusy(true);
    setError('');
    try {
      const payload = {
        name: pack.portfolio?.name || name,
        source: pack.portfolio?.source || source,
        client_id: pack.portfolio?.client_id || 'demo-client',
        model_id: source === 'model' ? modelId : undefined,
        csv_text: source === 'csv' ? csvText : undefined,
        holdings: pack.portfolio?.holdings || [],
      };
      const result = await runPortfolioOffice(payload);
      setRun(result);
      if (result?.portfolio) setPack(result.portfolio);
      setTab('CIO Summary');
    } catch (err) {
      setError(err.message || 'Portfolio Office run failed');
    } finally {
      setBusy(false);
    }
  }

  async function onScenario(q) {
    const question = q || scenarioQ;
    setScenarioQ(question);
    setBusy(true);
    setError('');
    try {
      const result = await runPortfolioScenario({
        question,
        portfolio: {
          name: pack?.portfolio?.name || name,
          source: pack?.portfolio?.source || 'model',
          model_id: modelId,
          holdings: pack?.portfolio?.holdings || [],
          csv_text: source === 'csv' ? csvText : undefined,
        },
      });
      setScenario(result);
    } catch (err) {
      setError(err.message || 'Scenario failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <SurfaceChrome askPlaceholder="What should I review in this portfolio?">
      <div className="beta-story-stack">
        <header className="relative overflow-hidden rounded-[1.5rem] border border-[var(--beta-border)] bg-gradient-to-br from-[#0a1e38] via-[#163456] to-[#0f7a4a]/px-6 py-10 text-white sm:px-10">
          <div
            className="pointer-events-none absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.18), transparent 40%), radial-gradient(circle at 80% 0%, rgba(15,122,74,0.35), transparent 45%)',
            }}
          />
          <p className="relative text-[11px] font-bold uppercase tracking-[0.22em] text-white/70">
            Portfolio Office
          </p>
          <h1 className="relative mt-3 font-[family-name:var(--beta-serif)] text-[clamp(2.2rem,5vw,3.4rem)] font-semibold leading-[1.05] tracking-tight">
            AGI
          </h1>
          <p className="relative mt-3 max-w-xl text-lg text-white/85">
            Continuously evaluate portfolios. Research-backed recommendations — never trade execution.
          </p>
          <div className="relative mt-6 flex flex-wrap gap-3">
            <button type="button" className="beta-btn beta-btn-primary" onClick={onCioRun} disabled={busy || !pack}>
              {busy ? 'Working…' : 'Run CIO Summary'}
            </button>
            <button
              type="button"
              className={`beta-btn ${view === 'client' ? 'beta-btn-primary' : 'beta-btn-ghost'}`}
              onClick={() => setView('client')}
            >
              Client
            </button>
            <button
              type="button"
              className={`beta-btn ${view === 'advisor' ? 'beta-btn-primary' : 'beta-btn-ghost'}`}
              onClick={() => setView('advisor')}
            >
              Advisor
            </button>
          </div>
        </header>

        {error && (
          <p className="rounded-xl border border-[var(--beta-red)]/30 bg-[var(--beta-red-bg)] px-4 py-3 text-sm text-[var(--beta-red)]">
            {error}
          </p>
        )}

        <StorySection title="Ingest">
          <form onSubmit={onIngest} className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {['csv', 'model', 'manual'].map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`beta-btn ${source === s ? 'beta-btn-primary' : 'beta-btn-ghost'}`}
                  onClick={() => setSource(s)}
                >
                  {s === 'csv' ? 'CSV Upload' : s === 'model' ? 'Model Portfolio' : 'Manual Holdings'}
                </button>
              ))}
            </div>
            <input
              className="w-full max-w-md rounded-xl border border-[var(--beta-border)] bg-white px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Portfolio name"
            />
            {source === 'csv' && (
              <textarea
                className="min-h-[140px] w-full rounded-xl border border-[var(--beta-border)] bg-white px-3 py-2 font-mono text-xs"
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
              />
            )}
            {source === 'model' && (
              <select
                className="rounded-xl border border-[var(--beta-border)] bg-white px-3 py-2 text-sm"
                value={modelId}
                onChange={(e) => setModelId(e.target.value)}
              >
                <option value="balanced_india">balanced_india</option>
                <option value="quality_compounders">quality_compounders</option>
              </select>
            )}
            {source === 'manual' && (
              <p className="beta-caption">Uses a small demo manual book (Banks / IT / Energy).</p>
            )}
            <button type="submit" className="beta-btn beta-btn-primary" disabled={busy}>
              Normalize portfolio
            </button>
          </form>
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

        {!pack && !busy && <EmptyState title="No portfolio loaded" detail="Ingest CSV, model, or manual holdings." />}

        {pack && tab === 'Overview' && (
          <>
            <StorySection title="Portfolio Health">
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
                <ScoreTile label="Health" value={pack.health_score} />
                <ScoreTile label="Research" value={pack.research_score} note="Withheld when no child research" />
                <ScoreTile label="Forecast" value={pack.forecast_score} note="Forecast Layer unavailable" />
                <ScoreTile label="Risk" value={pack.risk_score} note="Not fabricated" />
                <ScoreTile label="Diversification" value={pack.diversification_score} />
              </div>
              <p className="beta-lede mt-8 max-w-3xl">{health.portfolio_health}</p>
            </StorySection>

            {view === 'client' ? (
              <StorySection title="Client dashboard">
                <InsightCard
                  title="Today’s changes"
                  body="Withheld until a prior-day baseline is stored — AGI does not invent daily deltas."
                />
                <InsightCard
                  meta="Action Center"
                  title={`${(action.high || []).length} high · ${(action.medium || []).length} medium · ${(action.low || []).length} low`}
                  body="Open the Action Center tab for research priorities."
                />
              </StorySection>
            ) : (
              <StorySection title="Advisor dashboard">
                <InsightCard
                  title="Clients requiring review"
                  body={
                    (pack.advisor_dashboard?.clients_requiring_review || []).join(', ') ||
                    'None flagged high priority.'
                  }
                />
                <InsightCard
                  title="Portfolio health ranking"
                  body={`Health ${pack.health_score ?? '—'} · ${pack.portfolio?.name || name}`}
                />
              </StorySection>
            )}
          </>
        )}

        {pack && tab === 'Portfolio' && (
          <StorySection title="Holdings">
            <div className="space-y-3">
              {(pack.portfolio?.holdings || []).map((h) => (
                <InsightCard
                  key={h.symbol}
                  meta={h.sector || 'Unclassified'}
                  title={h.symbol}
                  body={`Weight ${(Number(h.weight || 0) * 100).toFixed(1)}%${h.name ? ` · ${h.name}` : ''}`}
                />
              ))}
            </div>
            <div className="mt-8">
              <p className="beta-kicker">Sector exposure</p>
              <ul className="mt-4 space-y-2">
                {sectors.map(([sector, weight]) => (
                  <li key={sector} className="flex justify-between border-t border-[var(--beta-border)] pt-2 text-sm">
                    <span>{sector}</span>
                    <span className="font-semibold">{(weight * 100).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </StorySection>
        )}

        {pack && tab === 'Research' && (
          <StorySection title="Holding research">
            {(pack.holding_research || []).length ? (
              (pack.holding_research || []).slice(0, isExplain ? 4 : 12).map((row) => (
                <InsightCard
                  key={row.symbol}
                  meta={row.missing ? 'Deferred' : `Confidence ${row.confidence}`}
                  title={row.symbol}
                  body={row.note || row.thesis || 'Research package'}
                />
              ))
            ) : (
              <EmptyState title="No research rows" />
            )}
          </StorySection>
        )}

        {pack && tab === 'Forecast' && (
          <StorySection title="Forecast">
            <EmptyState
              title="Forecast Score withheld"
              detail="Reuse Forecast Layer when available — Portfolio Office does not invent forecasts."
            />
          </StorySection>
        )}

        {pack && tab === 'Risk' && (
          <StorySection title="Risk">
            <InsightCard
              title="Risk Score withheld"
              body="Quantitative risk is not fabricated. Diversification and sector concentration are packaged from stated weights."
            />
            <InsightCard
              title={`Diversification ${pack.diversification_score ?? '—'}`}
              body={health.weaknesses?.[0] || 'Review sector concentration in Action Center.'}
            />
          </StorySection>
        )}

        {pack && tab === 'Events' && (
          <StorySection title="Upcoming events">
            <EmptyState
              title="Events withheld"
              detail="Corporate calendar not wired in this build — monitoring detectors are scaffolded only."
            />
          </StorySection>
        )}

        {pack && tab === 'Action Center' && (
          <StorySection title="Advisor Action Center">
            <p className="beta-caption mb-6">High · Medium · Low — Review / Research / Monitor language only.</p>
            <div className="space-y-10">
              <div>
                <p className="beta-kicker mb-3">High priority</p>
                <PriorityList items={action.high} empty="No high-priority items" />
              </div>
              <div>
                <p className="beta-kicker mb-3">Medium priority</p>
                <PriorityList items={action.medium} empty="No medium-priority items" />
              </div>
              <div>
                <p className="beta-kicker mb-3">Low priority</p>
                <PriorityList items={action.low} empty="No low-priority items" />
              </div>
            </div>
          </StorySection>
        )}

        {pack && tab === 'Timeline' && (
          <StorySection title="Timeline">
            {(pack.timeline || []).map((point, idx) => (
              <InsightCard
                key={`${point.label}-${idx}`}
                meta={point.ts || 'as of'}
                title={point.label}
                body={point.note}
              />
            ))}
            <p className="beta-caption mt-4">
              Compare Last Week / Month / Quarter / Year requires stored history — currently withheld.
            </p>
          </StorySection>
        )}

        {pack && tab === 'Reports' && (
          <StorySection title="Monthly report">
            <InsightCard
              title="Executive summary"
              body={pack.monthly_report?.executive_summary}
              lede
            />
            <InsightCard
              title="Research outstanding"
              body={(pack.monthly_report?.research_outstanding || []).join(', ') || 'None listed'}
            />
            <InsightCard
              title="Recommendations"
              body={`${(pack.monthly_report?.recommendations || []).length} packaged for this period`}
            />
          </StorySection>
        )}

        {pack && tab === 'CIO Summary' && (
          <StorySection title="CIO Summary">
            {run?.report?.executive_summary || run?.cio_thesis ? (
              <InsightCard
                meta={`Status ${run.status} · confidence ${run.report?.confidence?.score ?? '—'}`}
                title={run.report?.title || 'Portfolio Office CIO'}
                body={run.report?.executive_summary || run.cio_thesis}
                lede
              />
            ) : (
              <EmptyState
                title="No CIO run yet"
                detail="Click Run CIO Summary to synthesize via Research Director + CIO Committee."
              />
            )}
            {(run?.report?.action_items || []).length > 0 && (
              <ul className="mt-6 space-y-2">
                {run.report.action_items.map((item) => (
                  <li key={item} className="border-t border-[var(--beta-border)] pt-2 text-sm">
                    {item}
                  </li>
                ))}
              </ul>
            )}
          </StorySection>
        )}

        <StorySection title="Scenario analysis">
          <p className="beta-body mb-4 max-w-2xl">
            Ask macro or allocation questions. Outcomes are withheld unless Forecast / Macro engines can
            answer — assumptions are always explained.
          </p>
          <div className="flex flex-wrap gap-2">
            {SCENARIO_PROMPTS.map((q) => (
              <button key={q} type="button" className="beta-btn beta-btn-ghost" onClick={() => onScenario(q)}>
                {q}
              </button>
            ))}
          </div>
          {scenario && (
            <div className="mt-6 space-y-4">
              <InsightCard meta={scenario.status} title={scenario.question} body={scenario.disclaimer} />
              <InsightCard
                title="Assumptions"
                body={(scenario.assumptions || []).join(' · ')}
              />
              {(scenario.impact_notes || []).map((note) => (
                <InsightCard key={note} title="Note" body={note} />
              ))}
            </div>
          )}
        </StorySection>

        {isExplain && pack?.withheld?.length > 0 && (
          <StorySection title="Quality rails">
            <ul className="space-y-2 text-sm text-[var(--beta-ink-soft)]">
              {pack.withheld.map((w) => (
                <li key={w} className="border-t border-[var(--beta-border)] pt-2">
                  Withheld — {w}
                </li>
              ))}
            </ul>
          </StorySection>
        )}
      </div>
    </SurfaceChrome>
  );
}
