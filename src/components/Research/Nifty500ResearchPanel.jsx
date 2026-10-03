import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { searchNifty500Research } from '@/lib/nifty500ResearchApi';

function tone(sentiment = '') {
  if (/bullish/i.test(sentiment)) return 'text-[#087443]';
  if (/bearish/i.test(sentiment)) return 'text-[#b42318]';
  return 'text-[#966a00]';
}

export default function Nifty500ResearchPanel() {
  const [query, setQuery] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const cleaned = query.trim();
    if (!cleaned) {
      setItems([]);
      setError(null);
      return undefined;
    }
    let active = true;
    const timer = setTimeout(() => {
      setLoading(true);
      setError(null);
      searchNifty500Research(cleaned)
        .then((data) => active && setItems(data.items || []))
        .catch((reason) => {
          if (active) {
            setItems([]);
            setError(reason);
          }
        })
        .finally(() => active && setLoading(false));
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query]);

  return (
    <section id="nifty500-research" className="mt-8 border border-[#dde1e6] bg-white">
      <div className="border-b border-[#dde1e6] p-5">
        <h2 className="text-lg font-bold text-[#18202b]">Nifty 500 Research Search</h2>
        <p className="mt-1 text-xs text-[#737982]">Find a company’s current AGI technical research profile and evidence summary.</p>
        <div className="mt-4 flex items-center gap-2 border border-[#cbd2da] px-3 py-2 focus-within:border-[#274c77]">
          <Search className="h-4 w-4 shrink-0 text-[#667085]" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by NSE symbol, for example RELIANCE"
            className="w-full bg-transparent text-sm outline-none"
            aria-label="Search Nifty 500 research"
          />
        </div>
      </div>
      {query.trim() && (
        <div className="divide-y divide-[#edf0f2]">
          {loading && <p className="p-4 text-sm text-[#737982]">Searching published research…</p>}
          {!loading && error && (
            <p className="p-4 text-sm text-[#b42318]">
              Research search is unavailable: {error.message}
            </p>
          )}
          {!loading && !error && items.length === 0 && <p className="p-4 text-sm text-[#737982]">No published Nifty 500 research matches this symbol.</p>}
          {!loading && items.map((item) => (
            <Link key={item.symbol} to={`/research/stocks/${item.symbol}`} className="flex items-center justify-between gap-4 p-4 hover:bg-[#f8fafb]">
              <div>
                <p className="font-bold text-[#18202b]">{item.symbol}</p>
                <p className="mt-1 text-[11px] text-[#737982]">Confidence {item.aiConfidencePercent}% · Derived research score</p>
              </div>
              <span className={`text-xs font-bold ${tone(item.overallSentiment)}`}>{item.overallSentiment}</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
