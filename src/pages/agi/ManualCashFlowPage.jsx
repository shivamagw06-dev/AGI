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

export default function ManualCashFlowPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [cashFilter, setCashFilter] = useState('');
  const [sort, setSort] = useState('cap-desc');

  useEffect(() => {
    let active = true;
    fetch(`${API_ORIGIN || ''}/api/manual-screeners/cash-flow`, { cache: 'no-store' })
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
      (!sector || row.sector === sector) && (!cashFilter || (cashFilter === 'positive' ? row.fcf.every((value) => value > 0) : row.fcf.some((value) => value === 0))) &&
      (!query || [row.stock, row.nseCode, row.bseCode, row.stockCode, row.isin, row.industry, row.sector]
        .some((item) => String(item || '').toLowerCase().includes(query)))
    ).sort((left, right) => {
      if (sort === 'name') return left.stock.localeCompare(right.stock);
      if (sort === 'cap-desc') return right.marketCapCr - left.marketCapCr;
      if (sort === 'price-asc') return left.price - right.price;
      return right.fcf[0] - left.fcf[0];
    });
  }, [snapshot, search, sector, cashFilter, sort]);

  return <main className="manual-low-pe manual-cash-flow">
    <ManualScreenerTabs />
    <div className="manual-low-pe__intro"><div><span className="manual-low-pe__kicker">AGI / INDIA / FINANCIAL STRENGTH</span><h1>Consistent Free Cash Flow</h1><p>Six annual free cash flow observations for the companies in the uploaded list.</p></div><div className="manual-low-pe__stat"><span>TABLE AS OF</span><strong>{dateLabel(snapshot?.as_of)}</strong><small>{snapshot ? `${integer.format(snapshot.row_count)} stocks` : 'Awaiting data'}</small></div></div>
    <div className="manual-low-pe__explain">Free cash flow is shown in ₹ crore. “Latest” and earlier periods follow the workbook’s relative annual labels; exact fiscal year-end dates were not supplied. The complete uploaded list includes companies with zero values. Use the cash-flow filter to show only companies positive in all six periods.</div>
    {loading && <p className="manual-low-pe__state">Loading stocks…</p>}
    {error && <p className="manual-low-pe__state" role="alert">{error}</p>}
    {!loading && !error && !snapshot && <p className="manual-low-pe__state">No cash flow table has been published yet.</p>}
    {snapshot && <>
      <div className="manual-low-pe__toolbar"><label>Find a stock<input type="search" placeholder="Name, symbol, ISIN or industry" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>Cash flow<select value={cashFilter} onChange={(event) => setCashFilter(event.target.value)}><option value="">All supplied companies</option><option value="positive">Positive in all six periods</option><option value="zero">Includes zero values</option></select></label><label>Sector<select value={sector} onChange={(event) => setSector(event.target.value)}><option value="">All sectors</option>{sectors.map((item) => <option key={item}>{item}</option>)}</select></label><label>Sort by<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="fcf-desc">Highest latest free cash flow</option><option value="cap-desc">Largest market cap</option><option value="price-asc">Lowest price</option><option value="name">Company name</option></select></label><span>{integer.format(filtered.length)} results</span></div>
      <div className="manual-low-pe__scroll"><table><thead><tr><th>#</th><th>Company</th>{['Latest', '1 year ago', '2 years ago', '3 years ago', '4 years ago', '5 years ago'].map((label) => <th key={label}>FCF {label} <small>₹ Cr</small></th>)}<th>Sector</th><th>Industry</th><th>Price <small>₹</small></th><th>Market cap <small>₹ Cr</small></th><th>NSE</th><th>BSE</th><th>Stock code</th><th>ISIN</th></tr></thead><tbody>{filtered.map((row, index) => <tr key={row.isin}><td>{index + 1}</td><td><strong>{row.stock}</strong></td>{row.fcf.map((value, index) => <td key={index}>{decimal.format(value)}</td>)}<td>{row.sector}</td><td>{row.industry}</td><td>{decimal.format(row.price)}</td><td>{decimal.format(row.marketCapCr)}</td><td>{row.nseCode || '—'}</td><td>{row.bseCode || '—'}</td><td>{row.stockCode || '—'}</td><td>{row.isin}</td></tr>)}</tbody></table></div>
      {!filtered.length && <p className="manual-low-pe__state">No stocks match those filters.</p>}
      <p className="manual-low-pe__foot">Cash flows, prices and market caps reflect the dated workbook and update when an administrator publishes a replacement.</p>
    </>}
  </main>;
}
