import { Link } from 'react-router-dom';
import useMarketDashboard from '@/hooks/useMarketDashboard';
import AgiMarketPulse from '@/components/Home/AgiMarketPulse';

function StockFocusRow({ stock }) {
  const trendColor =
    stock.trend === 'Bullish'
      ? 'text-[#008001]'
      : stock.trend === 'Bearish'
        ? 'text-[#cc0000]'
        : 'text-[#555555]';

  return (
    <Link
      to="/markets"
      className="flex items-center justify-between py-3 border-b border-[#eeeeee] last:border-0 group hover:bg-[#fafafa] px-1 -mx-1"
    >
      <div className="min-w-0">
        <p className="text-sm font-bold text-[#111111] group-hover:text-[#ff6600]">{stock.name || stock.symbol}</p>
        <p className="text-[10px] text-[#767676]">{stock.name}</p>
      </div>
      <div className="text-right shrink-0 ml-4">
        <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676]">AGI signal</p>
        <p className={`text-xs font-bold ${trendColor}`}>{stock.trend}</p>
        <p className="text-[10px] text-[#929292]">{stock.category || stock.momentum}</p>
      </div>
    </Link>
  );
}

function SectorRow({ sector }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#eeeeee] last:border-0 text-xs">
      <span className="font-bold text-[#111111]">
        {sector.rank}. {sector.name}
      </span>
      <span className={`font-bold ${sector.direction === '↑' ? 'text-[#008001]' : 'text-[#cc0000]'}`}>
        {sector.direction === '↑' ? 'Leading' : 'Under pressure'} · {sector.strength}
      </span>
    </div>
  );
}

export default function TodayDashboard() {
  const { stocksInFocus, sectors, breadth, summary, loading } = useMarketDashboard();

  return (
    <section className="py-8 border-b border-[#dddddd]">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-[#111111]">Today&apos;s Market Intelligence</h2>
          <p className="text-sm text-[#767676] mt-1">
            A concise read on leadership, risk and developing market themes
          </p>
        </div>
        <Link to="/research" className="text-xs font-bold text-[#111111] hover:text-[#ff6600] hidden sm:block">
          Full research →
        </Link>
      </div>

      {summary && (
        <div className="mb-6 p-4 bg-[#fafafa] border border-[#eeeeee] border-l-4 border-l-[#ff6600]">
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">
            AGI Market Summary
          </p>
          <p className="text-sm text-[#333333] leading-relaxed">{summary}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4">
          <AgiMarketPulse />
        </div>

        <div className="lg:col-span-4">
          <div className="border border-[#dddddd] p-4 h-full">
            <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676] mb-1">
              Companies on Watch
            </h3>
            <p className="text-[10px] text-[#929292] mb-2">Model-driven signals, not market quotes</p>
            {loading ? (
              <p className="text-xs text-[#767676]">Calculating AGI scores…</p>
            ) : (
              (stocksInFocus || []).slice(0, 6).map((s) => (
                <StockFocusRow key={s.symbol} stock={s} />
              ))
            )}
            <p className="text-[10px] text-[#999] mt-3">Technical signal · Research watchlist · Not investment advice</p>
          </div>
        </div>

        <div className="lg:col-span-4 space-y-4">
          <div className="border border-[#dddddd] p-4">
            <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676] mb-3">
              Market Breadth
            </h3>
            <p className="text-2xl font-bold text-[#111111]">{breadth?.label || 'Neutral'}</p>
            {breadth?.ratio != null && (
              <p className="text-xs text-[#767676] mt-1">
                Advance/Decline ratio: {breadth.ratio.toFixed(2)}
              </p>
            )}
          </div>

          <div className="border border-[#dddddd] p-4">
            <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676] mb-3">
              Sector Leadership
            </h3>
            {loading ? (
              <p className="text-xs text-[#767676]">Loading…</p>
            ) : (
              (sectors || []).slice(0, 6).map((s) => <SectorRow key={s.name} sector={s} />)
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
