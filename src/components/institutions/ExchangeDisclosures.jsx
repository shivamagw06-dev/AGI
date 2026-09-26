import { useEffect, useState } from 'react';

const FEED = 'https://raw.githubusercontent.com/shivamagw06-dev/AGI/investor-valuation-data/investor-filings/latest.json';

export default function ExchangeDisclosures({ investorId }) {
  const [data, setData] = useState(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const load = () => fetch(FEED, { cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) })
      .then(r => { if (!r.ok) throw Error('Unavailable'); return r.json(); })
      .then(value => {
        if (!controller.signal.aborted && value.schemaVersion === 1 && value.profiles && Number.isFinite(Date.parse(value.updatedAt))) { setData(value); setUnavailable(false); }
      }).catch(() => { if (!controller.signal.aborted) setUnavailable(true); });
    load();
    const timer = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { controller.abort(); clearInterval(timer); };
  }, []);
  const profile = data?.profiles?.[`in-${investorId}`];
  const rows = profile?.rows || [];
  const stale = data && Date.now() - Date.parse(data.updatedAt) > 36 * 3600000;
  return <section className="ip-exchange" aria-labelledby="exchange-title">
    <div className="rk-section-title"><div><p className="rk-eyebrow">ORIGINAL EXCHANGE FILINGS</p><h2 id="exchange-title">Latest named disclosures</h2></div><span className="rk-snapshot">NSE · Daily check scheduled at 2 AM IST</span></div>
    <p>Exact shareholder-name matches from company filings. These can cover only part of a portfolio. Similar names, family members and group companies are not combined automatically; a name match alone does not establish identity.</p>
    {data && <p className="rk-table-hint">Checked {new Date(data.updatedAt).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST · {data.checkedCount.toLocaleString()} of {data.issuerCount.toLocaleString()} issuer filings read · {data.pendingCount.toLocaleString()} pending or unavailable. {stale || unavailable ? 'Refresh overdue or unavailable; last successful scan shown.' : ''} BSE-only companies are not covered by this feed.</p>}
    {!data ? <p role="status">{unavailable ? 'The exchange scan is unavailable. Imported holdings remain available below.' : 'Loading exchange disclosures…'}</p> : !rows.length ? <p>No unambiguous exact-name disclosure is available in the scanned filings. This does not mean the investor has no holdings. Group and alias matching may require review.</p> : <div className="rk-table-wrap" role="region" aria-label="Original exchange disclosures" tabIndex={0}><table><thead><tr><th>Company</th><th>Filed shareholder name</th><th>Shares held</th><th>Ownership</th><th>As of</th><th>Original filing</th></tr></thead><tbody>{rows.map(row => <tr key={`${row.symbol}-${row.period}`}><th scope="row">{row.stock}<small className="ip-holder">{row.symbol}</small></th><td>{row.holder}</td><td className="rk-number">{row.quantity.toLocaleString('en-IN')}</td><td className="rk-number">{row.ownershipPct == null ? '—' : `${row.ownershipPct}%`}</td><td>{row.period}</td><td><a href={row.url} target="_blank" rel="noopener noreferrer">NSE disclosure ↗</a><small className="ip-holder">Submitted {row.submitted}</small></td></tr>)}</tbody></table></div>}
    <p className="rk-table-hint">Ownership is dated to each filing, not today. Missing disclosures are not treated as sales. The imported portfolio and its price estimate below remain separate until identity and coverage can be reconciled.</p>
  </section>;
}
