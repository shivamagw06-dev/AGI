import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Building2, Loader2, Search, X } from 'lucide-react';
import { getRecentSearches } from '@/lib/searchHistory';
import { useUniversalSearch } from '@/hooks/useIntelligencePlatform';

const EXAMPLES = [
  'Should I invest in ICICI Bank?',
  "What is AGI's current market view?",
  'Which sectors benefit from lower interest rates?',
  'Compare HDFC Bank vs ICICI Bank.',
];

const ENTITY_EXAMPLES = ['Blackstone', 'KKR', 'Healthcare', 'Enterprise SaaS'];

export default function ResearchSearch({ onClose }) {
  const navigate = useNavigate();
  const [recent, setRecent] = useState([]);
  const [entityQuery, setEntityQuery] = useState('');
  const { groups, total, loading, took_ms } = useUniversalSearch(entityQuery);

  useEffect(() => {
    setRecent(getRecentSearches());
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const goToEntity = (path) => {
    onClose();
    navigate(path);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div
        className="absolute top-0 inset-x-0 bg-white border-b border-[#ddd] shadow-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="max-w-[760px] mx-auto px-4 py-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-[#ff6600]" />
              <p className="text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Universal Search</p>
            </div>
            <button type="button" onClick={onClose} aria-label="Close search">
              <X className="w-5 h-5 text-[#767676]" />
            </button>
          </div>

          <div className="relative mb-6">
            <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#767676]" />
            <input
              type="search"
              autoFocus
              value={entityQuery}
              onChange={(e) => setEntityQuery(e.target.value)}
              placeholder="Search firms, funds, companies, transactions, people…"
              className="w-full border border-[#ddd] pl-10 pr-10 py-3 text-sm focus:outline-none focus:border-[#111]"
            />
            {loading && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#767676] animate-spin" />
            )}
          </div>

          {entityQuery.trim().length >= 2 && (
            <div className="mb-6">
              {groups.length === 0 && !loading && (
                <p className="text-sm text-[#767676]">No entities found for &ldquo;{entityQuery}&rdquo;</p>
              )}
              {groups.map((group) => (
                <div key={group.name} className="mb-5">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
                    {group.name}
                  </p>
                  <ul className="divide-y divide-[#eee] border border-[#eee]">
                    {group.results.map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          onClick={() => goToEntity(item.path)}
                          className="w-full text-left px-4 py-3 hover:bg-[#fafafa] flex items-start gap-3"
                        >
                          {item.logo ? (
                            <img src={item.logo} alt="" className="w-8 h-8 rounded object-contain bg-[#f5f5f5] shrink-0" />
                          ) : (
                            <span
                              className="w-8 h-8 rounded flex items-center justify-center text-xs text-white font-bold shrink-0"
                              style={{ background: item.color || '#0B3B60' }}
                            >
                              {item.name?.[0]}
                            </span>
                          )}
                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-2">
                              <p className="font-medium text-sm text-[#111]">{item.name}</p>
                              <span className="text-[10px] uppercase tracking-wide text-[#767676] shrink-0">
                                {item.entity_type_label}
                              </span>
                            </div>
                            {item.ai_summary ? (
                              <p className="text-xs text-[#767676] mt-0.5 line-clamp-2">{item.ai_summary}</p>
                            ) : item.description ? (
                              <p className="text-xs text-[#767676] mt-0.5 line-clamp-1">{item.description}</p>
                            ) : null}
                            <div className="flex flex-wrap gap-2 mt-1 text-[10px] text-[#999]">
                              {item.intelligence_score != null && <span>{item.intelligence_score}/100</span>}
                              {item.updated_at && (
                                <span>Updated {new Date(item.updated_at).toLocaleDateString()}</span>
                              )}
                            </div>
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {total > 0 && (
                <p className="text-xs text-[#767676]">
                  {total} matching entities{took_ms ? ` · ${took_ms}ms` : ''}
                </p>
              )}
            </div>
          )}

          {entityQuery.trim().length < 2 && (
            <>
              <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
                Try searching
              </p>
              <div className="flex flex-wrap gap-2 mb-6">
                {ENTITY_EXAMPLES.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setEntityQuery(q)}
                    className="text-[11px] border border-[#ddd] px-3 py-1.5 hover:border-[#111] hover:text-[#ff6600]"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </>
          )}

          <div className="mt-5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
              Popular questions
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => {
                    onClose();
                    navigate(`/ask?q=${encodeURIComponent(q)}`);
                  }}
                  className="text-[11px] border border-[#ddd] px-3 py-1.5 hover:border-[#111] hover:text-[#ff6600]"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {recent.length > 0 && (
            <div className="mt-5">
              <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
                Recent searches
              </p>
              <div className="flex flex-wrap gap-2">
                {recent.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => {
                      onClose();
                      navigate(`/ask?q=${encodeURIComponent(q)}`);
                    }}
                    className="text-[11px] border border-[#ddd] px-3 py-1.5 hover:border-[#111]"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-[#767676] mt-5">
            Browse the library instead?{' '}
            <Link to="/research" onClick={onClose} className="font-bold text-[#111] hover:text-[#ff6600]">
              All research →
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
