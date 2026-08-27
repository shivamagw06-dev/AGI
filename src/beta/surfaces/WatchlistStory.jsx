import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, InsightCard, EmptyState, OpportunityCard } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import useMarketDashboard from '@/hooks/useMarketDashboard';
import { listWatchlists, listResearchRuns } from '@/lib/intelligenceApi';

export default function WatchlistStory() {
  const navigate = useNavigate();
  const { isExplain } = useBetaDepth();
  const dash = useMarketDashboard();
  const [lists, setLists] = useState([]);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    let active = true;
    listWatchlists()
      .then((data) => {
        if (!active) return;
        setLists(Array.isArray(data) ? data : data?.watchlists || []);
      })
      .catch(() => {
        if (active) setLists([]);
      });
    listResearchRuns({ limit: '6' })
      .then((data) => {
        if (!active) return;
        setRecent(Array.isArray(data) ? data : data?.runs || []);
      })
      .catch(() => {
        if (active) setRecent([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const changes = [
    ...(dash.gainers || []).slice(0, 2).map((s) => ({
      symbol: s.symbol || s.name,
      detail: 'Constructive focus in today’s market intelligence.',
    })),
    ...(dash.losers || []).slice(0, 2).map((s) => ({
      symbol: s.symbol || s.name,
      detail: 'Pressure signal — review risk narrative.',
    })),
    ...recent.slice(0, 2).map((r) => ({
      symbol: (r.symbols || [])[0] || r.desk,
      detail: r.query || r.cio_thesis || 'Research updated.',
    })),
  ].slice(0, 6);

  return (
    <SurfaceChrome askPlaceholder="What changed on my watchlist?">
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">Watchlist</p>
          <h1 className="beta-h1 mt-2">Good Morning</h1>
          <p className="mt-3 text-lg text-[var(--beta-ink-soft)]">
            {changes.length ? `${changes.length} things changed` : 'No material changes yet'}
          </p>
        </header>

        <StorySection title="Digest">
          {changes.length ? (
            <div className="space-y-3">
              {changes.slice(0, isExplain ? 3 : 6).map((item, idx) => (
                <InsightCard
                  key={`${item.symbol}-${idx}`}
                  title={item.symbol}
                  body={item.detail}
                >
                  <button
                    type="button"
                    className="beta-btn-ghost beta-btn mt-3"
                    onClick={() => navigate(`/beta/companies/${encodeURIComponent(item.symbol)}`)}
                  >
                    Read →
                  </button>
                </InsightCard>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Quiet session"
              detail="When watchlist monitors or market focus update, material deltas appear as a morning digest."
            />
          )}
        </StorySection>

        {!isExplain && (
          <StorySection title="Lists">
            {lists.length ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {lists.map((wl) => (
                  <OpportunityCard
                    key={wl.watchlist_id || wl.id || wl.name}
                    title={wl.name || 'Watchlist'}
                    detail={`${(wl.symbols || []).length} names`}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="No watchlists from API" detail="Wire Watchlist desk endpoints to populate custom lists." />
            )}
          </StorySection>
        )}
      </div>
    </SurfaceChrome>
  );
}
