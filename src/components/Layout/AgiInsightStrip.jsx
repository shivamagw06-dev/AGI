import { Link } from 'react-router-dom';
import useMarketIntelligence from '@/hooks/useMarketIntelligence';

/** AGI Insight Strip — proprietary analytics only, no raw exchange prices */
export default function AgiInsightStrip() {
  const { insightStrip, loading, disclaimer } = useMarketIntelligence();

  return (
    <div className="border-b border-[#dddddd] bg-[#fafafa]">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 flex items-center h-10 gap-4">
        <div className="flex items-center gap-5 overflow-x-auto flex-1 scrollbar-hide py-1">
          {loading ? (
            <span className="text-xs text-[#767676] shrink-0">Loading AGI insights…</span>
          ) : (
            insightStrip.map((item) => (
              <Link
                key={item.id}
                to="/"
                className="flex flex-col shrink-0 hover:opacity-75 transition-opacity min-w-[100px]"
              >
                <span className="text-[10px] font-bold uppercase tracking-wide text-[#767676]">
                  {item.label}
                </span>
                <span className="text-xs font-bold text-[#111111] leading-tight">
                  {item.value}
                </span>
                {item.sub && (
                  <span className="text-[9px] text-[#999]">{item.sub}</span>
                )}
              </Link>
            ))
          )}
        </div>
        <Link
          to="/research"
          className="hidden md:block shrink-0 text-[10px] font-bold text-[#111111] hover:text-[#ff6600] whitespace-nowrap"
        >
          AGI Research →
        </Link>
      </div>
      {!loading && disclaimer && (
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 pb-1 hidden lg:block">
          <p className="text-[9px] text-[#bbb] truncate" title={disclaimer}>
            AGI proprietary analytics · Not raw exchange data
          </p>
        </div>
      )}
    </div>
  );
}
