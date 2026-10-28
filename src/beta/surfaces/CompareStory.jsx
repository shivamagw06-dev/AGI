import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import {
  StorySection,
  InsightCard,
  MetricStoryCard,
  RiskCard,
  TimelineCard,
  ForecastCard,
  EmptyState,
  CompanyCard,
} from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import { buildStoryFromReport, whyFromText } from '@/beta/lib/reportStory';
import { runAndWait } from '@/lib/intelligenceApi';

export default function CompareStory() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { isExplain, isProfessional } = useBetaDepth();
  const initial = (params.get('symbols') || 'INFY,TCS,WIPRO')
    .split(/[,|\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean)
    .slice(0, 5);
  const [text, setText] = useState(initial.join('\n'));
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [runs, setRuns] = useState([]);

  const symbols = useMemo(
    () =>
      text
        .split(/[\n,]+/)
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean)
        .slice(0, 5),
    [text],
  );

  const compare = async (e) => {
    e?.preventDefault?.();
    if (symbols.length < 2) {
      setError(new Error('Enter 2–5 symbols to compare.'));
      return;
    }
    setRunning(true);
    setError(null);
    setRuns([]);
    try {
      // No dedicated comparison desk in this engine snapshot — run equity notes per symbol and synthesize relative cards from reports only.
      const settled = await Promise.all(
        symbols.map(async (sym) => {
          try {
            const run = await runAndWait({
              desk: 'equity',
              symbols: [sym],
              query: `Institutional equity research note on ${sym} for relative comparison.`,
            });
            return { symbol: sym, run, story: buildStoryFromReport(run?.report, { symbols: [sym] }) };
          } catch (err) {
            return { symbol: sym, error: err, story: null };
          }
        }),
      );
      setRuns(settled);
    } catch (err) {
      setError(err);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    if (initial.length >= 2) compare();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ranked = useMemo(() => {
    const ok = runs.filter((r) => r.story);
    const byConf = [...ok].sort((a, b) => (b.story.confidence || 0) - (a.story.confidence || 0));
    const byRisk = [...ok].sort((a, b) => (a.story.risks?.length || 0) - (b.story.risks?.length || 0));
    const byGrowth = [...ok].sort((a, b) => (b.story.growth?.length || 0) - (a.story.growth?.length || 0));
    return {
      overall: byConf[0]?.symbol,
      growth: byGrowth[0]?.symbol,
      safest: byRisk[0]?.symbol,
      value: byConf[1]?.symbol || byConf[0]?.symbol,
    };
  }, [runs]);

  return (
    <SurfaceChrome askPlaceholder="Ask why these companies differ…">
      <div className="beta-story-stack">
        <header className="beta-hero !min-h-[42vh] !pb-6 !pt-12">
          <div className="beta-hero-inner">
            <p className="beta-kicker beta-fade">AI Company Comparison</p>
            <h1 className="beta-display mt-3 beta-rise">Why they differ</h1>
            <p className="beta-lede mt-4 max-w-xl beta-rise-delay">
              Not a spreadsheet — relative roles from real research notes only.
            </p>
          </div>
        </header>

        <form onSubmit={compare} className="max-w-xl">
          <label className="beta-caption">Companies (2–5)</label>
          <textarea className="beta-textarea mt-2" value={text} onChange={(e) => setText(e.target.value.toUpperCase())} />
          <button type="submit" className="beta-btn mt-3" disabled={running}>
            {running ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Comparing…
              </>
            ) : (
              'Generate comparison'
            )}
          </button>
          {error && <p className="mt-3 text-sm text-[var(--beta-red)]">{error.message}</p>}
        </form>

        {runs.length > 0 && (
          <StorySection chapter="Verdict" title="Who leads — and why">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Winner', ranked.overall],
                ['Best Growth', ranked.growth],
                ['Best Value', ranked.value],
                ['Safest', ranked.safest],
              ].map(([label, value]) => (
                <div key={label} className="beta-panel text-center">
                  <p className="beta-caption">{label}</p>
                  <p className="mt-3 font-[family-name:var(--beta-serif)] text-3xl font-semibold text-[var(--beta-navy)]">
                    {value || '—'}
                  </p>
                </div>
              ))}
            </div>
            <p className="beta-caption mt-4">
              Roles reflect confidence, catalysts, and risk counts among compared notes — never Buy/Sell/Hold.
            </p>
          </StorySection>
        )}

        {!isExplain &&
          runs.map(({ symbol, story, error: rowErr }) => (
            <StorySection key={symbol} title={symbol}>
              {rowErr && <EmptyState title={`${symbol} failed`} detail={rowErr.message} />}
              {story && (
                <div className="space-y-4">
                  <InsightCard title="One minute" body={story.summary} meta={story.stance} />
                  {!isExplain && story.business && <InsightCard title="Business" body={story.business} />}
                  {story.financial && (
                    <MetricStoryCard
                      label="Financial story"
                      why={whyFromText(story.financial)}
                      meaning={story.financial}
                    />
                  )}
                  {story.forecast && (
                    <div className="grid gap-3 sm:grid-cols-3">
                      {['base', 'bull', 'bear'].map((k) => {
                        const c = story.forecast[k];
                        if (!c) return null;
                        return <ForecastCard key={k} label={c.label || k} probability={c.probability} detail={c.detail} />;
                      })}
                    </div>
                  )}
                  {(story.risks || []).length > 0 && (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {story.risks.slice(0, 4).map((r) => (
                        <RiskCard key={r} title="Risk" items={[r]} />
                      ))}
                    </div>
                  )}
                  {isProfessional && (story.timeline || []).length > 0 && <TimelineCard items={story.timeline} />}
                  <CompanyCard symbol={symbol} stance={story.stance} confidence={story.confidence} onOpen={() => navigate(`/beta/companies/${symbol}`)} />
                </div>
              )}
            </StorySection>
          ))}
      </div>
    </SurfaceChrome>
  );
}
