import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { AdminOnly } from '@/components/auth/AskAgiAdminAccess';
import { getUiAutocomplete } from '@/lib/uiApi';
import { getRecentSearches, pushSearch } from '@/lib/searchHistory';

const DEFAULT_PLACEHOLDER =
  'Ask AGI anything about markets, companies, sectors, investing or the economy...';

export default function AskAgiBar({
  placeholder = DEFAULT_PLACEHOLDER,
  examples = [],
  autoFocus = false,
  size = 'large',
  initialQuery = '',
  onAsk,
  buttonLabel = 'Ask AGI',
  ariaLabel = 'Ask AGI',
}) {
  const navigate = useNavigate();
  const [query, setQuery] = useState(initialQuery || '');
  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState(null);
  const [recent, setRecent] = useState([]);
  const boxRef = useRef(null);

  useEffect(() => {
    setRecent(getRecentSearches());
  }, []);

  useEffect(() => {
    setQuery(initialQuery || '');
  }, [initialQuery]);

  useEffect(() => {
    if (!query.trim()) {
      setSuggestions(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      getUiAutocomplete(query.trim())
        .then((data) => {
          if (!cancelled) setSuggestions(data);
        })
        .catch(() => {
          if (!cancelled) setSuggestions(null);
        });
    }, 180);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    const onDoc = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const submit = (q) => {
    const value = String(q || query).trim();
    if (!value) return;
    pushSearch(value);
    setOpen(false);
    if (typeof onAsk === 'function') {
      onAsk(value);
      return;
    }
    navigate(`/ask?q=${encodeURIComponent(value)}`);
  };

  const inputCls =
    size === 'large'
      ? 'text-base md:text-lg py-4 pl-12 pr-28'
      : 'text-sm py-2.5 pl-10 pr-20';

  const groups = [
    { key: 'questions', label: 'Questions', items: suggestions?.questions },
    { key: 'companies', label: 'Companies', items: suggestions?.companies },
    { key: 'themes', label: 'Themes', items: suggestions?.themes },
    { key: 'sectors', label: 'Sectors', items: suggestions?.sectors },
    { key: 'articles', label: 'Articles', items: suggestions?.articles },
  ];

  return (
    <AdminOnly>
      <div ref={boxRef} className="relative w-full">
      <form
        role="search"
        aria-label={ariaLabel}
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="relative"
      >
        <Search
          className={`absolute left-4 top-1/2 -translate-y-1/2 text-[#767676] ${
            size === 'large' ? 'w-5 h-5' : 'w-4 h-4 left-3'
          }`}
          aria-hidden
        />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          autoFocus={autoFocus}
          placeholder={placeholder}
          className={`w-full border border-[#cccccc] bg-white text-[#111111] outline-none focus:border-[#111111] ${inputCls}`}
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls="ask-agi-suggestions"
        />
        <button
          type="submit"
          className={`absolute right-2 top-1/2 -translate-y-1/2 bg-[#111111] text-white font-bold hover:bg-[#333333] transition-colors ${
            size === 'large' ? 'text-sm px-5 py-2.5' : 'text-xs px-3 py-1.5'
          }`}
        >
          {buttonLabel}
        </button>
      </form>

      {open && (
        <div
          id="ask-agi-suggestions"
          className="absolute z-30 mt-1 w-full border border-[#dddddd] bg-white shadow-lg max-h-[60vh] overflow-y-auto"
          role="listbox"
        >
          {!query.trim() && (
            <div className="p-3 border-b border-[#eee]">
              <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
                Recent searches
              </p>
              {recent.length === 0 ? (
                <p className="text-xs text-[#929292]">Start with a company, theme, or market question.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {recent.map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => submit(r)}
                      className="text-[11px] border border-[#ddd] px-2 py-1 hover:border-[#111] hover:text-[#ff6600]"
                    >
                      {r}
                    </button>
                  ))}
                </div>
              )}
              {examples?.length > 0 && (
                <div className="mt-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
                    Try asking
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {examples.slice(0, 4).map((ex) => (
                      <button
                        key={ex}
                        type="button"
                        onClick={() => submit(ex)}
                        className="text-[11px] border border-[#ddd] px-2 py-1 text-left hover:border-[#111] hover:text-[#ff6600]"
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {groups.map(
            (g) =>
              (g.items || []).length > 0 && (
                <div key={g.key} className="p-2 border-b border-[#eee]">
                  <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[#767676]">
                    {g.label}
                  </p>
                  {g.items.map((item) => (
                    <button
                      key={`${g.key}-${item.id || item.label}`}
                      type="button"
                      role="option"
                      onClick={() => {
                        if (g.key === 'companies') {
                          navigate(`/research/stocks/${encodeURIComponent(item.id || item.label)}`);
                          setOpen(false);
                          return;
                        }
                        if (g.key === 'themes') {
                          navigate(`/themes/${encodeURIComponent(item.id || item.label)}`);
                          setOpen(false);
                          return;
                        }
                        if (g.key === 'sectors') {
                          navigate(`/sectors/${encodeURIComponent(item.id || item.label)}`);
                          setOpen(false);
                          return;
                        }
                        submit(item.label || item.id);
                      }}
                      className="block w-full text-left px-2 py-2 text-sm hover:bg-[#fafafa]"
                    >
                      <span className="font-bold text-[#111]">{item.label}</span>
                      {item.reason && (
                        <span className="block text-[11px] text-[#767676] mt-0.5">{item.reason}</span>
                      )}
                    </button>
                  ))}
                </div>
              )
          )}
        </div>
      )}
      </div>
    </AdminOnly>
  );
}
