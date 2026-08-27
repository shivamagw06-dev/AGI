import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { enrichResearchCard } from '@/components/Home/homeTerminalData';
import { formatTimeAgo } from '@/lib/articleUtils';

function ChipList({ items }) {
  const list = (Array.isArray(items) ? items : []).filter(Boolean).slice(0, 4);
  if (!list.length) return <span className="text-[#9298a3]">—</span>;
  return (
    <span className="text-[#252b36]">
      {list.map((item, i) => (
        <span key={`${item}-${i}`}>
          {i > 0 ? ', ' : ''}
          {typeof item === 'string' ? item : item.name || item.ticker || item.label}
        </span>
      ))}
    </span>
  );
}

/** Institutional research card — not a news teaser. */
export default function ResearchFeedCard({ article, index = 0 }) {
  const row = enrichResearchCard(article);
  if (!row) return null;
  const href = row.href || (row.slug ? `/article/${row.slug}` : '/research');

  return (
    <article
      className="group border-b border-[#e6e8ec] py-6 first:pt-0 last:border-b-0 animate-home-rise"
      style={{ animationDelay: `${Math.min(index, 8) * 45}ms` }}
    >
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#ff6600]">
          {row.section || row.category || 'Research Note'}
        </span>
        {row.premium && (
          <span className="border border-[#0b1f33]/15 bg-[#0b1f33]/[0.04] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#0b1f33]">
            Premium
          </span>
        )}
      </div>

      <h3 className="font-serif text-xl md:text-[1.35rem] font-bold leading-snug text-[#111111]">
        <Link to={href} className="hover:underline decoration-[#ff6600] underline-offset-4">
          {row.title}
        </Link>
      </h3>

      <dl className="mt-4 space-y-2.5 text-sm leading-relaxed">
        <div>
          <dt className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#767676]">AI Executive Summary</dt>
          <dd className="mt-0.5 text-[#333] line-clamp-3">{row.executiveSummary || 'Summary pending from AGIB research desk.'}</dd>
        </div>
        <div>
          <dt className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#767676]">Why It Matters</dt>
          <dd className="mt-0.5 text-[#444] line-clamp-2">{row.whyItMatters}</dd>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1 text-xs">
          <div>
            <dt className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#767676]">Affected Companies</dt>
            <dd className="mt-0.5"><ChipList items={row.affectedCompanies} /></dd>
          </div>
          <div>
            <dt className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#767676]">Affected Sectors</dt>
            <dd className="mt-0.5"><ChipList items={row.affectedSectors} /></dd>
          </div>
          <div>
            <dt className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#767676]">Market Impact</dt>
            <dd className="mt-0.5 text-[#444] line-clamp-2">{row.marketImpact}</dd>
          </div>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#767676]">
          <span>{row.readTime}</span>
          <span>
            Published{' '}
            {row.publishedLabel
              ? formatTimeAgo(row.publishedLabel) || row.publishedLabel
              : 'Today'}
          </span>
        </div>
        <Link
          to={href}
          className="inline-flex items-center gap-1 text-xs font-bold text-[#0b1f33] group-hover:text-[#ff6600] transition-colors"
        >
          Read Research <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </article>
  );
}
