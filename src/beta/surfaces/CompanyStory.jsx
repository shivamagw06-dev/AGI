import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import {
  StorySection,
  InsightCard,
  MetricStoryCard,
  OpportunityCard,
  RiskCard,
  TimelineCard,
  ForecastCard,
  EvidenceCard,
  EmptyState,
  CompanyCard,
} from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import { buildStoryFromReport, stanceTone, whyFromText } from '@/beta/lib/reportStory';
import { getSimilarCompanies, listResearchRuns, getResearchRun, runAndWait } from '@/lib/intelligenceApi';
import useNifty500Research from '@/hooks/useNifty500Research';

const EQUITY_QUERY = 'Institutional equity research note — business, financials, risks, and catalysts.';

export default function CompanyStory() {
  const { symbol: paramSymbol } = useParams();
  const navigate = useNavigate();
  const symbol = (paramSymbol || 'RELIANCE').toUpperCase();
  const { isExplain, isProfessional } = useBetaDepth();
  const nifty = useNifty500Research();
  const [input, setInput] = useState(symbol);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [run, setRun] = useState(null);
  const [peers, setPeers] = useState([]);

  useEffect(() => {
    setInput(symbol);
  }, [symbol]);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      setRun(null);
      try {
        const runs = await listResearchRuns({ limit: '20' });
        const list = Array.isArray(runs) ? runs : runs?.runs || [];
        const existing = list.find(
          (r) =>
            (r.desk === 'equity' || r.desk === 'cio_morning' || r.desk === 'smoke') &&
            Array.isArray(r.symbols) &&
            r.symbols.map((s) => String(s).toUpperCase()).includes(symbol) &&
            ['completed', 'partial'].includes(r.status),
        );
        let full = existing ? await getResearchRun(existing.run_id) : null;
        if (!full?.report) {
          full = await runAndWait({
            desk: 'equity',
            symbols: [symbol],
            query: `${EQUITY_QUERY} Focus: ${symbol}`,
          });
        }
        if (active) setRun(full);
      } catch (err) {
        if (active) setError(err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [symbol]);

  useEffect(() => {
    let active = true;
    getSimilarCompanies(symbol)
      .then((data) => {
        if (!active) return;
        const list = data?.similar || data?.peers || (Array.isArray(data) ? data : []);
        setPeers(list.map((p) => String(p).toUpperCase()));
      })
      .catch(() => {
        const FALLBACK = {
          RELIANCE: ['ONGC', 'IOC', 'BPCL', 'HPCL'],
          TCS: ['INFY', 'WIPRO', 'HCLTECH', 'TECHM'],
          INFY: ['TCS', 'WIPRO', 'HCLTECH', 'TECHM'],
          TITAN: ['KALYANKJIL', 'SENCO', 'PCJEWELLER'],
          HDFCBANK: ['ICICIBANK', 'AXISBANK', 'KOTAKBANK'],
        };
        if (active) setPeers(FALLBACK[symbol] || []);
      });
    return () => {
      active = false;
    };
  }, [symbol]);

  const niftyRow = useMemo(() => {
    const rows = nifty?.stocks || nifty?.items || nifty?.results || [];
    return rows.find((r) => String(r.symbol || '').toUpperCase() === symbol);
  }, [nifty, symbol]);

  const story = buildStoryFromReport(run?.report, { symbols: [symbol] });
  const tone = stanceTone(story?.stance || niftyRow?.overallSentiment);
  const summary =
    story?.summary ||
    niftyRow?.researchSummary ||
    `${symbol} — research opens when the Intelligence engine is available. AGI never invents numbers to fill a page.`;

  const openSymbol = (e) => {
    e.preventDefault();
    const next = input.trim().toUpperCase();
    if (next) navigate(`/beta/companies/${encodeURIComponent(next)}`);
  };

  return (
    <SurfaceChrome askPlaceholder={`Ask about ${symbol}…`}>
      <form onSubmit={openSymbol} className="mb-2 flex flex-wrap items-center gap-2">
        <input
          className="beta-input max-w-[12rem] py-2.5 text-sm"
          value={input}
          onChange={(e) => setInput(e.target.value.toUpperCase())}
          placeholder="Symbol"
          aria-label="Company symbol"
        />
        <button type="submit" className="beta-btn-ghost beta-btn py-2.5 text-xs">
          Switch
        </button>
      </form>

      {/* Full-bleed editorial hero — brand/company first, one stance, one lede */}
      <header className="beta-hero !min-h-[70vh] !justify-end !pb-10 !pt-16">
        <div className="beta-hero-inner max-w-3xl">
          <p className="beta-kicker beta-fade">Company Intelligence</p>
          <h1 className="beta-display mt-4 beta-rise">{symbol}</h1>
          <div className="mt-6 flex flex-wrap items-center gap-2 beta-rise-delay">
            <span className={`beta-chip beta-chip-${tone === 'pos' ? 'pos' : tone === 'neg' ? 'neg' : 'warn'}`}>
              {story?.stance || niftyRow?.overallSentiment || 'Stance pending'}
            </span>
            {(story?.confidence ?? niftyRow?.agiResearchScore) != null && (
              <span className="beta-chip">
                Confidence {story?.confidence ?? niftyRow?.agiResearchScore}
                {story?.confidence != null ? '%' : ''}
              </span>
            )}
            <span className="beta-chip">{story?.readTime || 5} min read</span>
          </div>
          <p className="beta-lede mt-8 max-w-2xl beta-rise-delay-2">
            {isExplain ? `${summary.slice(0, 200)}${summary.length > 200 ? '…' : ''}` : summary.slice(0, 320)}
            {!isExplain && summary.length > 320 ? '…' : ''}
          </p>
        </div>
      </header>

      {loading && (
        <div className="flex items-center gap-2 py-8 text-sm text-[var(--beta-muted)]">
          <Loader2 className="h-4 w-4 animate-spin" /> Writing the company story…
        </div>
      )}
      {error && !story && (
        <EmptyState title="Equity research unavailable" detail={error.message || 'Showing any published context available.'} />
      )}

      <div className="beta-story-stack mt-6">
        <StorySection chapter="01" title="One Minute Summary">
          <InsightCard lede body={summary} />
          {!isExplain && (story?.takeaways || []).length > 0 && (
            <ul className="mt-8 max-w-xl space-y-3">
              {story.takeaways.slice(0, 4).map((t) => (
                <li key={t} className="flex gap-3 text-[var(--beta-ink-soft)]">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--beta-navy)]" />
                  <span className="leading-relaxed">{t}</span>
                </li>
              ))}
            </ul>
          )}
        </StorySection>

        {!isExplain && (
          <>
            <StorySection chapter="02" title="Business Story">
              {story?.business || niftyRow?.trendAnalysis ? (
                <InsightCard lede body={story?.business || niftyRow?.trendAnalysis} />
              ) : (
                <EmptyState title="Business narrative withheld" detail="Appears when the note includes a company view." />
              )}
            </StorySection>

            <StorySection chapter="03" title="Financial Story">
              {story?.financial ? (
                <MetricStoryCard
                  label="The numbers that matter"
                  to="Narrative"
                  why={whyFromText(story.financial)}
                  meaning={story.financial}
                  watchNext="Can margins stay durable while growth compounds?"
                />
              ) : (
                <EmptyState
                  title="No fabricated financials"
                  detail="When financial_view or cached metrics exist, this becomes Number → Why → Meaning → Watch next."
                />
              )}
            </StorySection>

            <StorySection chapter="04" title="Growth Story">
              {(story?.growth || []).length ? (
                story.growth.map((g) => <OpportunityCard key={g} title={g} />)
              ) : (
                <EmptyState title="No catalysts listed" />
              )}
            </StorySection>

            <StorySection chapter="05" title="Forecast Story">
              {story?.forecast ? (
                <div className="grid gap-4 sm:grid-cols-3">
                  {['bull', 'base', 'bear'].map((key) => {
                    const c = story.forecast[key];
                    if (!c) return null;
                    return <ForecastCard key={key} label={c.label || key} probability={c.probability} detail={c.detail} />;
                  })}
                </div>
              ) : (
                <EmptyState title="No scenario package yet" detail="Bull / base / bear appear when CIO attaches scenarios." />
              )}
            </StorySection>

            <StorySection chapter="06" title="Risk Story">
              <div className="grid gap-4 sm:grid-cols-2">
                {(story?.risks || niftyRow?.riskFactors || []).length ? (
                  (story?.risks || niftyRow?.riskFactors || []).slice(0, 6).map((r) => (
                    <RiskCard key={r} title="Stated risk" items={[r]} level="stated" />
                  ))
                ) : (
                  <EmptyState title="No risks listed" />
                )}
              </div>
            </StorySection>

            <StorySection chapter="07" title="Timeline">
              {(story?.timeline || []).length ? (
                <TimelineCard items={story.timeline} />
              ) : (
                <EmptyState title="No timeline events" />
              )}
            </StorySection>

            <StorySection chapter="08" title="Peers">
              {peers.length ? (
                <>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {peers.slice(0, 4).map((p) => (
                      <CompanyCard key={p} symbol={p} onOpen={() => navigate(`/beta/companies/${encodeURIComponent(p)}`)} />
                    ))}
                  </div>
                  <button
                    type="button"
                    className="beta-btn mt-8"
                    onClick={() =>
                      navigate(`/beta/compare?symbols=${encodeURIComponent([symbol, ...peers].slice(0, 5).join(','))}`)
                    }
                  >
                    Compare vs peers
                  </button>
                </>
              ) : (
                <EmptyState title="No peer set" />
              )}
            </StorySection>

            {isProfessional && (story?.evidence || []).length > 0 && (
              <StorySection chapter="09" title="Sources">
                {story.evidence.slice(0, 8).map((ev) => (
                  <EvidenceCard key={ev.claim} claim={ev.claim} source={`${ev.source_type} · ${ev.source_id}`} />
                ))}
              </StorySection>
            )}
          </>
        )}

        {isExplain && (
          <p className="beta-caption border-t border-[var(--beta-border)] pt-6">
            Switch depth to <strong>Research Report</strong> for the full scroll — business, financials, forecast, risk, peers.
          </p>
        )}
      </div>
    </SurfaceChrome>
  );
}
