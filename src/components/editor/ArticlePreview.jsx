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
      <div className="relative w-full max-w-[1800px] bg-white rounded-xl shadow-2xl overflow-hidden">
        <div className="sticky top-0 flex items-center justify-between px-6 py-4 border-b bg-white rounded-t-xl z-10">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-600 font-semibold">Preview</p>
            <p className="text-sm text-slate-500">{minutes} min read · {article.status || 'draft'}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={18} />
          </Button>
        </div>

        <div className="article-preview-shell mx-auto w-full max-w-[1800px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
          <header className="article-preview-header w-full">
            <span className="text-sm font-medium text-blue-700">{article.section}</span>
            <h1 className="mt-3 text-3xl md:text-4xl font-bold text-slate-900 leading-tight">
              {article.title || 'Untitled'}
            </h1>
            {article.metaDescription && (
              <p className="mt-4 text-lg text-slate-500 leading-relaxed">{article.metaDescription}</p>
            )}
          </header>

          {article.coverUrl && (
            <div className="agi-cover agi-cover--article mt-6">
              <img src={article.coverUrl} alt="" />
            </div>
          )}

          <div
            className="article-prose prose prose-lg prose-neutral mt-8 w-full max-w-none prose-headings:text-slate-900 prose-a:text-blue-700 prose-blockquote:border-blue-600"
            dangerouslySetInnerHTML={{ __html: html || '<p>No content yet.</p>' }}
          />
        </div>
      </div>
    </div>
  );
}
