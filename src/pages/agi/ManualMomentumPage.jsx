import { useEffect, useMemo, useState } from 'react';
import { API_ORIGIN } from '@/config';
import ManualScreenerTabs from './ManualScreenerTabs';
import './manualLowPe.css';

const decimal = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

function dateLabel(date) {
  if (!date) return 'Not published';
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(`${date}T00:00:00Z`));
}

export default function ManualMomentumPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [score, setScore] = useState('');
  const [sort, setSort] = useState('score-desc');

  useEffect(() => {
    let active = true;
    fetch(`${API_ORIGIN || ''}/api/manual-screeners/momentum`, { cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Unable to load the screener.');
        if (active) setSnapshot(data.snapshot);
      })
      .catch((cause) => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const sectors = useMemo(() => [...new Set((snapshot?.rows || []).map((row) => row.sector))].sort(), [snapshot]);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (snapshot?.rows || []).filter((row) =>
      (!sector || row.sector === sector) && (!score || (score === 'outperform' ? row.relativeWeekChange > 0 : row.relativeWeekChange <= 0)) &&
      (!query || [row.stock, row.nseCode, row.bseCode, row.stockCode, row.isin, row.industry, row.sector]
        .some((item) => String(item || '').toLowerCase().includes(query)))
    ).sort((left, right) => {
      if (sort === 'weekly-desc') return right.weekChange - left.weekChange;
      if (sort === 'volume-desc') return right.volume - left.volume;
      if (sort === 'name') return left.stock.localeCompare(right.stock);
      if (sort === 'cap-desc') return right.marketCapCr - left.marketCapCr;
      if (sort === 'price-asc') return left.price - right.price;
      return right.score - left.score || right.marketCapCr - left.marketCapCr;
    });
  }, [snapshot, search, sector, score, sort]);

  return <main className="manual-low-pe manual-momentum">
    <ManualScreenerTabs />
    <div className="manual-low-pe__intro"><div><span className="manual-low-pe__kicker">AGI / INDIA / MOMENTUM</span><h1>Momentum Stocks</h1><p>Compare supplied momentum scores, trading volume and weekly returns.</p></div><div className="manual-low-pe__stat"><span>TABLE AS OF</span><strong>{dateLabel(snapshot?.as_of)}</strong><small>{snapshot ? `${integer.format(snapshot.row_count)} stocks` : 'Awaiting data'}</small></div></div>
    <div className="manual-low-pe__explain">Data comes from the latest administrator-published workbook. Momentum scores are supplied scores. Relative weekly performance is the stock’s weekly change minus Nifty 50’s weekly change, in percentage points.</div>
    {loading && <p className="manual-low-pe__state">Loading stocks…</p>}
    {error && <p className="manual-low-pe__state" role="alert">{error}</p>}
    {!loading && !error && !snapshot && <p className="manual-low-pe__state">No Momentum table has been published yet.</p>}
    {snapshot && <>
      <div className="manual-low-pe__toolbar"><label>Find a stock<input type="search" placeholder="Name, symbol, ISIN or industry" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>Weekly performance<select value={score} onChange={(event) => setScore(event.target.value)}><option value="">All stocks</option><option value="outperform">Outperforming Nifty 50</option><option value="underperform">At or below Nifty 50</option></select></label><label>Sector<select value={sector} onChange={(event) => setSector(event.target.value)}><option value="">All sectors</option>{sectors.map((item) => <option key={item}>{item}</option>)}</select></label><label>Sort by<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="score-desc">Score, then market cap</option><option value="weekly-desc">Highest weekly return</option><option value="volume-desc">Highest day volume</option><option value="cap-desc">Largest market cap</option><option value="price-asc">Lowest price</option><option value="name">Company name</option></select></label><span>{integer.format(filtered.length)} results</span></div>
      <div className="manual-low-pe__scroll"><table><thead><tr><th>#</th><th>Company</th><th>Supplied momentum score</th><th>Day volume</th><th>Week change %</th><th>Nifty 50 week %</th><th>Relative week <small>pp</small></th><th>Sector</th><th>Industry</th><th>Price <small>₹</small></th><th>Market cap <small>₹ Cr</small></th><th>NSE</th><th>BSE</th><th>Stock code</th><th>ISIN</th></tr></thead><tbody>{filtered.map((row, index) => <tr key={row.isin}><td>{index + 1}</td><td><strong>{row.stock}</strong></td><td className="manual-low-pe__lead"><span className="manual-momentum__score">{decimal.format(row.score)}</span></td><td>{integer.format(row.volume)}</td><td>{decimal.format(row.weekChange)}%</td><td>{decimal.format(row.niftyWeekChange)}%</td><td>{decimal.format(row.relativeWeekChange)}</td><td>{row.sector}</td><td>{row.industry}</td><td>{decimal.format(row.price)}</td><td>{decimal.format(row.marketCapCr)}</td><td>{row.nseCode || '—'}</td><td>{row.bseCode || '—'}</td><td>{row.stockCode || '—'}</td><td>{row.isin}</td></tr>)}</tbody></table></div>
      {!filtered.length && <p className="manual-low-pe__state">No stocks match those filters.</p>}
      <p className="manual-low-pe__foot">Scores are shown as supplied in the dated workbook. Check the latest company filings before making an investment decision.</p>
    </>}
  </main>;
}
