import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, CompanyCard, EmptyState } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import useNifty500Research from '@/hooks/useNifty500Research';
import useMarketDashboard from '@/hooks/useMarketDashboard';

export default function ScreenerStory() {
  const navigate = useNavigate();
  const { isExplain } = useBetaDepth();
  const nifty = useNifty500Research();
  const dash = useMarketDashboard();
  const [query, setQuery] = useState('Find companies with improving research scores and constructive stance.');

  const picks = useMemo(() => {
    const fromNifty = (nifty?.stocks || nifty?.topBullish || nifty?.leaders || []).slice(0, 8);
    if (fromNifty.length) return fromNifty;
    return (dash.stocksInFocus || []).slice(0, 8);
  }, [nifty, dash.stocksInFocus]);

  return (
    <SurfaceChrome askPlaceholder="Describe a screen…">
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">AI Screener</p>
          <h1 className="beta-h1 mt-2">Today&apos;s most interesting companies</h1>
          <p className="mt-3 max-w-2xl text-[var(--beta-ink-soft)]">
            Cards first. Filters second. Each card answers why it made the list.
          </p>
        </header>

        <StorySection>
          {picks.length ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {picks.slice(0, isExplain ? 3 : 8).map((row) => {
                const symbol = row.symbol || row.ticker || row.name;
                const why = [
                  row.researchSummary,
                  row.overallSentiment && `Stance: ${row.overallSentiment}`,
                  row.agiResearchScore != null && `Research score ${row.agiResearchScore}`,
                  row.trend && `Trend ${row.trend}`,
                  row.reason,
                ].filter(Boolean);
                return (
                  <CompanyCard
                    key={symbol}
                    symbol={symbol}
                    stance={row.overallSentiment || row.trend}
                    confidence={row.agiResearchScore}
                    why={why}
                    onOpen={() => navigate(`/beta/companies/${encodeURIComponent(symbol)}`)}
                  />
                );
              })}
            </div>
          ) : (
            <EmptyState
              title="No interesting names yet"
              detail="When Nifty 500 research or market focus loads, cards appear here with why bullets."
            />
          )}
        </StorySection>

        <StorySection title="Create custom screen">
          <div className="beta-card">
            <textarea
              className="beta-textarea"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Growth + rising ROCE + forecast upgrade…"
            />
            <button
              type="button"
              className="beta-btn mt-3"
              onClick={() => navigate(`/beta/copilot?q=${encodeURIComponent(query)}`)}
            >
              Run with Copilot
            </button>
            <p className="beta-caption mt-3">
              Custom screens route through Copilot / Screener desks when available — this beta does not invent ranked financials.
            </p>
          </div>
        </StorySection>
      </div>
    </SurfaceChrome>
  );
}
