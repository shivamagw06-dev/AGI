import { Link } from 'react-router-dom';
import useMarketTicker from '@/hooks/useMarketTicker';

function formatPrice(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function formatChange(n) {
  const num = Number(n);
  if (!Number.isFinite(num)) return null;
  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
}

function formatAbsChange(price, pct) {
  const p = Number(price);
  const c = Number(pct);
  if (!Number.isFinite(p) || !Number.isFinite(c) || c === 0) return null;
  const abs = (p * c) / (100 + c);
  const sign = c >= 0 ? '+' : '';
  return `${sign}${abs.toFixed(0)}`;
}

export default function MarketTicker() {
  const { items, loading } = useMarketTicker();

  return (
    <div className="border-b border-[#dddddd] bg-[#fafafa]">
      <div className="max-w-[1280px] mx-auto px-4 flex items-center h-10 gap-4">
        <div className="flex items-center gap-6 overflow-x-auto flex-1 scrollbar-hide py-1">
          {loading ? (
            <span className="text-xs text-[#767676] shrink-0">Loading markets…</span>
          ) : (
            items.map((item) => {
              const pct = item.percentChange ?? item.change;
              const up = Number(pct) >= 0;
              const absChange = formatAbsChange(item.price, pct);
              return (
                <Link
                  key={item.id || item.name}
                  to="/markets/stocks"
                  className="flex items-baseline gap-2 shrink-0 hover:opacity-75 transition-opacity group"
                >
                  <span className="text-[11px] font-bold uppercase tracking-wide text-[#111111]">
                    {item.name}
                  </span>
                  <span className="text-xs font-semibold text-[#333333] tabular-nums">
                    {formatPrice(item.price)}
                  </span>
                  {pct != null && (
                    <span className={`text-[11px] font-semibold tabular-nums ${up ? 'text-[#008001]' : 'text-[#cc0000]'}`}>
                      {absChange && <span className="mr-1">{absChange}</span>}
                      ({formatChange(pct)})
                    </span>
                  )}
                </Link>
              );
            })
          )}
        </div>
        <Link
          to="/markets/stocks"
          className="hidden md:block shrink-0 text-[11px] font-bold text-[#111111] hover:text-[#ff6600] whitespace-nowrap"
        >
          Live market data →
        </Link>
      </div>
    </div>
  );
}
