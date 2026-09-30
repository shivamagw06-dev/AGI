import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_ORIGIN } from '@/config';
import ManualScreenerTabs from './ManualScreenerTabs';
import './manualLowPe.css';

const integer = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });

function percent(value) {
  return value == null ? '—' : `${value > 0 ? '+' : ''}${decimal.format(value)}%`;
}

function changeClass(value) {
  return value > 0 ? 'up' : value < 0 ? 'down' : '';
}

function dateLabel(date) {
  if (!date) return 'Not published';
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${date}T00:00:00Z`));
}

export default function ManualLowPePage() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [sort, setSort] = useState('pe-asc');

  useEffect(() => {
    let active = true;
    fetch(`${API_ORIGIN || ''}/api/manual-screeners/low-pe`, { cache: 'no-store' })
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
      (!sector || row.sector === sector) &&
      (!query || [row.stock, row.nseCode, row.bseCode, row.isin, row.sector].some((value) => String(value || '').toLowerCase().includes(query)))
    ).sort((left, right) => {
      if (sort === 'name') return left.stock.localeCompare(right.stock);
      if (sort === 'cap-desc') return (right.marketCapCr || 0) - (left.marketCapCr || 0);
      if (sort === 'discount-desc') return (1 - right.peTtm / right.pe10y) - (1 - left.peTtm / left.pe10y);
      return left.peTtm - right.peTtm;
    });
  }, [snapshot, search, sector, sort]);

  return <main className="manual-low-pe">
    <ManualScreenerTabs />
    <div className="manual-low-pe__intro"><div><span className="manual-low-pe__kicker">AGI / INDIA / VALUATION</span><h1>Low P/E stocks</h1><p>Stocks in the published table whose current P/E is below their 3, 5 and 10-year averages.</p></div><div className="manual-low-pe__stat"><span>DATA AS OF</span><strong>{dateLabel(snapshot?.as_of)}</strong><small>{snapshot ? `${integer.format(snapshot.row_count)} stocks` : 'Awaiting data'}</small></div></div>
    <div className="manual-low-pe__explain"><strong>A dated screen, not a live signal.</strong> Figures reflect the last administrator-published table and change only when a new table is published. P/E comparisons alone do not establish that a stock is undervalued.</div>
    {loading && <p className="manual-low-pe__state">Loading stocks…</p>}
    {error && <p className="manual-low-pe__state" role="alert">{error}</p>}
    {!loading && !error && !snapshot && <p className="manual-low-pe__state">No low P/E table has been published yet.</p>}
    {snapshot && <>
      <div className="manual-low-pe__toolbar"><label>Find a stock<input type="search" placeholder="Name, symbol, ISIN or sector" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>Sector<select value={sector} onChange={(event) => setSector(event.target.value)}><option value="">All sectors</option>{sectors.map((value) => <option key={value}>{value}</option>)}</select></label><label>Sort by<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="pe-asc">Lowest P/E</option><option value="discount-desc">Largest gap vs 10Y</option><option value="cap-desc">Largest market cap</option><option value="name">Company name</option></select></label><span>{integer.format(filtered.length)} results</span></div>
      <div className="manual-low-pe__scroll"><table><thead><tr><th>#</th><th>Company</th><th>P/E TTM</th><th>3Y avg</th><th>5Y avg</th><th>10Y avg</th><th>Gap vs 10Y</th><th>Day</th><th>Week</th><th>Quarter</th><th>Market cap <small>₹ Cr</small></th><th>Sector</th><th>Revenue growth <small>Qtr YoY</small></th><th>Profit growth <small>Qtr YoY</small></th><th>NSE</th><th>BSE</th><th>ISIN</th></tr></thead><tbody>{filtered.map((row, index) => <tr key={row.isin}><td>{index + 1}</td><td><strong>{row.stock}</strong></td><td className="manual-low-pe__lead">{decimal.format(row.peTtm)}</td><td>{decimal.format(row.pe3y)}</td><td>{decimal.format(row.pe5y)}</td><td>{decimal.format(row.pe10y)}</td><td>{percent((row.peTtm / row.pe10y - 1) * 100)}</td><td className={changeClass(row.dayChange)}>{percent(row.dayChange)}</td><td className={changeClass(row.weekChange)}>{percent(row.weekChange)}</td><td className={changeClass(row.quarterChange)}>{percent(row.quarterChange)}</td><td>{row.marketCapCr == null ? '—' : decimal.format(row.marketCapCr)}</td><td>{row.sector}</td><td className={changeClass(row.revenueGrowth)}>{percent(row.revenueGrowth)}</td><td className={changeClass(row.profitGrowth)}>{percent(row.profitGrowth)}</td><td>{row.nseCode || '—'}</td><td>{row.bseCode || '—'}</td><td>{row.isin}</td></tr>)}</tbody></table></div>
      {!filtered.length && <p className="manual-low-pe__state">No stocks match those filters.</p>}
      <p className="manual-low-pe__foot">P/E and market cap are as supplied in the dated table. Explore a company before making an investment decision. <Link to="/agi/companies">Company research →</Link></p>
    </>}
  </main>;
}
