import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import useMarketIndices from '@/hooks/useMarketIndices';

/**
 * A Bloomberg-shaped Markets dropdown: two link columns and a grid of index
 * tiles.
 *
 * The tiles render from useMarketIndices, which is AGI's own feed, rather than
 * from embedded TradingView widgets. Twelve Single Ticker widgets would be
 * twelve iframes opening twelve connections on hover of a nav menu, each
 * carrying its own mandatory TradingView attribution, and each showing a number
 * that can disagree with the same number elsewhere on the site. The desk spent
 * a week proving how expensive one disagreeing price is.
 *
 * Every link points at a route that exists in App.jsx. A menu that promises
 * pages the router does not serve is worse than a shorter menu.
 */

const NEWS_LINKS = [
  { label: 'Deal Tracker', to: '/deal-tracker' },
  { label: 'Insider Activity', to: '/insider-activity' },
  { label: 'IPO Intelligence', to: '/ipo-intelligence' },
  { label: 'Economics', to: '/economics' },
  { label: 'Company Updates', to: '/company-updates' },
  { label: 'Private Markets', to: '/private-markets' },
];

const DATA_LINKS = [
  { label: 'Market Intelligence', to: '/market-intelligence' },
  { label: 'Sectors', to: '/market-sector-intelligence' },
  { label: 'Global Markets', to: '/global-markets' },
  { label: 'US Market', to: '/us-stock-intelligence' },
  { label: 'Valuation Terminal', to: '/valuation-terminal' },
  { label: 'Macro Intelligence', to: '/macro-intelligence' },
];

function tone(change) {
  const n = Number(change);
  if (!Number.isFinite(n) || n === 0) return 'text-muted-foreground';
  return n > 0 ? 'text-emerald-500' : 'text-red-500';
}

function arrow(change) {
  const n = Number(change);
  if (!Number.isFinite(n) || n === 0) return '';
  return n > 0 ? '▲' : '▼';
}

function formatValue(value) {
  if (value === null || value === undefined || value === '—') return '—';
  const n = Number(String(value).replace(/,/g, ''));
  if (!Number.isFinite(n)) return String(value);
  return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function Tile({ name, value, change }) {
  return (
    <div className="rounded-md bg-muted/60 px-3 py-2.5">
      <div className="truncate text-[13px] font-semibold text-foreground">{name}</div>
      <div className="mt-0.5 text-[15px] tabular-nums text-foreground">{formatValue(value)}</div>
      <div className={`mt-0.5 text-[12px] tabular-nums ${tone(change)}`}>
        {arrow(change)} {Math.abs(Number(change) || 0).toFixed(2)}%
      </div>
    </div>
  );
}

export default function MarketsMenu() {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const closeTimer = useRef(null);
  // Only fetch once the menu has been opened. A nav dropdown should not cost a
  // network request on every page load for data most visitors never see.
  const [everOpened, setEverOpened] = useState(false);
  const { indices, loading } = useMarketIndices(everOpened);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => { if (event.key === 'Escape') setOpen(false); };
    const onClick = (event) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [open]);

  useEffect(() => () => window.clearTimeout(closeTimer.current), []);

  const show = () => {
    window.clearTimeout(closeTimer.current);
    setEverOpened(true);
    setOpen(true);
  };
  // A short grace period, so crossing a gap between the trigger and the panel
  // does not dismiss it.
  const hide = () => {
    closeTimer.current = window.setTimeout(() => setOpen(false), 120);
  };

  return (
    <div
      ref={wrapRef}
      className="relative"
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      <button
        type="button"
        className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-foreground hover:text-primary"
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => (open ? setOpen(false) : show())}
      >
        Markets
        <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open ? (
        <div
          className="absolute left-0 top-full z-50 w-[min(64rem,calc(100vw-2rem))] border border-border bg-background shadow-xl"
          role="menu"
        >
          <div className="grid gap-8 p-6 md:grid-cols-[minmax(0,10rem)_minmax(0,10rem)_1fr]">
            <div>
              <p className="mb-3 text-xs uppercase tracking-wide text-muted-foreground">News</p>
              <ul className="space-y-2.5">
                {NEWS_LINKS.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      className="text-sm text-foreground hover:text-primary"
                      onClick={() => setOpen(false)}
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="mb-3 text-xs uppercase tracking-wide text-muted-foreground">Data</p>
              <ul className="space-y-2.5">
                {DATA_LINKS.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      className="text-sm text-foreground hover:text-primary"
                      onClick={() => setOpen(false)}
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="mb-3 text-xs uppercase tracking-wide text-muted-foreground">
                Top securities
              </p>
              {loading && !indices?.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                  {Array.from({ length: 8 }, (_, i) => (
                    <div key={i} className="h-[68px] animate-pulse rounded-md bg-muted/60" />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                  {(indices || []).map((row) => (
                    <Tile key={row.name} {...row} />
                  ))}
                </div>
              )}
              <p className="mt-3 text-[11px] text-muted-foreground">
                {/* Stated rather than implied. The desk feed is end-of-day for
                    most symbols, and a tile that looks live when it is not is
                    the same failure that showed a five-day-old close. */}
                AGI market feed · delayed unless marked live
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
