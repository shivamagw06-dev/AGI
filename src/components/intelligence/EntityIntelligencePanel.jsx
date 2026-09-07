import { Bookmark, ExternalLink } from 'lucide-react';
import EntityCard from './EntityCard';

function ScoreBadge({ intelligence }) {
  if (!intelligence) return null;
  const color = intelligence.score >= 85 ? '#1D6B4F' : intelligence.score >= 70 ? '#0B3B60' : '#C2410C';
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="font-semibold" style={{ color }}>{intelligence.score} / 100</span>
      <span className="text-xs uppercase tracking-wider text-[var(--pe-muted)]">{intelligence.label}</span>
    </div>
  );
}

function RelatedList({ title, items }) {
  if (!items?.length) return null;
  return (
    <div className="mb-5">
      <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--pe-muted)] mb-2">{title}</p>
      <ul className="space-y-2">
        {items.slice(0, 5).map((item) => (
          <li key={item.id}>
            <EntityCard entity={item} compact />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function EntityIntelligencePanel({ entity, intelligence, related, timeline, lastRefresh }) {
  const meta = entity?.metadata || {};
  const latestNews = related?.news?.[0] || related?.articles?.[0];

  return (
    <aside className="pe-card p-5 lg:sticky lg:top-6 h-fit">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--pe-accent)] mb-4">
        Intelligence Panel
      </p>

      <ScoreBadge intelligence={intelligence} />

      {entity?.ai_summary && (
        <div className="mt-4 pb-4 border-b border-[var(--pe-border)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--pe-muted)] mb-2">AI Summary</p>
          <p className="text-sm leading-relaxed text-[var(--pe-text)]">{entity.ai_summary}</p>
        </div>
      )}

      {latestNews && (
        <div className="mt-4 pb-4 border-b border-[var(--pe-border)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--pe-muted)] mb-2">Latest News</p>
          <EntityCard entity={latestNews} compact />
        </div>
      )}

      {timeline?.length > 0 && (
        <div className="mt-4 pb-4 border-b border-[var(--pe-border)]">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--pe-muted)] mb-2">Recent Timeline</p>
          <ul className="space-y-2">
            {timeline.slice(0, 3).map((ev) => (
              <li key={ev.id} className="text-sm">
                <span className="text-[10px] text-[var(--pe-muted)]">{new Date(ev.occurred_at).getFullYear()}</span>
                <p className="font-medium">{ev.title}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 pb-4 border-b border-[var(--pe-border)] grid grid-cols-2 gap-3 text-sm">
        {meta.aum && (
          <div>
            <p className="text-[10px] uppercase text-[var(--pe-muted)]">AUM</p>
            <p className="font-semibold">{meta.aum}</p>
          </div>
        )}
        {meta.hq && (
          <div>
            <p className="text-[10px] uppercase text-[var(--pe-muted)]">HQ</p>
            <p className="font-semibold">{meta.hq}</p>
          </div>
        )}
        {related && (
          <div>
            <p className="text-[10px] uppercase text-[var(--pe-muted)]">Relationships</p>
            <p className="font-semibold">
              {(related.funds?.length || 0) + (related.portfolio_companies?.length || 0) + (related.people?.length || 0)}
            </p>
          </div>
        )}
        {entity?.tags?.length > 0 && (
          <div className="col-span-2">
            <p className="text-[10px] uppercase text-[var(--pe-muted)] mb-1">Industries</p>
            <div className="flex flex-wrap gap-1">
              {entity.tags.slice(0, 4).map((t) => (
                <span key={t} className="pe-tag text-[10px] px-1.5 py-0.5">{t}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <RelatedList title="Comparable Entities" items={related?.comparables} />
      <RelatedList title="Related Funds" items={related?.funds} />

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className="pe-btn text-xs flex items-center gap-1">
          <Bookmark size={12} /> Watch Entity
        </button>
        {meta.website && (
          <a
            href={meta.website.startsWith('http') ? meta.website : `https://${meta.website}`}
            target="_blank"
            rel="noopener noreferrer"
            className="pe-btn text-xs flex items-center gap-1 no-underline"
          >
            <ExternalLink size={12} /> Source
          </a>
        )}
      </div>

      {lastRefresh && (
        <p className="text-[10px] text-[var(--pe-muted)] mt-4">
          Intelligence refreshed {new Date(lastRefresh).toLocaleString()}
        </p>
      )}
    </aside>
  );
}
