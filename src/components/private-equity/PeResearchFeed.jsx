import { Link } from 'react-router-dom';
import { ArrowUpRight, Clock } from 'lucide-react';

function formatTime(iso) {
  try {
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function PeResearchFeed({ items = [], activeSector, onClearSector }) {
  return (
    <aside className="pe-col-side">
      <div className="pe-glass p-4 sticky top-[72px]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="pe-eyebrow">Research Feed</h2>
          {activeSector && (
            <button type="button" onClick={onClearSector} className="text-xs pe-gold bg-transparent border-none cursor-pointer">
              Clear filter
            </button>
          )}
        </div>
        <div className="max-h-[calc(100vh-120px)] overflow-y-auto pr-1">
          {items.map((item) => (
            <article key={item.id} className="pe-glass pe-feed-item">
              <div className="flex items-start gap-3">
                <img
                  src={`https://www.google.com/s2/favicons?domain=${item.firmSlug}.com&sz=64`}
                  alt=""
                  className="pe-firm-logo shrink-0"
                />
                <div className="min-w-0 flex-1">
                  <span className="pe-badge">{item.dealType || item.category}</span>
                  <h3 className="text-sm font-semibold mt-2 leading-snug">{item.headline}</h3>
                  <p className="text-xs text-[var(--pe-text-muted)] mt-1.5 line-clamp-2">{item.summary}</p>
                  <div className="flex flex-wrap gap-2 mt-2 text-[10px] text-[var(--pe-text-muted)]">
                    <span>{item.sector}</span>
                    <span>·</span>
                    <span>{item.geography}</span>
                  </div>
                  <div className="pe-meta-hover">
                    <div className="flex items-center gap-1"><Clock size={10} /> {formatTime(item.timestamp)}</div>
                    <div>Source: {item.source}</div>
                    <div>Firm: {item.firmName}</div>
                  </div>
                  {item.firmSlug && (
                    <Link
                      to={`/private-equity/firms/${item.firmSlug}`}
                      className="inline-flex items-center gap-1 mt-2 text-xs pe-gold no-underline hover:underline"
                    >
                      Read more <ArrowUpRight size={12} />
                    </Link>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </aside>
  );
}
