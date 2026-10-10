import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, ForecastCard, EmptyState, CompanyCard } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import { listResearchRuns, getResearchRun } from '@/lib/intelligenceApi';
import { buildStoryFromReport } from '@/beta/lib/reportStory';

export default function ForecastsStory() {
  const navigate = useNavigate();
  const { isExplain } = useBetaDepth();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const runs = await listResearchRuns({ limit: '12' });
        const list = Array.isArray(runs) ? runs : runs?.runs || [];
        const detailed = await Promise.all(
          list.slice(0, 6).map(async (r) => {
            try {
              const full = await getResearchRun(r.run_id);
              return { run: full, story: buildStoryFromReport(full?.report, { symbols: full?.symbols || [] }) };
            } catch {
              return { run: r, story: null };
            }
          }),
        );
        if (active) setRows(detailed.filter((d) => d.story?.forecast));
      } catch {
        if (active) setRows([]);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const highest = [...rows].sort((a, b) => (b.story.confidence || 0) - (a.story.confidence || 0));
  const lowest = [...rows].sort((a, b) => (a.story.confidence || 0) - (b.story.confidence || 0));

  return (
    <SurfaceChrome>
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">Forecast Center</p>
          <h1 className="beta-h1 mt-2">Forecasts that earn trust</h1>
        </header>

        <StorySection title="Highest confidence">
          {highest.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {highest.slice(0, isExplain ? 2 : 4).map(({ run, story }) => (
                <CompanyCard
                  key={run.run_id}
                  symbol={(run.symbols || [])[0] || run.desk}
                  confidence={story.confidence}
                  stance={story.stance}
                  why={[story.summary?.slice(0, 120)]}
                  onOpen={() => navigate(`/beta/companies/${(run.symbols || [])[0] || 'RELIANCE'}`)}
                />
              ))}
            </div>
          ) : (
            <EmptyState title="No forecast packages yet" detail="Scenario probabilities appear when CIO notes include bull/base/bear cases." />
          )}
        </StorySection>

        {!isExplain && highest[0]?.story?.forecast && (
          <StorySection title="Scenario detail">
            <div className="grid gap-3 sm:grid-cols-3">
              {['bull', 'base', 'bear'].map((k) => {
                const c = highest[0].story.forecast[k];
                if (!c) return null;
                return <ForecastCard key={k} label={c.label || k} probability={c.probability} detail={c.detail} />;
              })}
            </div>
          </StorySection>
        )}

        {!isExplain && lowest.length > 0 && (
          <StorySection title="Lowest confidence">
            <div className="grid gap-3 sm:grid-cols-2">
              {lowest.slice(0, 2).map(({ run, story }) => (
                <CompanyCard
                  key={run.run_id}
                  symbol={(run.symbols || [])[0] || run.desk}
                  confidence={story.confidence}
                  stance={story.stance}
                />
              ))}
            </div>
          </StorySection>
        )}
      </div>
    </SurfaceChrome>
  );
}
