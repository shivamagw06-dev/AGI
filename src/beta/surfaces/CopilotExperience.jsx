import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, EvidenceCard, EmptyState, CompanyCard } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import { buildStoryFromReport } from '@/beta/lib/reportStory';
import { copilotChat, runAndWait } from '@/lib/intelligenceApi';

export default function CopilotExperience() {
  const [params] = useSearchParams();
  const initial = params.get('q') || '';
  const [query, setQuery] = useState(initial);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const { isExplain, isProfessional } = useBetaDepth();

  useEffect(() => {
    if (initial) setQuery(initial);
  }, [initial]);

  const ask = async (e) => {
    e?.preventDefault?.();
    const q = query.trim();
    if (!q || running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      try {
        const data = await copilotChat({ message: q, query: q, mode: 'quick_answer' });
        setResult({ kind: 'copilot', data });
      } catch {
        const run = await runAndWait({ desk: 'cio_morning', query: q });
        setResult({ kind: 'run', data: run });
      }
    } catch (err) {
      setError(err);
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    if (initial) ask();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const story =
    result?.kind === 'run' ? buildStoryFromReport(result.data?.report, { symbols: result.data?.symbols || [] }) : null;
  const copilot = result?.kind === 'copilot' ? result.data?.copilot || result.data : null;
  const executive =
    copilot?.executive_answer ||
    copilot?.answer ||
    story?.summary ||
    result?.data?.report?.executive_summary ||
    null;

  return (
    <SurfaceChrome>
      <div className="beta-story-stack">
        <header className="beta-hero !min-h-[52vh] !items-center !justify-center !pb-8 !pt-16 text-center">
          <div className="beta-hero-inner mx-auto max-w-2xl text-center">
            <p className="beta-kicker beta-fade">Copilot</p>
            <h1 className="beta-display mt-4 beta-rise">Ask AGI</h1>
            <p className="beta-lede mx-auto mt-5 max-w-lg beta-rise-delay">
              One question. Evidence-backed answer. No invented analysis.
            </p>
          </div>
        </header>

        <form onSubmit={ask} className="mx-auto w-full max-w-2xl -mt-4">
          <textarea
            className="beta-textarea min-h-[9.5rem] text-lg"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="How will lower oil prices affect Indian paint companies?"
          />
          <button type="submit" className="beta-btn mt-4 w-full sm:w-auto" disabled={running || !query.trim()}>
            {running ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Thinking…
              </>
            ) : (
              'Ask'
            )}
          </button>
        </form>

        {error && <EmptyState title="Could not reach intelligence" detail={error.message} />}

        {executive && (
          <StorySection chapter="Answer" title="Executive Summary">
            <p className="beta-lede max-w-2xl">{executive}</p>
          </StorySection>
        )}

        {!isExplain && story?.forecast && (
          <StorySection title="Scenarios">
            <div className="grid gap-4 sm:grid-cols-3">
              {['bull', 'base', 'bear'].map((key) => {
                const c = story.forecast[key];
                if (!c) return null;
                return (
                  <div key={key} className="beta-panel">
                    <p className="beta-caption capitalize">{c.label || key}</p>
                    <p className="mt-2 font-[family-name:var(--beta-serif)] text-3xl text-[var(--beta-navy)]">{c.probability}%</p>
                    <p className="beta-caption mt-3">{c.detail}</p>
                  </div>
                );
              })}
            </div>
          </StorySection>
        )}

        {!isExplain && (story?.evidence?.length > 0 || (copilot?.evidence || []).length > 0) && (
          <StorySection title="Evidence">
            {(story?.evidence || copilot?.evidence || []).slice(0, isProfessional ? 8 : 4).map((ev, i) => (
              <EvidenceCard
                key={ev.claim || i}
                claim={ev.claim || ev.statement || String(ev)}
                source={ev.source_id || ev.source_type}
              />
            ))}
          </StorySection>
        )}

        {(copilot?.related_companies || story?.symbols || []).length > 0 && (
          <StorySection title="Related companies">
            <div className="grid gap-4 sm:grid-cols-2">
              {(copilot?.related_companies || story?.symbols || []).slice(0, 4).map((sym) => (
                <CompanyCard key={sym} symbol={sym} onOpen={() => window.location.assign(`/beta/companies/${encodeURIComponent(sym)}`)} />
              ))}
            </div>
          </StorySection>
        )}

        {!running && !executive && !error && (
          <EmptyState title="Start with one institutional question" detail="Oil → paints. Private banks. A single name like RELIANCE." />
        )}

        <p className="beta-caption text-center">
          <Link to="/macro-intelligence" className="underline">
            Prefer production Macro Intelligence
          </Link>
        </p>
      </div>
    </SurfaceChrome>
  );
}
