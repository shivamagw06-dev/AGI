import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_ORIGIN } from '@/config';
import ManualScreenerTabs from './ManualScreenerTabs';
import './manualLowPe.css';

const decimal = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

function dateLabel(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(`${value}T00:00:00Z`));
}

function isOlderThan180Days(date, asOf) {
  if (!date || !asOf) return false;
  return (Date.parse(`${asOf}T00:00:00Z`) - Date.parse(`${date}T00:00:00Z`)) > 180 * 86400000;
}

function formatNumber(number, suffix = '') {
  return number == null ? '—' : `${decimal.format(number)}${suffix}`;
}

function signed(number) {
  return number == null ? '—' : `${number > 0 ? '+' : ''}${formatNumber(number)}%`;
}

export default function ManualPromoterPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('change-desc');
  const [hideOlder, setHideOlder] = useState(true);

  useEffect(() => {
    let active = true;
    fetch(`${API_ORIGIN || ''}/api/manual-screeners/promoter-holdings`, { cache: 'no-store' })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Unable to load the screener.');
        if (active) setSnapshot(data.snapshot);
      })
      .catch((cause) => { if (active) setError(cause.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const oldCount = useMemo(() => (snapshot?.rows || []).filter((row) => isOlderThan180Days(row.shareholdingDate, snapshot.as_of)).length, [snapshot]);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (snapshot?.rows || []).filter((row) =>
      (!hideOlder || !isOlderThan180Days(row.shareholdingDate, snapshot.as_of)) &&
      (!query || [row.stock, row.nseCode, row.bseCode, row.isin].some((item) => String(item || '').toLowerCase().includes(query)))
    ).sort((left, right) => {
      if (sort === 'name') return left.stock.localeCompare(right.stock);
      if (sort === 'cap-desc') return (right.marketCapCr || 0) - (left.marketCapCr || 0);
      if (sort === 'date-desc') return right.shareholdingDate.localeCompare(left.shareholdingDate);
      return right.promoterChange - left.promoterChange;
    });
  }, [snapshot, search, sort, hideOlder]);

  return <main className="manual-low-pe manual-promoter">
    <ManualScreenerTabs />
    <div className="manual-low-pe__intro"><div><span className="manual-low-pe__kicker">AGI / INDIA / OWNERSHIP</span><h1>Promoter holdings rising</h1><p>Companies in the published table with a reported quarter-on-quarter promoter holding change above 0.1%.</p></div><div className="manual-low-pe__stat"><span>TABLE AS OF</span><strong>{snapshot ? dateLabel(snapshot.as_of) : 'Not published'}</strong><small>{snapshot ? `${integer.format(snapshot.row_count)} rows supplied` : 'Awaiting data'}</small></div></div>
    <div className="manual-low-pe__explain"><strong>Check the filing date.</strong> This is a dated administrator-published list, not a live ownership signal. Each row keeps its supplied shareholding date. Rows more than 180 days older than the table date are hidden by default. An increase alone does not establish investment merit.</div>
    {loading && <p className="manual-low-pe__state">Loading stocks…</p>}
    {error && <p className="manual-low-pe__state" role="alert">{error}</p>}
    {!loading && !error && !snapshot && <p className="manual-low-pe__state">No promoter holdings table has been published yet.</p>}
    {snapshot && <>
      <div className="manual-low-pe__toolbar"><label>Find a stock<input type="search" placeholder="Name, symbol or ISIN" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>Sort by<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="change-desc">Largest increase</option><option value="date-desc">Newest filing date</option><option value="cap-desc">Largest market cap</option><option value="name">Company name</option></select></label><label className="manual-promoter__toggle"><input type="checkbox" checked={hideOlder} onChange={(event) => setHideOlder(event.target.checked)} />Hide older filings ({oldCount})</label><span>{integer.format(filtered.length)} results</span></div>
      <div className="manual-low-pe__scroll"><table><thead><tr><th>#</th><th>Company</th><th>Promoter change <small>QoQ</small></th><th>Shareholding date</th><th>Last traded price <small>₹</small></th><th>Market cap <small>₹ Cr</small></th><th>Latest financial result</th><th>P/E TTM</th><th>P/B adjusted</th><th>Revenue growth <small>QoQ</small></th><th>Profit growth <small>QoQ</small></th><th>NSE</th><th>BSE</th><th>ISIN</th></tr></thead><tbody>{filtered.map((row, index) => <tr key={row.isin}><td>{index + 1}</td><td><strong>{row.stock}</strong></td><td className="manual-low-pe__lead">+{formatNumber(row.promoterChange, '%')}</td><td>{dateLabel(row.shareholdingDate)}{isOlderThan180Days(row.shareholdingDate, snapshot.as_of) && <span className="manual-promoter__old">Older filing</span>}</td><td>{formatNumber(row.ltp)}</td><td>{formatNumber(row.marketCapCr)}</td><td>{dateLabel(row.financialResultDate)}</td><td>{formatNumber(row.peTtm)}</td><td>{formatNumber(row.pbv)}</td><td className={row.revenueGrowth > 0 ? 'up' : row.revenueGrowth < 0 ? 'down' : ''}>{signed(row.revenueGrowth)}</td><td className={row.profitGrowth > 0 ? 'up' : row.profitGrowth < 0 ? 'down' : ''}>{signed(row.profitGrowth)}</td><td>{row.nseCode || '—'}</td><td>{row.bseCode || '—'}</td><td>{row.isin}</td></tr>)}</tbody></table></div>
      {!filtered.length && <p className="manual-low-pe__state">No stocks match those filters.</p>}
      <p className="manual-low-pe__foot">Changes and prices are shown as supplied in the published table. Confirm current disclosures before drawing a conclusion. <Link to="/agi/companies">Company research →</Link></p>
    </>}
  </main>;
}
