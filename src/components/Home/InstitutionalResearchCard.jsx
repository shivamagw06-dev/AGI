import { Link } from 'react-router-dom';

function OutlookPill({ tag }) {
  if (!tag) return null;
  const t = String(tag).toUpperCase();
  const buy = t.includes('BUY');
  const sell = t.includes('SELL');
  const cls = buy
    ? 'bg-[#e8f5e9] text-[#1b5e20]'
    : sell
      ? 'bg-[#ffebee] text-[#b71c1c]'
      : 'bg-[#f5f5f5] text-[#555]';
  return (
    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 ${cls}`}>{tag}</span>
  );
}

export default function InstitutionalResearchCard({ article, showImage = true }) {
  if (!article) return null;

  const sector = article.sector || article.category || article.section || 'Research';
  const researchType = article.researchType || article.section || 'Research Note';
  const tags = Array.isArray(article.tags) ? article.tags : [];

  return (
    <Link
      to={`/article/${article.slug}`}
      className="group block border border-[#dddddd] bg-white hover:border-[#999999] transition-colors h-full"
    >
      {showImage && article.coverUrl && (
        <div className="aspect-[16/9] bg-[#f0f0f0] overflow-hidden">
          <img
            src={article.coverUrl}
            alt=""
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
          />
        </div>
      )}

      <div className="p-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wide text-[#ff6600]">
            {sector}
          </span>
          <OutlookPill tag={tags.find((t) => /buy|sell|hold/i.test(t))} />
        </div>

        <p className="text-[10px] font-semibold uppercase tracking-wide text-[#767676] mb-1">
          {researchType}
        </p>

        <h3 className="text-base font-bold text-[#111111] leading-snug group-hover:underline decoration-[#ff6600] underline-offset-2 line-clamp-2">
          {article.title}
        </h3>

        {article.excerpt && (
          <p className="text-xs text-[#555555] mt-2 line-clamp-2 leading-relaxed">{article.excerpt}</p>
        )}

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 text-[11px] text-[#767676]">
          <span>{article.publishedLabel || article.date}</span>
          {article.readTime && <span>{article.readTime}</span>}
          {article.analyst && <span>{article.analyst}</span>}
        </div>

        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {tags.slice(0, 3).map((tag) => (
              <span key={tag} className="text-[10px] border border-[#eee] px-1.5 py-0.5 text-[#666]">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}
