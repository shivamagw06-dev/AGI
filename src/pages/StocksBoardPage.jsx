import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import MarketsDeskNav from '@/components/markets/MarketsDeskNav';
import usePublishedArticles from '@/hooks/usePublishedArticles';
import { getStocksBoard } from '@/lib/stocksBoardApi';
import './stocksBoard.css';

const TABS = [
  { id: 'all', label: 'All' },
  { id: 'futures', label: 'Futures' },
  { id: 'americas', label: 'Americas' },
  { id: 'emea', label: 'EMEA' },
  { id: 'apac', label: 'APAC' },
  { id: 'india', label: 'India' },
];

const RANGES = [
  { id: '1M', days: 30 },
  { id: '6M', days: 182 },
  { id: 'YTD', days: null },
  { id: '1Y', days: 365 },
];

const LINE_COLORS = ['#ff6600', '#0b6e4f', '#1d4e89', '#7a3e9d', '#b45309', '#0f766e'];

const COLUMNS = [
  { key: 'name', label: 'Name', align: 'left' },
  { key: 'last', label: 'Value', align: 'right' },
  { key: 'change', label: 'Change', align: 'right' },
  { key: 'changePct', label: '% Change', align: 'right' },
  { key: 'monthPct', label: '1 Month', align: 'right' },
  { key: 'yearPct', label: '1 Year', align: 'right' },
  { key: 'timeLabel', label: 'Time', align: 'right' },
];

function tone(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return 'sb-flat';
  return n > 0 ? 'sb-up' : 'sb-down';
}

