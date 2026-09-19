import { Link } from 'react-router-dom';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, InsightCard, EmptyState } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import useMarketIntelligence from '@/hooks/useMarketIntelligence';

export default function MarketsStory() {
  const { isExplain } = useBetaDepth();
  const { pulse, outlook, sectors = [], stocksInFocus = [], loading } = useMarketIntelligence();

  const cards = (sectors || []).slice(0, isExplain ? 3 : 8);

  return (
    <SurfaceChrome>
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">Market Intelligence</p>
          <h1 className="beta-h1 mt-2">What happened. Why. Who is affected.</h1>
          <p className="mt-3 max-w-2xl text-[var(--beta-ink-soft)]">{outlook || pulse || 'Session context loads with market intelligence.'}</p>
        </header>

        <StorySection title="Session pulse">
          <InsightCard title="Market pulse" body={pulse || (loading ? 'Loading…' : 'No pulse yet.')} meta="Live context" />
        </StorySection>

        <StorySection title="Stories">
          {cards.length ? (
            <div className="space-y-4">
              {cards.map((s) => (
                <article key={s.name || s.sector} className="beta-card">
                  <p className="beta-kicker">{s.name || s.sector}</p>
                  <h3 className="beta-h3 mt-2">What happened?</h3>
                  <p className="beta-body mt-2">{s.summary || s.note || s.bias || s.trend || 'Sector in focus.'}</p>
                  <h3 className="beta-h3 mt-5">Why?</h3>
                  <p className="beta-body mt-2">{s.reason || s.drivers || outlook || 'See full market intelligence for drivers.'}</p>
                  <h3 className="beta-h3 mt-5">Market impact</h3>
                  <p className="beta-body mt-2">{s.impact || s.sentiment || s.bias || '—'}</p>
                  {!isExplain && (
                    <>
                      <h3 className="beta-h3 mt-5">Companies affected</h3>
                      <p className="beta-caption mt-2">
                        {(stocksInFocus || [])
                          .slice(0, 4)
                          .map((x) => x.symbol || x.name)
                          .filter(Boolean)
                          .join(' · ') || 'Open company intelligence for named exposure.'}
                      </p>
                    </>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No sector stories yet" detail="Market intelligence populates these narrative cards." />
          )}
        </StorySection>

        <Link to="/market-intelligence" className="beta-btn-ghost beta-btn inline-flex">
          Open full Market Intelligence →
        </Link>
      </div>
    </SurfaceChrome>
  );
}
