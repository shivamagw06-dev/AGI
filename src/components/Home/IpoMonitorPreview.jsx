import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarDays, ChevronRight, FileText } from 'lucide-react';
import { getIpoSummary } from '@/lib/ipoApi';

function formatDate(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : 'To be announced';
}

function priceBand(ipo) {
  if (ipo.minPrice == null && ipo.maxPrice == null) return 'Price band pending';
  if (ipo.minPrice === ipo.maxPrice) return `₹${ipo.minPrice}`;
  return `₹${ipo.minPrice}–${ipo.maxPrice}`;
}

export default function IpoMonitorPreview() {
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    getIpoSummary()
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, []);

  const active = state.data?.active || [];
  const upcoming = state.data?.upcoming || [];

  return (
    <section className="py-8 border-b border-[#dddddd]">
      <div className="flex flex-col gap-3 border-b border-[#eeeeee] pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[#274c77]">
            <CalendarDays className="h-4 w-4" />
            <span className="text-[10px] font-bold uppercase tracking-[0.12em]">IPO Intelligence</span>
          </div>
          <h2 className="mt-2 text-lg font-bold text-[#111111]">Upcoming Public Issues</h2>
          <p className="mt-1 text-xs text-[#767676]">Live pipeline plus Research Hub. Offer details refresh daily at 12:00 PM IST.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-[#767676]">{active.length} active issue{active.length === 1 ? '' : 's'}</span>
          <Link to="/ipo-intelligence" className="inline-flex items-center gap-1 text-[11px] font-bold text-[#274c77] hover:underline">
            Open platform <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {state.loading ? (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((item) => <div key={item} className="h-44 animate-pulse border border-[#eeeeee] bg-[#f7f7f7]" />)}
        </div>
      ) : state.error || state.data?.unavailable ? (
        <div className="mt-4 border border-dashed border-[#cbd2da] bg-[#fafbfc] p-4 text-xs leading-relaxed text-[#667085]">
          IPO information is temporarily unavailable. The next scheduled data refresh is at 12:00 PM IST.
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {upcoming.slice(0, 6).map((ipo) => (
            <Link key={ipo.symbol} to={`/ipos/${ipo.symbol}`} className="group border border-[#dddddd] bg-white p-4 hover:border-[#111111]">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-bold text-[#111111] group-hover:underline">{ipo.name}</p>
                  <p className="mt-1 text-[11px] text-[#767676]">{ipo.isSme ? 'SME IPO' : 'Mainboard IPO'}</p>
                </div>
                <ChevronRight className="h-4 w-4 text-[#767676] group-hover:text-[#111111]" />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 border-y border-[#eeeeee] py-3 text-xs">
                <div><p className="text-[#767676]">Opens</p><p className="mt-1 font-bold text-[#111111]">{formatDate(ipo.biddingStartDate)}</p></div>
                <div><p className="text-[#767676]">Price band</p><p className="mt-1 font-bold text-[#111111]">{priceBand(ipo)}</p></div>
              </div>
              <p className="mt-3 line-clamp-1 text-[11px] text-[#767676]">{ipo.detail || 'View offer details and source document'}</p>
            </Link>
          ))}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        {state.data?.disclaimer ? (
          <p className="flex items-start gap-2 text-[11px] leading-relaxed text-[#767676]">
            <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {state.data.disclaimer}
          </p>
        ) : (
          <span />
        )}
        <Link to="/ipo-intelligence" className="text-[11px] font-bold text-[#274c77] hover:underline">
          View IPO Intelligence Platform →
        </Link>
      </div>
    </section>
  );
}
