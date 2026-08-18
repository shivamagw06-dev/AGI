import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { readingTime } from '@/lib/articleUtils';

/**
 * CMS preview mirrors the published article shell:
 * wider header/cover, readable prose column, shared .article-prose media rules.
 */
export default function ArticlePreview({ open, onClose, article, html }) {
  if (!open) return null;

  const minutes = readingTime(html);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 overflow-y-auto py-8 px-4">
      <div className="relative w-full max-w-[760px] bg-white rounded-xl shadow-2xl overflow-hidden">
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
          <header className="article-preview-header article-page-column mx-auto">
            {article.section && <p className="article-kicker">{article.section}</p>}
            <h1>
              {article.title || 'Untitled'}
            </h1>
            {article.metaDescription && (
              <p className="article-dek">{article.metaDescription}</p>
            )}
          </header>

          {article.coverUrl && (
            <div className="article-page-column mx-auto">
            <div className="agi-cover agi-cover--article mt-8">
              <img src={article.coverUrl} alt="" />
            </div>
            </div>
          )}

          <div
            className="article-prose prose prose-lg prose-neutral article-page-column mx-auto mt-8 w-full"
            dangerouslySetInnerHTML={{ __html: html || '<p>No content yet.</p>' }}
          />
        </div>
      </div>
    </div>
  );
}
