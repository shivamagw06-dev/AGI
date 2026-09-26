import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { useIntelligenceEntity } from '@/hooks/useIntelligencePlatform';
import KnowledgeGraph from '@/components/intelligence/KnowledgeGraph';
import EntityIntelligencePanel from '@/components/intelligence/EntityIntelligencePanel';
import EntityTimeline from '@/components/intelligence/EntityTimeline';
import EntityCard from '@/components/intelligence/EntityCard';
import '@/components/private-equity/editorial/peEditorial.css';

function RelatedSection({ title, items }) {
  if (!items?.length) return null;
  return (
    <section className="mb-10">
      <h2 className="font-serif text-2xl font-semibold mb-5">{title}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.slice(0, 6).map((item) => (
          <EntityCard key={item.id} entity={item} />
        ))}
      </div>
    </section>
  );
}

export default function IntelligenceEntityPage() {
  const { slug } = useParams();
  const { data, loading, error } = useIntelligenceEntity(slug, { full: true });
  const entity = data?.entity;

  if (loading) {
    return (
      <div className="pe-editorial pe-loading py-24 text-center text-[var(--pe-muted)]">
        Loading entity intelligence…
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="pe-editorial pe-editorial-inner py-16">
        <Link to="/private-markets" className="inline-flex items-center gap-2 text-sm text-[var(--pe-accent)] no-underline mb-6">
          <ArrowLeft size={16} /> Private Markets Intelligence
        </Link>
        <p>Entity not found.</p>
      </div>
    );
  }

  const meta = entity.metadata || {};
  const typeLabel = entity.entity_type.replace(/_/g, ' ');
  const related = data.related || {};

  return (
    <div className="pe-editorial">
      <Helmet>
        <title>{entity.name} | Private Markets Intelligence | AGI</title>
      </Helmet>
      <div className="pe-editorial-inner py-10">
        <Link to="/private-markets" className="inline-flex items-center gap-2 text-sm text-[var(--pe-muted)] no-underline mb-8 hover:text-[var(--pe-accent)]">
          <ArrowLeft size={16} /> Private Markets Intelligence
        </Link>

        {/* Hero */}
        <section className="pe-card p-6 md:p-10 mb-8">
          <div className="flex flex-wrap items-start gap-6">
            {meta.logo ? (
              <img src={meta.logo} alt="" className="w-16 h-16 rounded object-contain bg-[#f5f5f5] p-2" />
            ) : (
              <div className="w-16 h-16 rounded bg-[var(--pe-accent)] text-white flex items-center justify-center font-serif text-2xl font-semibold">
                {entity.name[0]}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="pe-tag capitalize">{typeLabel}</p>
              <h1 className="font-serif text-3xl md:text-4xl font-semibold mt-2">{entity.name}</h1>
              {entity.description && (
                <p className="text-[var(--pe-muted)] text-lg mt-3 max-w-2xl leading-relaxed">{entity.description}</p>
              )}
              {entity.tags?.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-4">
                  {entity.tags.slice(0, 8).map((tag) => (
                    <span key={tag} className="pe-tag border border-[var(--pe-border)] px-2 py-1">{tag}</span>
                  ))}
                </div>
              )}
            </div>
            {data.intelligence && (
              <div className="text-right">
                <div className="text-3xl font-semibold text-[var(--pe-accent)]">{data.intelligence.score}</div>
                <div className="text-xs uppercase tracking-wider text-[var(--pe-muted)] mt-1">Intelligence Score</div>
                <div className="text-sm text-[var(--pe-muted)] mt-1">{data.intelligence.label}</div>
              </div>
            )}
          </div>
        </section>

        {/* AI Summary */}
        {entity.ai_summary && (
          <section className="pe-card p-6 md:p-8 mb-8 border-l-4 border-l-[var(--pe-accent)]">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--pe-accent)] mb-3">
              AI Intelligence Summary
            </p>
            <p className="text-base leading-relaxed text-[var(--pe-text)]">{entity.ai_summary}</p>
            {entity.ai_summary_updated_at && (
              <p className="text-xs text-[var(--pe-muted)] mt-4">
                Updated {new Date(entity.ai_summary_updated_at).toLocaleDateString()}
              </p>
            )}
          </section>
        )}

        {/* Knowledge Graph + Panel */}
        <section className="mb-10">
          <h2 className="font-serif text-2xl font-semibold mb-5">Knowledge Graph</h2>
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
            <KnowledgeGraph entitySlug={entity.slug} entityId={entity.id} />
            <EntityIntelligencePanel
              entity={entity}
              intelligence={data.intelligence}
              related={related}
              timeline={data.timeline}
              lastRefresh={data.last_refresh}
            />
          </div>
        </section>

        {/* Timeline */}
        <section className="pe-card p-6 md:p-8 mb-10">
          <EntityTimeline events={data.timeline} />
        </section>

        {/* Overview */}
        <section className="pe-card p-6 md:p-8 mb-10">
          <h2 className="font-serif text-2xl font-semibold mb-4">Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {meta.aum && <div><p className="text-[10px] uppercase text-[var(--pe-muted)]">AUM</p><p className="font-semibold text-lg">{meta.aum}</p></div>}
            {meta.hq && <div><p className="text-[10px] uppercase text-[var(--pe-muted)]">HQ</p><p className="font-semibold text-lg">{meta.hq}</p></div>}
            {meta.founded && <div><p className="text-[10px] uppercase text-[var(--pe-muted)]">Founded</p><p className="font-semibold text-lg">{meta.founded}</p></div>}
            {meta.status && <div><p className="text-[10px] uppercase text-[var(--pe-muted)]">Status</p><p className="font-semibold text-lg">{meta.status}</p></div>}
          </div>
          {meta.website && (
            <a
              href={meta.website.startsWith('http') ? meta.website : `https://${meta.website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-[var(--pe-accent)] mt-6 no-underline hover:underline"
            >
              Website <ExternalLink size={14} />
            </a>
          )}
        </section>

        <RelatedSection title="Transactions" items={related.transactions} />
        <RelatedSection title="Funds" items={related.funds} />
        <RelatedSection title="Portfolio Companies" items={related.portfolio_companies} />
        <RelatedSection title="People" items={related.people} />
        <RelatedSection title="Related Research" items={related.articles} />
        <RelatedSection title="Related News" items={related.news} />
        <RelatedSection title="Comparable Entities" items={related.comparables} />
        <RelatedSection title="Industries" items={related.industries} />

        {data.last_refresh && (
          <p className="text-xs text-[var(--pe-muted)] text-center pt-6 border-t border-[var(--pe-border)]">
            Morning intelligence last refreshed {new Date(data.last_refresh).toLocaleString()}
          </p>
        )}
      </div>
    </div>
  );
}
