import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { usePlus } from '@/contexts/PlusContext';
import { SCREENER_CATEGORIES, screenerPath } from '@/lib/screenerLibrary';
import { libraryRequest, screenerDate } from '@/lib/screenerLibraryApi';
import './screenerLibrary.css';
import './screenerCatalogue.css';
const legacyParameters = {
  'low-pe': ['P/E TTM', '3Y average P/E', '5Y average P/E', '10Y average P/E'],
  'promoter-holdings': ['Promoter holding change', 'Shareholding date', 'Market capitalisation'],
  piotroski: ['Piotroski score', 'Market capitalisation'],
  'cash-flow': ['Six annual free cash flow observations', 'Market capitalisation'],
  momentum: ['Momentum score', 'Volume', 'Weekly return', 'Nifty weekly return'],
};
function Parameters({ screen }) {
  const columns = legacyParameters[screen.slug] || (screen.columns || []).filter(c => !/^(stock name|stock|company name|nse code|bse code|stock code|isin|symbol|ticker|industry name|sector name)$/i.test(c));
  return <div className="sc-parameters">{columns.slice(0, 3).map(c => <span key={c}>{c}</span>)}{columns.length > 3 && <details><summary>+{columns.length - 3} more</summary><div>{columns.slice(3).map(c => <span key={c}>{c}</span>)}</div></details>}{!columns.length && <small>See saved definition</small>}</div>;
}
export default function ScreenerLibrary() {
  const plus = usePlus();
  const [screens, setScreens] = useState([]), [loading, setLoading] = useState(true), [error, setError] = useState('');
  const [search, setSearch] = useState(''), [category, setCategory] = useState('All'), [status, setStatus] = useState('all'), [sort, setSort] = useState('name');
  async function load() { setLoading(true); setError(''); try { setScreens((await libraryRequest()).screens); } catch (e) { setError(e.message); } finally { setLoading(false); } }
  useEffect(() => { load(); }, []);
  const categories = ['All', ...SCREENER_CATEGORIES.filter(c => screens.some(s => s.category === c))];
  const filtered = useMemo(() => screens.filter(s => (category === 'All' || s.category === category) && (!search.trim() || `${s.display_name} ${s.category} ${s.description} ${s.rule_notes || ''}`.toLowerCase().includes(search.trim().toLowerCase())) && (status === 'all' || (status === 'published' ? s.row_count !== null : s.row_count === null))).sort((a, b) => (sort === 'stocks' ? (b.row_count ?? -1) - (a.row_count ?? -1) : sort === 'date' ? (b.as_of || '').localeCompare(a.as_of || '') : 0) || a.display_name.localeCompare(b.display_name)), [screens, search, category, status, sort]);
  return <main className="sl-page sc-library"><header className="sl-header"><div><p className="sl-eyebrow">AGI / RESEARCH TOOLS</p><h1>Screener library<span>.</span></h1><p>Find your next research idea. Compare the rules. Look inside the stock list.</p></div>{plus.isAdmin && <Link className="sl-primary" to="/admin/screener-import">Import / create screener ↗</Link>}</header>
    <div className="sc-summary"><span><b>{screens.length}</b> screeners</span><span><b>{screens.filter(s => s.row_count !== null).length}</b> published lists</span><span><b>{categories.length - 1}</b> categories</span><p>Dated research snapshots · Updated when a new source table is published</p></div>
    <div className="sc-workspace"><aside className="sc-sidebar"><p className="sl-eyebrow">EXPLORE SCREENERS</p><nav aria-label="Screener categories">{categories.map(c => <button key={c} className={category === c ? 'active' : ''} aria-pressed={category === c} onClick={() => setCategory(c)}><span>{c === 'All' ? 'All screeners' : c}</span><b>{c === 'All' ? screens.length : screens.filter(s => s.category === c).length}</b></button>)}</nav><p className="sc-sidebar-note">Open any screener for its intelligence, source and dated holdings. A candidate list is a starting point for research.</p></aside>
    <section className="sc-results" aria-label="Screener catalogue"><div className="sc-toolbar"><label className="sc-search">Search screeners<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search a name, theme or rule…" /></label><label>Availability<select value={status} onChange={e => setStatus(e.target.value)}><option value="all">All screens</option><option value="published">Published data</option><option value="empty">Awaiting import</option></select></label><label>Sort by<select value={sort} onChange={e => setSort(e.target.value)}><option value="name">Name A–Z</option><option value="stocks">Most stocks</option><option value="date">Latest data</option></select></label></div>
    <div className="sc-result-heading"><h2>{category === 'All' ? 'All screeners' : category}</h2><span>{filtered.length} results</span></div>
    {loading && <p role="status">Loading screener library…</p>}{error && <div className="sl-error" role="alert">{error} <button onClick={load}>Retry</button></div>}
    {!loading && !error && <><table className="sc-table"><thead><tr><th>Screener name</th><th>Description & rules</th><th>Table parameters</th><th>Stocks</th><th>Data as of</th></tr></thead><tbody>{filtered.map(s => <tr key={s.slug}><td><div className="sc-name"><span className="sc-icon" aria-hidden="true">▤</span><div><Link to={screenerPath(s)}>{s.display_name} <span aria-hidden="true">↗</span></Link><small>{s.category} · {s.row_count === null ? 'Awaiting import' : 'Published'}</small></div></div></td><td><p>{s.description || 'Open the screener to inspect its saved definition.'}</p>{s.rule_notes && <details className="sc-rules"><summary>Read screening notes</summary><p>{s.rule_notes}</p></details>}</td><td><Parameters screen={s} /></td><td className="sc-number" data-label="Stocks"><strong>{s.row_count === null ? '—' : s.row_count.toLocaleString('en-IN')}</strong></td><td className="sc-date" data-label="Data as of">{screenerDate(s.as_of)}</td></tr>)}</tbody></table>{!filtered.length && <div className="sc-empty"><h3>No matching screeners</h3><p>Try a different search or category.</p><button onClick={() => { setSearch(''); setCategory('All'); setStatus('all'); }}>Clear filters</button></div>}</>}
    </section></div>
  </main>;
}
