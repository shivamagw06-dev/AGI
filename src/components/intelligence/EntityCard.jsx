import { useState } from 'react';
import { Link } from 'react-router-dom';
import { entityPublicPath } from '@/lib/intelligencePlatformApi';

const TYPE_COLORS = {
  pe_firm: '#0B3B60',
  company: '#1D6B4F',
  portfolio_company: '#1D6B4F',
  fund: '#B8860B',
  person: '#6D28D9',
  transaction: '#B91C1C',
  industry: '#C2410C',
  news: '#64748B',
  article: '#64748B',
};

export default function EntityCard({ entity, compact = false }) {
  const [hover, setHover] = useState(false);
  if (!entity) return null;

  const path = entity.path || entityPublicPath(entity);
  const color = TYPE_COLORS[entity.entity_type] || '#64748B';
  const typeLabel = (entity.entity_type || '').replace(/_/g, ' ');

  if (compact) {
    return (
      <Link
        to={path}
        className="flex items-center gap-2 no-underline text-inherit hover:text-[var(--pe-accent)] group"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        {entity.logo ? (
          <img src={entity.logo} alt="" className="w-6 h-6 rounded object-contain bg-[#f5f5f5]" />
        ) : (
          <span className="w-6 h-6 rounded flex items-center justify-center text-[9px] text-white font-bold" style={{ background: color }}>
            {entity.name?.[0]}
          </span>
        )}
        <span className="text-sm font-medium group-hover:underline">{entity.name}</span>
        {hover && entity.ai_summary && (
          <span className="absolute z-20 ml-8 mt-8 w-64 p-3 bg-white border shadow-lg text-xs text-[var(--pe-muted)] hidden group-hover:block">
            {entity.ai_summary.slice(0, 120)}…
          </span>
        )}
      </Link>
    );
  }

  return (
    <div
      className="relative border border-[var(--pe-border)] bg-white p-4 hover:border-[var(--pe-accent)] transition-colors"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <Link to={path} className="no-underline text-inherit block">
        <div className="flex items-start gap-3">
          {entity.logo ? (
            <img src={entity.logo} alt="" className="w-10 h-10 rounded object-contain bg-[#f5f5f5] p-1" />
          ) : (
            <span
              className="w-10 h-10 rounded flex items-center justify-center text-sm text-white font-serif font-semibold shrink-0"
              style={{ background: color }}
            >
              {entity.name?.[0]}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-[10px] uppercase tracking-wider text-[var(--pe-muted)] capitalize">{typeLabel}</p>
            <p className="font-serif font-semibold text-base mt-0.5">{entity.name}</p>
            {entity.description && (
              <p className="text-sm text-[var(--pe-muted)] mt-1 line-clamp-2">{entity.description}</p>
            )}
          </div>
        </div>
      </Link>

      {hover && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 p-4 bg-white border border-[var(--pe-accent)] shadow-lg">
          {entity.ai_summary && (
            <p className="text-xs leading-relaxed text-[var(--pe-muted)] mb-3">{entity.ai_summary.slice(0, 200)}</p>
          )}
          <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wide">
            {entity.intelligence_score != null && (
              <span className="text-[var(--pe-accent)]">{entity.intelligence_score}/100</span>
            )}
            {entity.metadata?.aum && <span>AUM {entity.metadata.aum}</span>}
            {entity.metadata?.industry && <span>{entity.metadata.industry}</span>}
          </div>
          <Link to={path} className="inline-block mt-3 text-xs font-semibold text-[var(--pe-accent)] no-underline hover:underline">
            View Entity →
          </Link>
        </div>
      )}
    </div>
  );
}
