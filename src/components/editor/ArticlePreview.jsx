import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { readingTime } from '@/lib/articleUtils';
import LiveBadge from '@/components/Article/LiveBadge';
import { formatLiveClock, normalizeLiveUpdates } from '@/lib/liveArticle';

/**
 * CMS preview mirrors the published article shell:
 * wider header/cover, readable prose column, shared .article-prose media rules.
 */
export default function ArticlePreview({ open, onClose, article, html }) {
  if (!open) return null;

  const minutes = readingTime(html);
  const liveUpdates = normalizeLiveUpdates(article.liveUpdates);
  const showLive = Boolean(article.isLive);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 overflow-y-auto py-8 px-4">
      <div className="relative w-full max-w-[1500px] bg-white rounded-xl shadow-2xl overflow-hidden">
        <div className="sticky top-0 flex items-center justify-between px-6 py-4 border-b bg-white rounded-t-xl z-10">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-600 font-semibold">Preview</p>
            <p className="text-sm text-slate-500">{minutes} min read · {article.status || 'draft'}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={18} />
          </Button>
        </div>

        <div className="article-preview-shell mx-auto w-full px-6 py-8">
          <header className="article-preview-header article-preview-wide mx-auto">
            {showLive ? (
              <div className="article-live-bar">
                <LiveBadge size="md" />
                <span>Coverage is live</span>
              </div>
            ) : null}
            {article.section && <p className="article-kicker">{article.section}</p>}
            <h1>
              {article.title || 'Untitled'}
            </h1>
            {article.metaDescription && (
              <p className="article-dek">{article.metaDescription}</p>
            )}
          </header>

          {article.coverUrl && (
            <div className="article-preview-wide mx-auto">
            <div className="agi-cover agi-cover--article mt-8">
              <img src={article.coverUrl} alt="" />
            </div>
            </div>
          )}

          {liveUpdates.length ? (
            <div className="article-preview-reading mx-auto mt-8 w-full">
              <p className="article-live-updates-heading">Live updates</p>
              {liveUpdates.map((update) => (
                <article key={update.id} className="article-live-update">
                  {update.at ? <time dateTime={update.at}>{formatLiveClock(update.at)}</time> : null}
                  {update.headline ? <h2>{update.headline}</h2> : null}
                </article>
              ))}
            </div>
          ) : null}

          <div
            className="article-prose prose prose-lg prose-neutral article-preview-reading mx-auto mt-8 w-full"
            dangerouslySetInnerHTML={{ __html: html || '<p>No content yet.</p>' }}
          />
        </div>
      </div>
    </div>
  );
}
