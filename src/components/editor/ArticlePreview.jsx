import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { readingTime } from '@/lib/articleUtils';

export default function ArticlePreview({ open, onClose, article, html }) {
  if (!open) return null;

  const minutes = readingTime(html);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 overflow-y-auto py-8 px-4">
      <div className="relative w-full max-w-4xl bg-white rounded-xl shadow-2xl">
        <div className="sticky top-0 flex items-center justify-between px-6 py-4 border-b bg-white rounded-t-xl z-10">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-600 font-semibold">Preview</p>
            <p className="text-sm text-slate-500">{minutes} min read · {article.status || 'draft'}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={18} />
          </Button>
        </div>

        {article.coverUrl && (
          <img src={article.coverUrl} alt="" className="w-full max-h-80 object-cover" />
        )}

        <div className="px-8 py-10">
          <span className="text-sm font-medium text-blue-700">{article.section}</span>
          <h1 className="mt-3 text-4xl font-bold text-slate-900 leading-tight">{article.title || 'Untitled'}</h1>

          {article.metaDescription && (
            <p className="mt-4 text-lg text-slate-500 leading-relaxed">{article.metaDescription}</p>
          )}

          <div
            className="article-prose prose prose-lg max-w-none mt-10 prose-headings:text-slate-900 prose-a:text-blue-700 prose-blockquote:border-blue-600"
            dangerouslySetInnerHTML={{ __html: html || '<p>No content yet.</p>' }}
          />
        </div>
      </div>
    </div>
  );
}
