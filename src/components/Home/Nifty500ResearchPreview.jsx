import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ChevronRight, Database, ShieldAlert } from 'lucide-react';
import useNifty500Research from '@/hooks/useNifty500Research';

const TABS = [
  { key: 'topBullish', label: 'Positive structure' },
  { key: 'neutralWatchlist', label: 'Neutral / Watchlist' },
  { key: 'topBearish', label: 'Under pressure' },
];

function tone(sentiment = '') {
  if (/bullish/i.test(sentiment)) return 'text-[#087443] bg-[#ecfdf3] border-[#b7ebcc]';
  if (/bearish/i.test(sentiment)) return 'text-[#b42318] bg-[#fff1f0] border-[#f7c5c0]';
  return 'text-[#966a00] bg-[#fff8e8] border-[#f4d99d]';
}

export default function Nifty500ResearchPreview() {
  const [tab, setTab] = useState('topBullish');
  const { run, topBullish = [], topBearish = [], neutralWatchlist = [], loading, error } = useNifty500Research();
  const items = { topBullish, topBearish, neutralWatchlist }[tab] || [];

  return (
    <section className="py-8 border-b border-[#dddddd]">
      <div className="flex flex-col gap-4 border-b border-[#eeeeee] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[#274c77]">
            <Database className="h-4 w-4" />
            <span className="text-[10px] font-bold uppercase tracking-[0.12em]">Nifty 500 research engine</span>
          </div>
          <h2 className="mt-2 text-lg font-bold text-[#111111]">Nifty 500 Market Structure</h2>
          <p className="mt-1 text-xs text-[#767676]">Model-ranked technical research for all covered companies. Not investment recommendations.</p>
        </div>
        <Link to="/market-intelligence#nifty500-research" className="inline-flex items-center gap-1 text-xs font-bold text-[#111111] hover:text-[#ff6600]">
          Explore all research <ChevronRight className="h-4 w-4" />
        </Link>
      </div>

      {loading ? (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse border border-[#eeeeee] bg-[#f7f7f7]" />)}
        </div>
      ) : error || !run ? (
        <div className="mt-4 flex items-start gap-3 border border-dashed border-[#cbd2da] bg-[#fafbfc] p-4 text-xs leading-relaxed text-[#667085]">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          The first published Nifty 500 research run will appear here after the scheduled research engine completes.
        </div>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-2">
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={`border px-3 py-1.5 text-xs font-bold ${tab === key ? 'border-[#111111] bg-[#111111] text-white' : 'border-[#dddddd] text-[#444444] hover:border-[#999999]'}`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {items.slice(0, 8).map((item) => (
              <Link key={item.symbol} to={`/research/stocks/${item.symbol}`} className="group border border-[#dddddd] bg-white p-4 hover:border-[#111111]">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-[#111111] group-hover:underline">{item.symbol}</p>
                    <p className="mt-1 text-[11px] text-[#767676]">Derived technical research</p>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#767676] group-hover:text-[#111111]" />
                </div>
                <span className={`mt-4 inline-flex border px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${tone(item.overallSentiment)}`}>
                  {item.overallSentiment}
                </span>
              </Link>
            ))}
          </div>
          <p className="mt-4 text-[11px] text-[#767676]">
            {run.totalStocksAnalyzed} companies analyzed · Updated {new Date(run.publishedAt || run.generatedAt).toLocaleString('en-IN')}
          </p>
        </>
      )}
    </section>
  );
}
