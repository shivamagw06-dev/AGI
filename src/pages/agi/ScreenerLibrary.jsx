import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, BarChart3, CandlestickChart, CheckCircle2, Coins, Compass, Gem, Layers, LayoutGrid, ShieldCheck, SlidersHorizontal, Target, TrendingUp, Users } from 'lucide-react';
import { usePlus } from '@/contexts/PlusContext';
import { SCREENER_CATEGORIES, screenerPath } from '@/lib/screenerLibrary';
import { libraryRequest, screenerDate } from '@/lib/screenerLibraryApi';
import './screenerLibrary.css';
import './screenerCatalogue.css';
const categoryVisuals = {
  All: [LayoutGrid, '#315c97', '#eaf1fc'], Value: [Gem, '#986321', '#fff3dc'],
  Growth: [TrendingUp, '#17745b', '#e3f6ed'], Quality: [ShieldCheck, '#6550a3', '#f0ebfc'],
  Momentum: [Activity, '#b74e33', '#fff0e9'], Shareholding: [Users, '#216e9b', '#e5f3fc'],
  Technicals: [BarChart3, '#236e83', '#e4f4f8'], 'Moving averages': [Activity, '#4f60b2', '#edf0fc'],
  Candlesticks: [CandlestickChart, '#9f4c88', '#faedf6'], Dividends: [Coins, '#646e19', '#f1f5dd'],
  'Analyst estimates': [Target, '#2f7168', '#e7f5f1'], 'Risk flags': [AlertTriangle, '#a94e42', '#fceeea'],
  'Multi-factor': [Layers, '#725393', '#f1eafa'],
};
function visualStyle(category) { const [, ink, tint] = categoryVisuals[category] || categoryVisuals.All; return { '--sc-ink': ink, '--sc-tint': tint }; }
function CategoryIcon({ category, className = '' }) { const [Icon] = categoryVisuals[category] || categoryVisuals.All; return <span className={`sc-category-icon ${className}`} style={visualStyle(category)} aria-hidden="true"><Icon size={19} strokeWidth={1.8} /></span>; }
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
  return <main className="sl-page sc-library"><header className="sl-header sc-hero"><div className="sc-hero-copy"><p className="sl-eyebrow">AGI / RESEARCH TOOLS</p><h1>Find your next<br /><em>investment idea.</em></h1><p>Explore the screener library. Compare the rules, then look inside every stock list.</p></div><div className="sc-hero-art" aria-hidden="true"><span className="sc-orbit sc-orbit-one" /><span className="sc-orbit sc-orbit-two" /><span className="sc-hero-symbol"><SlidersHorizontal size={43} strokeWidth={1.4} /></span><span className="sc-floating sc-float-one"><TrendingUp size={23} /></span><span className="sc-floating sc-float-two"><Gem size={21} /></span><span className="sc-floating sc-float-three"><ShieldCheck size={21} /></span></div>{plus.isAdmin && <Link className="sl-primary" to="/admin/screener-import">Import / create screener ↗</Link>}</header>
    <div className="sc-summary"><div className="sc-stat"><span className="sc-stat-icon"><LayoutGrid size={21} /></span><span><b>{screens.length}</b><small>Screeners to explore</small></span></div><div className="sc-stat"><span className="sc-stat-icon"><CheckCircle2 size={21} /></span><span><b>{screens.filter(s => s.row_count !== null).length}</b><small>Published stock lists</small></span></div><div className="sc-stat"><span className="sc-stat-icon"><Compass size={21} /></span><span><b>{categories.length - 1}</b><small>Research categories</small></span></div><p>Research snapshots<br /><strong>Updated with each source import</strong></p></div>
    <div className="sc-workspace"><aside className="sc-sidebar"><p className="sl-eyebrow">EXPLORE SCREENERS</p><nav aria-label="Screener categories">{categories.map(c => <button key={c} className={category === c ? 'active' : ''} aria-pressed={category === c} onClick={() => setCategory(c)}><CategoryIcon category={c} /><span>{c === 'All' ? 'All screeners' : c}</span><b>{c === 'All' ? screens.length : screens.filter(s => s.category === c).length}</b></button>)}</nav><p className="sc-sidebar-note">Open any screener for its intelligence, source and dated holdings. A candidate list is a starting point for research.</p></aside>
    <section className="sc-results" aria-label="Screener catalogue"><div className="sc-toolbar"><label className="sc-search">Search screeners<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search a name, theme or rule…" /></label><label>Availability<select value={status} onChange={e => setStatus(e.target.value)}><option value="all">All screens</option><option value="published">Published data</option><option value="empty">Awaiting import</option></select></label><label>Sort by<select value={sort} onChange={e => setSort(e.target.value)}><option value="name">Name A–Z</option><option value="stocks">Most stocks</option><option value="date">Latest data</option></select></label></div>
    <div className="sc-result-heading"><h2>{category === 'All' ? 'All screeners' : category}</h2><span>{filtered.length} results</span></div>
    {loading && <p role="status">Loading screener library…</p>}{error && <div className="sl-error" role="alert">{error} <button onClick={load}>Retry</button></div>}
    {!loading && !error && <><table className="sc-table"><thead><tr><th>Screener name</th><th>Description & rules</th><th>Table parameters</th><th>Stocks</th><th>Data as of</th></tr></thead><tbody>{filtered.map(s => <tr key={s.slug} style={visualStyle(s.category)}><td><div className="sc-name"><CategoryIcon category={s.category} className="sc-row-icon" /><div><Link to={screenerPath(s)}>{s.display_name} <span aria-hidden="true">↗</span></Link><div className="sc-row-badges"><span className="sc-category-badge">{s.category}</span><span className={s.row_count === null ? 'sc-pending' : 'sc-published'}>{s.row_count === null ? 'Awaiting import' : 'Published'}</span></div></div></div></td><td><p>{s.description || 'Open the screener to inspect its saved definition.'}</p>{s.rule_notes && <details className="sc-rules"><summary>Read screening notes</summary><p>{s.rule_notes}</p></details>}</td><td><Parameters screen={s} /></td><td className="sc-number" data-label="Stocks"><strong>{s.row_count === null ? '—' : s.row_count.toLocaleString('en-IN')}</strong><small>stocks</small></td><td className="sc-date" data-label="Data as of">{screenerDate(s.as_of)}</td></tr>)}</tbody></table>{!filtered.length && <div className="sc-empty"><h3>No matching screeners</h3><p>Try a different search or category.</p><button onClick={() => { setSearch(''); setCategory('All'); setStatus('all'); }}>Clear filters</button></div>}</>}
    </section></div>
  </main>;
}
