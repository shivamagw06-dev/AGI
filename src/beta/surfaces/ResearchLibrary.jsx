import { Link } from 'react-router-dom';
import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, EmptyState } from '@/beta/components/Cards';
import { useBetaDepth } from '@/beta/BetaDepthContext';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import { useEffect, useState } from 'react';
import { listResearchRuns } from '@/lib/intelligenceApi';

export default function ResearchLibrary() {
  const { isProfessional } = useBetaDepth();
  const { articles, loading } = usePublishedArticles({ limit: 8 });
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    let active = true;
    listResearchRuns({ limit: '10' })
      .then((data) => {
        if (!active) return;
        setRuns(Array.isArray(data) ? data : data?.runs || []);
      })
      .catch(() => active && setRuns([]));
    return () => {
      active = false;
    };
  }, []);

  return (
    <SurfaceChrome>
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">Research Library</p>
          <h1 className="beta-h1 mt-2">Notion calm. McKinsey spine.</h1>
        </header>

        <StorySection title="Published research">
          {loading && <p className="beta-caption">Loading…</p>}
          <div className="grid gap-4 sm:grid-cols-2">
            {(articles || []).map((a) => (
              <Link key={a.id || a.slug} to={a.slug ? `/article/${a.slug}` : '/research'} className="beta-card block hover:border-[var(--beta-navy)]">
                <div className="mb-4 h-28 rounded-xl bg-gradient-to-br from-[#0b1f3a] to-[#344054]" />
                <p className="beta-caption">{a.section || 'Research'}</p>
                <h3 className="mt-1 text-lg font-semibold text-[var(--beta-ink)]">{a.title}</h3>
                <p className="beta-caption mt-2">
                  {a.published_at ? new Date(a.published_at).toLocaleDateString('en-IN') : '—'}
                </p>
              </Link>
            ))}
          </div>
          {!loading && !(articles || []).length && <EmptyState title="No published covers yet" />}
        </StorySection>

        {isProfessional && (
          <StorySection title="Intelligence runs">
            <div className="space-y-3">
              {runs.map((r) => (
                <div key={r.run_id} className="beta-card-quiet">
                  <p className="text-sm font-semibold">{r.desk}</p>
                  <p className="beta-caption mt-1">{r.query || r.run_id}</p>
                  <p className="beta-caption mt-1">
                    {(r.symbols || []).join(', ') || '—'} · {r.status}
                  </p>
                </div>
              ))}
              {!runs.length && <EmptyState title="No intelligence runs stored yet" />}
            </div>
          </StorySection>
        )}
      </div>
    </SurfaceChrome>
  );
}
