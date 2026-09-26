import ExchangeDisclosures from '@/components/institutions/ExchangeDisclosures';
import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet';
import { Link, useParams } from 'react-router-dom';
import { API_ORIGIN } from '@/config';
import { disclosureStatus, investorSlug, portfolioCsv } from '@/lib/investorProfiles';
import { usaInstitutionalInvestors } from '@/data/usInstitutionalInvestors';
import { indiaInstitutionalInvestors } from '@/data/institutionalInvestors';
import directory from '@/data/investorProfiles/index.json';
import './richKids.css';
import './investorPortfolio.css';
import { useInvestorValuations, valuationFingerprint, valuationMoney, valuationTime, valuationStale } from '@/lib/investorValuations';

const snapshots = import.meta.glob('../data/investorProfiles/holdings/*.json');
const display = value => value == null || value === '' ? '—' : value;

function SummaryEntries({ title, entries }) {
  return <section className="ip-summary-card"><h3>{title}</h3>{entries?.length ? <ul>{entries.map((entry, i) => <li key={i}>{entry.label}</li>)}</ul> : <p>Not supplied</p>}</section>;
}

export default function InvestorPortfolioPage() {
  const { country: market, investorId } = useParams();
  const country = ['in', 'us'].includes(market) ? market.toUpperCase() : null;
  const entry = directory.find(item => item.country === country && item.slug === investorId);
  const category=entry?.category || 'individual';
  const [profile, setProfile] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(0);
  const [history, setHistory] = useState(false);
  const [retry, setRetry] = useState(0);
  const valuations = useInvestorValuations();
  const [fingerprint, setFingerprint] = useState(null);
  useEffect(() => {
    let active = true; setFingerprint(null);
    if (profile) valuationFingerprint(profile).then(value => { if (active) setFingerprint({ profile, value }); }).catch(() => {});
    return () => { active = false; };
  }, [profile]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setProfile(null); setSummary(category==='institutional'?(country==='US'?usaInstitutionalInvestors:indiaInstitutionalInvestors).find(row=>investorSlug(row.name)===investorId)||null:null); setError(''); setQuery(''); setStatus('all'); setPage(0); setHistory(false);
    if (!country) return () => { active = false; controller.abort(); };
    const load = snapshots[`../data/investorProfiles/holdings/${country.toLowerCase()}-${investorId}.json`];
    if (load) load().then(module => { if (active) setProfile(module.default); }).catch(() => { if (active) setError('The holdings snapshot could not load. Please retry.'); });
    fetch(`${API_ORIGIN || ''}/api/intelligence/institutions?country=${country}&category=${category}`, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)]), cache: 'no-store' })
      .then(response => { if (!response.ok) throw Error('Summary unavailable'); return response.json(); })
      .then(data => { if (active && data.country === country && (data.category||'individual')===category && data.published) setSummary(data.rows?.find(row => investorSlug(row.name) === investorId) || null); })
      .catch(() => { /* A dated, bundled source snapshot remains usable offline. */ });
    return () => { active = false; controller.abort(); };
  }, [country, investorId, category, retry]);

  const currentProfile = profile?.country === country && profile.slug === investorId ? profile : null;
  const candidate = valuations?.profiles?.[`${country?.toLowerCase()}-${investorId}`];
  const valuation = currentProfile && fingerprint?.profile === currentProfile && candidate?.fingerprint === fingerprint.value ? candidate : null;
  const rows = useMemo(() => (currentProfile?.rows || []).filter(row =>
    `${row.stock} ${row.holder || ''} ${row.security || ''}`.toLowerCase().includes(query.trim().toLowerCase()) &&
    (status === 'all' || disclosureStatus(row) === status)), [currentProfile, query, status]);
  const statuses = [...new Set((currentProfile?.rows || []).map(disclosureStatus))];
  const shown = rows.slice(page * 50, (page + 1) * 50);
  const currentSummary = summary && investorSlug(summary.name) === investorId ? summary : null;
  const name = currentSummary?.name || entry?.name;
  const periods = (currentProfile?.periods || []).slice(0, history ? undefined : 1);
  const changeQuery = value => { setQuery(value); setPage(0); };
  const download = () => {
    const blob = new Blob(['\uFEFF', portfolioCsv(currentProfile)], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `${country.toLowerCase()}-${investorId}-holdings.csv`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  if (!country || (!entry && !currentSummary)) return <main className="rk-page"><div className="rk-container ip-content"><Link to="/institutions">← All institutions</Link><h1>Investor page unavailable</h1><p>Choose an investor from the current directory.</p></div></main>;
  return <main className="rk-page ip-page">
    <Helmet><title>{name} — Publicly Disclosed Holdings | AGI</title><meta name="description" content={`Explore ${name}'s publicly disclosed holdings, reporting periods and source coverage.`}/></Helmet>
    <header className="rk-hero"><div className="rk-container">
      <Link className="ip-back" to={`/institutions?country=${country}&category=${category}`}>← {country === 'IN' ? 'India' : 'USA'} institutions</Link>
      <p className="rk-eyebrow">AGI / PUBLICLY DISCLOSED HOLDINGS</p><h1>{name}</h1>
      <p className="rk-intro">Explore the disclosed positions and how reported ownership has changed.</p>
      <div className="rk-hero-meta"><span>{country === 'IN' ? 'INDIA · INR' : 'USA · USD'}</span><span>{currentProfile?.reportPeriod ? `SOURCE PERIOD · ${currentProfile.reportPeriod}` : 'REPORTING PERIOD UNAVAILABLE'}</span></div>
    </div></header>
    <div className="rk-container ip-content">
      {country === 'IN' && <ExchangeDisclosures investorId={investorId}/>}
      {error ? <div className="ip-notice" role="alert">{error} <button onClick={() => setRetry(x => x + 1)}>Retry</button></div> : entry && !currentProfile ? <p role="status">Loading disclosed holdings…</p> : null}
      {currentProfile && <>
        <div className="ip-metrics"><div><span>Holdings rows available</span><strong>{currentProfile.rows.length.toLocaleString()}</strong></div><div><span>Source period</span><strong>{currentProfile.reportPeriod || 'Not available'}</strong></div><div><span>Source</span><strong>{currentProfile.sourceLabel}</strong></div><div><span>Retrieved</span><strong>{currentProfile.retrievedAt}</strong></div></div>
        <aside className="ip-notice"><strong>Daily price-based valuation</strong><p>{valuation?.pricedCount ? `${valuationMoney(valuation.value, country)} · ${valuation.pricedCount} of ${valuation.rowCount} disclosed rows priced. ${valuation.pricedCount < valuation.rowCount ? 'Partial subtotal; unpriced holdings are excluded.' : 'Value of the disclosed rows only.'}` : 'Price-based valuation is not available yet. Reported values remain visible below.'}</p>{valuation?.pricedCount > 0 && <p>{valuation.dayChangePct != null && `Price movement: ${valuation.dayChangePct > 0 ? '+' : ''}${valuation.dayChangePct.toFixed(2)}% versus prior trading-session close, using the same disclosed quantities. `}Last successful refresh: {valuationTime(valuations.updatedAt)}. {valuationStale(valuations) ? 'Refresh overdue; showing the last successful snapshot. ' : ''}Oldest included quote: {valuationTime(valuation.oldestPriceAt)}.</p>}<p>Scheduled daily at 2:00 AM IST. Yahoo Finance regular-session prices may be delayed; US prices can be intraday at this time. This estimates disclosed holdings, not personal net worth. Share counts remain as reported; unsupported securities and unresolved corporate actions are excluded.</p></aside>
        <aside className="ip-notice"><strong>{currentProfile.coverageLabel}</strong><p>{currentProfile.coverageNote}</p>{currentProfile.managerName && <p>Filing entity: <strong>{currentProfile.managerName}</strong>. This is the entity’s reported portfolio, not the named individual’s personal assets.</p>}
          {currentProfile.sourceUrl && <a href={currentProfile.sourceUrl} target="_blank" rel="noopener noreferrer">View source disclosure ↗</a>}
        </aside>
        {currentProfile.rows.length > 0 ? <>
          <div className="rk-section-title"><div><p className="rk-eyebrow">THE DISCLOSED BOOK</p><h2>Holdings</h2></div><button className="rk-refresh" onClick={download}>Download holdings CSV</button></div>
          <div className="rk-toolbar"><label>Find a holding<input type="search" value={query} onChange={e => changeQuery(e.target.value)} placeholder="Company, holder or security class"/></label><label>Reported movement<select value={status} onChange={e => { setStatus(e.target.value); setPage(0); }}><option value="all">All disclosed rows</option>{statuses.map(value => <option key={value}>{value}</option>)}</select></label><p aria-live="polite">{rows.length.toLocaleString()} matching rows</p></div>
          {currentProfile.periods.length > 1 && <label className="ip-history"><input type="checkbox" checked={history} onChange={e => setHistory(e.target.checked)}/> Show quarterly ownership history</label>}
          <p className="rk-table-hint">{['sec13f', 'fund-disclosures'].includes(currentProfile.kind) ? 'Value is at the filing date. Portfolio weight is a share of the disclosed book, not ownership of the company.' : 'Values retain source units. Ownership changes are reported percentage-point changes, not investment returns or confirmed trades.'}</p>
          <div className="rk-table-wrap" role="region" aria-label={`${name} holdings`} tabIndex={0}><table><caption className="rk-sr-only">{name} holdings; {currentProfile.reportPeriod}. {currentProfile.coverageLabel}.</caption><thead><tr><th scope="col">Stock / security</th><th scope="col">Holding value {country === 'IN' ? '(INR)' : '(USD)'}</th><th scope="col">Latest price / estimated value</th><th scope="col">Quantity held</th><th scope="col">{currentProfile.kind === 'sec13f' ? 'Security type' : currentProfile.kind === 'fund-disclosures' ? 'Reported share change' : 'Reported change (pp)'}</th>{periods.map(period => <th key={period} scope="col">{period}</th>)}</tr></thead><tbody>{shown.map((row, i) => { const priced = valuation?.rows[currentProfile.rows.indexOf(row)]; return <tr key={`${page}:${i}`}><th scope="row">{row.stock}{(row.holder || row.security) && <small className="ip-holder">{[row.holder, row.security].filter(Boolean).join(' · ')}</small>}</th><td className="rk-number">{display(row.value)}</td><td className="rk-number">{priced?.value != null ? <><strong>{valuationMoney(priced.value, country)}</strong><small className="ip-holder">{country === 'IN' ? '₹' : '$'}{priced.price.toLocaleString()} · {priced.symbol}</small><small className="ip-holder">{valuationTime(priced.priceAt)}</small></> : <span className="rk-muted">{priced?.reason || 'Not priced'}</span>}</td><td className="rk-number">{display(row.quantity)}</td><td className={disclosureStatus(row) === 'Increased' ? 'rk-positive' : disclosureStatus(row) === 'Reduced' ? 'rk-negative' : ''}>{currentProfile.kind === 'sec13f' ? display(row.security) : display(row.change)}</td>{periods.map((period, index) => <td className="rk-number" key={period}>{display(row.history[index])}</td>)}</tr>; })}</tbody></table>{!shown.length && <div className="rk-no-results"><h3>No matching holdings</h3><button onClick={() => { changeQuery(''); setStatus('all'); }}>Clear filters</button></div>}</div>
          {rows.length > 50 && <nav className="ip-pagination" aria-label="Holdings pagination"><button disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</button><span>Page {page + 1} of {Math.ceil(rows.length / 50)}</span><button disabled={(page + 1) * 50 >= rows.length} onClick={() => setPage(p => p + 1)}>Next</button></nav>}
        </> : <div className="rk-empty"><h3>Detailed holdings are not available yet</h3><p>The source could not provide a usable holdings table. The published summary below is limited to the entries supplied by the administrator.</p></div>}
      </>}
      {currentSummary && <section className="ip-summary"><div className="rk-section-title"><div><p className="rk-eyebrow">PUBLISHED DIRECTORY SNAPSHOT</p><h2>Portfolio overview</h2></div><span className="rk-snapshot">Separate snapshot · dates may differ from holdings above</span></div><p>{currentSummary.stocks} stocks reported in the directory · {country === 'IN' ? '₹' : '$'}{currentSummary.value.toLocaleString()} {country === 'IN' ? 'Cr' : 'M'} listed portfolio value.</p><div className="ip-summary-grid"><SummaryEntries title="Sector preferences" entries={currentSummary.sectors}/><SummaryEntries title="Top holdings supplied" entries={currentSummary.holdings}/><SummaryEntries title="Reported additions" entries={currentSummary.bought}/><SummaryEntries title="Reported reductions" entries={currentSummary.sold}/></div></section>}
      <aside className="rk-notes"><h3>Disclosure coverage</h3><p>These are public reporting snapshots, not live positions or complete personal wealth. A missing value is unknown, not zero. “New” can reflect a disclosure threshold; falling below that threshold does not establish a complete exit. Family and associate portfolios can overlap.</p><p>{country === 'IN' ? 'Indian tables retain the source’s quarterly ownership percentages, including historical rows. INR Cr means crore; L means lakh. Holdings values may use a different valuation date from the ownership quarter.' : 'US 13F reports cover specified securities and can omit shorts, private investments and confidential positions. USD B means billion, M means million and K means thousand. A source month is not necessarily the underlying filing quarter.'}</p><p>Detailed snapshots were retrieved on 26 September 2026 and do not refresh with a summary-table paste. Open the linked source to check subsequent filings.</p></aside>
    </div>
  </main>;
}
