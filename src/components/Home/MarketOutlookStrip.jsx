import { Link } from 'react-router-dom';
import useMarketSnapshot from '@/hooks/useMarketSnapshot';

/** Preferred strip order — only rows with live prices are shown. */
const STRIP_ORDER = [
  { key: 'nifty50', label: 'NIFTY 50', match: /^(nifty 50|nifty)$/i },
  { key: 'sensex', label: 'SENSEX', match: /^sensex$/i },
  { key: 'banknifty', label: 'BANK NIFTY', match: /bank\s*nifty|nifty\s*bank/i },
  { key: 'usdinr', label: 'USD/INR', match: /usd\s*\/?\s*inr|usdinr/i },
  { key: 'gold', label: 'GOLD', match: /^gold$/i },
  { key: 'brent', label: 'BRENT', match: /brent|crude/i },
  { key: 'bitcoin', label: 'BTC', match: /bitcoin|^btc$/i },
  { key: 'nasdaq', label: 'NASDAQ', match: /nasdaq/i },
  { key: 'sp500', label: 'S&P', match: /^s&p|spx|s\s*&\s*p/i },
  { key: 'vix', label: 'VIX', match: /vix/i },
];

function formatPrice(value, label) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return '—';
  if (/usd\/inr|usdinr/i.test(label)) {
    return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (n >= 1000) return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPct(pct) {
  const n = Number(pct);
  if (!Number.isFinite(n)) return null;
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function matchStripRows(items = []) {
  const used = new Set();
  const rows = [];
  for (const def of STRIP_ORDER) {
    const hit = items.find((row, idx) => {
      if (used.has(idx)) return false;
      return def.match.test(String(row.name || row.label || ''));
    });
    if (!hit || !(Number(hit.price) > 0)) continue;
    const idx = items.indexOf(hit);
    if (idx >= 0) used.add(idx);
    rows.push({
      key: def.key,
      label: def.label,
      price: Number(hit.price),
      percentChange: Number(hit.percentChange ?? hit.change ?? hit.pct),
    });
  }
  return rows;
}

function QuoteChip({ item }) {
  const pct = item.percentChange;
  const up = Number(pct) > 0;
  const down = Number(pct) < 0;
  const tone = up ? 'text-[#087443]' : down ? 'text-[#b42318]' : 'text-[#5d6470]';
  const pctLabel = formatPct(pct);

  return (
    <Link
      to="/market-intelligence"
      className="market-ticker-chip inline-flex shrink-0 flex-col justify-center gap-0.5 border-r border-[#e8eaee] px-4 py-2 hover:bg-[#fafbfc]"
    >
      <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#6b7280] whitespace-nowrap">
        {item.label}
      </span>
      <span className="flex items-center gap-2 whitespace-nowrap">
        <span className="text-[12px] font-semibold tabular-nums text-[#111111]">
          {formatPrice(item.price, item.label)}
        </span>
        {pctLabel ? (
          <span className={`text-[11px] font-semibold tabular-nums ${tone}`}>{pctLabel}</span>
        ) : null}
      </span>
    </Link>
  );
}

/** Sticky scrolling market strip — live prices, no overlapping numbers. */
export default function MarketOutlookStrip() {
  const { items, loading, stale, updatedLabel } = useMarketSnapshot();
  const rows = matchStripRows(items);
  const loop = rows.length ? [...rows, ...rows] : [];
  const badge = stale ? 'Snapshot' : 'Live';

  return (
    <div className="border-b border-[#e6e8ec] bg-white">
      <div className="flex items-stretch">
        <span className="hidden shrink-0 items-center border-r border-[#e8eaee] bg-[#0b1f33] px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-white/80 md:inline-flex">
          {badge}
        </span>

        <div className="market-ticker-viewport min-w-0 flex-1 overflow-hidden">
          {loading && !rows.length ? (
            <span className="block px-4 py-2.5 text-xs text-[#767676]">Loading markets…</span>
          ) : !rows.length ? (
            <span className="block px-4 py-2.5 text-xs text-[#767676]">
              Live unavailable · waiting for first successful snapshot
            </span>
          ) : (
            <div className="market-ticker-track flex w-max items-stretch" aria-label="Live market quotes">
              {stale ? (
                <span className="inline-flex shrink-0 items-center border-r border-[#e8eaee] px-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#9a3412]">
                  Live unavailable{updatedLabel ? ` · ${updatedLabel}` : ''}
                </span>
              ) : null}
              {loop.map((item, i) => (
                <QuoteChip key={`${item.key}-${i}`} item={item} />
              ))}
            </div>
          )}
        </div>

        <Link
          to="/market-intelligence"
          className="hidden shrink-0 items-center border-l border-[#e8eaee] px-3 text-[11px] font-bold text-[#111111] hover:bg-[#fafbfc] lg:inline-flex"
        >
          Markets →
        </Link>
      </div>
    </div>
  );
}