function money(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function signed(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  const abs = Math.abs(n).toFixed(digits);
  return `${n > 0 ? '+' : n < 0 ? '−' : ''}${abs}`;
}

function signedPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(n).toFixed(2)}%`;
}

function stamp(iso) {
  if (!iso) return 'Awaiting first print';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Awaiting first print';
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Kolkata',
  }) + ' IST';
}

function sortRows(rows, key, dir) {
  if (!key || key === 'catalog') return rows;
  const copy = [...rows];
  copy.sort((a, b) => {
    if (key === 'name') {
      const cmp = String(a.name || '').localeCompare(String(b.name || ''));
      return dir === 'asc' ? cmp : -cmp;
    }
    const av = a[key];
    const bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return dir === 'asc' ? av - bv : bv - av;
  });
  return copy;
}

function historyAfter(history, rangeId) {
  if (!history?.length) return [];
  const last = new Date(`${history.at(-1).t}T00:00:00Z`).getTime();
  let start = last - 365 * 86_400_000;
  if (rangeId === '1M') start = last - 30 * 86_400_000;
  if (rangeId === '6M') start = last - 182 * 86_400_000;
  if (rangeId === 'YTD') start = Date.UTC(new Date(last).getUTCFullYear(), 0, 1);
  return history.filter((point) => new Date(`${point.t}T00:00:00Z`).getTime() >= start);
}

function buildCompareData(rows, ids, rangeId) {
  const series = ids
    .map((id) => rows.find((row) => row.id === id))
    .filter((row) => row?.history?.length > 1);
  if (!series.length) return [];
  const windows = series.map((row) => historyAfter(row.history, rangeId));
  const dates = [...new Set(windows.flatMap((points) => points.map((point) => point.t)))].sort();
  const bases = series.map((row, index) => windows[index][0]?.v || null);
  return dates.map((date) => {
    const point = { date };
    series.forEach((row, index) => {
      const match = windows[index].find((item) => item.t === date)
        || windows[index].filter((item) => item.t <= date).at(-1);
      const base = bases[index];
      point[row.id] = match && base ? Number(((match.v / base) * 100).toFixed(2)) : null;
    });
    return point;
  });
}

function RegionTable({ region, sort, onSort, activeId, onPick }) {
  if (!region?.rows?.length) return null;
  const rows = sortRows(region.rows, sort.key, sort.dir);
  return (
    <section className="sb-region" id={`region-${region.id}`}>
      <div className="sb-region-head">
        <h2>{region.title}</h2>
        {region.blurb ? <p>{region.blurb}</p> : null}
      </div>
      <div className="sb-table-wrap">
        <table className="sb-table">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`${col.align === 'right' ? 'num' : ''} ${sort.key === col.key ? 'is-sorted' : ''}`}
                  onClick={() => onSort(col.key)}
                >
                  {col.label}
                  {sort.key === col.key ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                className={`${activeId === row.id ? 'is-active' : ''} ${row.proxy ? 'is-proxy' : ''}`}
                onClick={() => onPick(row.id)}
              >
                <td className="name">
                  <span className="ticker">{row.ticker}</span>
                  <span className="full">{row.name}</span>
                </td>
                <td className="num">{money(row.last)}</td>
                <td className={`num ${tone(row.change)}`}>{signed(row.change)}</td>
                <td className={`num ${tone(row.changePct)}`}>{signedPct(row.changePct)}</td>
                <td className={`num ${tone(row.monthPct)}`}>{signedPct(row.monthPct)}</td>
                <td className={`num ${tone(row.yearPct)}`}>{signedPct(row.yearPct)}</td>
                <td className="num sb-flat">{row.timeLabel || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function StocksBoardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = TABS.some((item) => item.id === searchParams.get('tab'))
    ? searchParams.get('tab')
    : 'all';
  const [board, setBoard] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [sort, setSort] = useState({ key: 'catalog', dir: 'asc' });
  const [activeId, setActiveId] = useState(null);
  const [compareIds, setCompareIds] = useState([]);
  const [range, setRange] = useState('1Y');
  const { articles, loading: newsLoading } = usePublishedArticles({ limit: 8 });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getStocksBoard()
      .then((payload) => {
        if (cancelled) return;
        setBoard(payload);
        setError(payload?.ok ? null : payload?.error || 'Stocks board unavailable');
        setCompareIds((current) => (
          current.length ? current : payload?.compareDefault || []
        ));
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Stocks board unavailable');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const allRows = useMemo(
    () => Object.values(board?.regions || {}).flatMap((region) => region.rows || []),
    [board]
  );
  const regions = TABS.filter((item) => item.id !== 'all')
    .map((item) => board?.regions?.[item.id])
    .filter(Boolean);
  const visibleRegions = tab === 'all' ? regions : regions.filter((region) => region.id === tab);
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return allRows
      .filter((row) =>
        row.ticker.toLowerCase().includes(q) || row.name.toLowerCase().includes(q)
      )
      .slice(0, 8);
  }, [allRows, query]);

  const compareData = useMemo(
    () => buildCompareData(allRows, compareIds, range),
    [allRows, compareIds, range]
  );

  const onSort = (key) => {
    setSort((prev) => (
      prev.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: key === 'name' ? 'asc' : 'desc' }
    ));
  };

  const pick = (id, opts = {}) => {
    setActiveId(id);
    if (opts.add && !compareIds.includes(id)) {
      setCompareIds((current) => [...current, id].slice(-6));
    }
    const row = allRows.find((item) => item.id === id);
    if (row && tab !== 'all' && tab !== row.region) {
      setSearchParams({ tab: row.region }, { replace: true });
    }
    requestAnimationFrame(() => {
      document.getElementById(`region-${row?.region || tab}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  return (
    <>
      <Helmet>
        <title>Stocks | Agarwal Global Investments</title>
        <meta
          name="description"
          content="AGI world stocks board: Americas, EMEA, APAC and India cash indices with last, change, 1-month and 1-year returns."
        />
      </Helmet>
      <div className="sb-page reuters-page">
        <header className="sb-hero">
          <div className="sb-shell">
            <div className="sb-kicker">
              <span>AGI Markets</span>
              <span className="sb-stamp">Delayed · {stamp(board?.asOf)} · Yahoo reference</span>
            </div>
            <h1>Stocks</h1>
            <p className="sb-lede">
              World and India equity indices with last, day change, 1-month and 1-year return.
              Quotes are delayed market reference, not an exchange or Bloomberg feed.
            </p>
            <MarketsDeskNav />
            <div className="sb-toolbar">
              <div className="sb-tabs" role="tablist" aria-label="Regions">
                {TABS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={tab === item.id ? 'is-active' : undefined}
                    onClick={() => setSearchParams(item.id === 'all' ? {} : { tab: item.id })}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <div className="sb-search">
                <Search size={16} />
                <input
                  type="search"
                  value={query}
                  placeholder="Search indices — Nifty, S&P 500, Nikkei…"
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setOpen(true);
                  }}
                  onFocus={() => setOpen(true)}
                  onBlur={() => setTimeout(() => setOpen(false), 160)}
                />
                {open && matches.length > 0 && (
                  <div className="sb-search-menu">
                    {matches.map((row) => (
                      <button
                        key={row.id}
                        type="button"
                        onMouseDown={() => {
                          setQuery('');
                          pick(row.id, { add: true });
                        }}
                      >
                        <strong>{row.ticker}</strong>
                        <span>{row.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        <div className="sb-shell">
          {loading ? (
            <div className="sb-status">Loading world stocks board…</div>
          ) : error && !allRows.length ? (
            <div className="sb-status is-error">{error}</div>
          ) : (
            <>
              <section className="sb-today">
                <h2>Today in the Markets</h2>
                <div className="sb-chips">
                  {(board?.popular || []).map((row) => (
                    <button
                      key={row.id}
                      type="button"
                      className="sb-chip"
                      onClick={() => pick(row.id, { add: false })}
                    >
                      <b>{row.name}</b>
                      <small className={tone(row.changePct)}>{signedPct(row.changePct)}</small>
                    </button>
                  ))}
                </div>
              </section>

              {visibleRegions.map((region) => (
                <RegionTable
                  key={region.id}
                  region={region}
                  sort={sort}
                  onSort={onSort}
                  activeId={activeId}
                  onPick={(id) => pick(id)}
                />
              ))}

              <div className="sb-grid">
                <section className="sb-news">
                  <h2>Market News</h2>
                  {newsLoading ? (
                    <p className="sb-flat">Loading AGI research…</p>
                  ) : articles.length ? (
                    <ul>
                      {articles.map((article) => (
                        <li key={article.id || article.slug}>
                          <Link to={article.slug ? `/article/${article.slug}` : '/research'}>
                            {article.title}
                          </Link>
                          <span>
                            {article.section || 'AGI Research'}
                            {article.publishedLabel ? ` · ${article.publishedLabel}` : ''}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="sb-flat">No published research notes yet.</p>
                  )}
                </section>

                <section className="sb-compare">
                  <h2>Compare to benchmarks</h2>
                  <div className="sb-compare-tools">
                    <div className="sb-range">
                      {RANGES.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className={range === item.id ? 'is-active' : undefined}
                          onClick={() => setRange(item.id)}
                        >
                          {item.id}
                        </button>
                      ))}
                    </div>
                    <span className="sb-flat">Rebased to 100 at the start of the window.</span>
                  </div>
                  <div style={{ width: '100%', height: 260 }}>
                    {compareData.length ? (
                      <ResponsiveContainer>
                        <LineChart data={compareData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                          <CartesianGrid stroke="#eee" vertical={false} />
                          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#767676' }} minTickGap={28} />
                          <YAxis tick={{ fontSize: 11, fill: '#767676' }} domain={['auto', 'auto']} width={42} />
                          <Tooltip
                            formatter={(value, name) => [`${Number(value).toFixed(2)}`, allRows.find((row) => row.id === name)?.ticker || name]}
                          />
                          {compareIds.map((id, index) => (
                            <Line
                              key={id}
                              type="monotone"
                              dataKey={id}
                              stroke={LINE_COLORS[index % LINE_COLORS.length]}
                              dot={false}
                              strokeWidth={2}
                              connectNulls
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="sb-flat">Select an index to compare.</p>
                    )}
                  </div>
                  <div className="sb-picked">
                    {compareIds.map((id, index) => {
                      const row = allRows.find((item) => item.id === id);
                      return (
                        <button
                          key={id}
                          type="button"
                          style={{ borderColor: LINE_COLORS[index % LINE_COLORS.length] }}
                          onClick={() => setCompareIds((current) => current.filter((item) => item !== id))}
                        >
                          {row?.ticker || id} ×
                        </button>
                      );
                    })}
                  </div>
                </section>
              </div>

              <p className="sb-note">
                {board?.methodology ||
                  'Delayed Yahoo Finance market reference. Not an exchange-owned quote and not Bloomberg. Research discussion only — not investment advice.'}
                {' '}
                {board?.available != null ? `${board.available} of ${board.expected} series available.` : ''}
              </p>
            </>
          )}
        </div>
      </div>
    </>
  );
}
