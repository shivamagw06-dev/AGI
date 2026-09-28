import React, { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Search, Trophy, Layers, Plus, Check } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { API_ORIGIN } from '@/config';
import './financeTools.css';

export const categories = ['Leaderboards', 'SEO', 'Marketing', 'Productivity', 'Agents', 'Developer', 'Crypto', 'Other', 'Games', 'Health', 'Business', 'Ecommerce', 'Travel', 'Directories', 'Agencies', 'AI Media', 'Education', 'Social', 'People', 'Design', 'Hiring', 'Domains', 'Sales', 'Security', 'News', 'Real Estate', 'Writing', 'Audio', 'Analytics', 'Product Management'];
const samples = [
  { id: 'a', name: 'Example Research Studio', description: 'Company filings and earnings transcripts in one searchable workspace.', category: 'Analytics', amount: 2500, today: 500 },
  { id: 'b', name: 'Example Model Desk', description: 'Forecasts, valuation templates and scenario tools for financial analysts.', category: 'Productivity', amount: 1500, today: 750 },
  { id: 'c', name: 'Example Ledger', description: 'A simpler way for finance teams to reconcile and review their accounts.', category: 'Business', amount: 500, today: 0 },
];
const money = n => `₹${Number(n).toLocaleString('en-IN')}`;
export async function toolsRequest(path, options = {}) {
  const { data } = await supabase.auth.getSession();
  if (!data?.session?.access_token) throw Error('Please sign in with your AGI account to continue.');
  const r = await fetch(`${API_ORIGIN || ''}/api/intelligence/finance-tools${path}`, {
    ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${data.session.access_token}` }, signal: AbortSignal.timeout(25000),
  });
  const value = await r.json();
  if (!r.ok) throw Error(value.error || value.detail || 'Unable to complete this request.');
  return value;
}
export default function FinanceToolsPage() {
  const [category, setCategory] = useState('All'), [query, setQuery] = useState(''), [period, setPeriod] = useState('all');
  const [explore, setExplore] = useState(false);
  const [example, setExample] = useState(false), [board, setBoard] = useState(null), [loadError, setLoadError] = useState(''), [retry, setRetry] = useState(0);
  const [form, setForm] = useState({ name: '', url: '', description: '', category: categories[0], budget: '', authorized: false });
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState(''), [mine, setMine] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoadError('');
    fetch(`${API_ORIGIN || ''}/api/intelligence/finance-tools/board`, { signal: controller.signal, cache: 'no-store' })
      .then(async r => { if (!r.ok) throw Error(); return r.json(); }).then(setBoard)
      .catch(e => { if (e.name !== 'AbortError') setLoadError('The board could not load. Please try again.'); });
    return () => controller.abort();
  }, [retry]);
  const rows = (example ? samples : board?.listings || []).map(r => ({ ...r, displayed: period === 'today' ? r.today : r.amount }))
    .filter(r => r.displayed > 0 && (category === 'All' || r.category === category) && `${r.name} ${r.description}`.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => b.displayed - a.displayed);
  const change = e => setForm(f => ({ ...f, [e.target.name]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      const result = await toolsRequest('/applications', { method: 'POST', body: JSON.stringify({ ...form, budget: Number(form.budget) }) });
      setMessage(result.duplicate ? 'You already submitted this website. View its status under My submissions.' : 'Application received. We’ll review it and contact you at your account email with the next steps.');
      setMine(null);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function loadMine() {
    setError('');
    try { setMine((await toolsRequest('/mine')).applications); } catch (e) { setError(e.message); }
  }
  return <main className="ft">
    <Helmet><title>AGI Tools — Sponsored Directory</title><meta name="description" content="Discover tools and submit your business to the AGI sponsored directory for review." /></Helmet>
    <div className="ft-top"><Link to="/" className="ft-wordmark">AGI<span>/ TOOLS</span></Link><a href="#ft-rules">How it works</a></div>
    <header className="ft-heading"><div><p className="ft-eyebrow">THE TOOLS DIRECTORY</p><h1>Useful tools.<br/><em>A place to be seen.</em></h1><p>Find your next useful tool. Put your business in front of the people doing the work.</p></div><a className="ft-primary" href="#ft-submit"><Plus size={18}/> Submit your company</a></header>
    <nav className="ft-categories" aria-label="Tool categories">{['All', ...categories.slice(0, 9), ...(category !== 'All' && !categories.slice(0, 9).includes(category) ? [category] : [])].map(c => <button key={c} aria-pressed={category === c} onClick={() => setCategory(c)}>{c}</button>)}<button className="ft-explore" aria-expanded={explore} aria-controls="ft-category-explorer" onClick={() => setExplore(v => !v)}>Explore {explore ? '−' : '+'}</button></nav>
    {explore && <section id="ft-category-explorer" className="ft-category-explorer" aria-label="Explore all categories"><h2>Explore all categories</h2><div>{categories.map(c => <button key={c} aria-pressed={category === c} onClick={() => { setCategory(c); setExplore(false); }}>{c}</button>)}</div></section>}
    <div className="ft-workspace"><section className="ft-board" aria-label="Sponsored leaderboard">
      <div className="ft-board-head"><div><h2>Sponsored leaderboard</h2><p>Placement reflects verified sponsorship spend, never an AGI endorsement.</p></div><Trophy size={24}/></div>
      <div className="ft-toolbar"><div className="ft-period">{[['all', 'All time'], ['today', 'Today · IST']].map(([id, label]) => <button key={id} aria-pressed={period === id} onClick={() => setPeriod(id)}>{label}</button>)}</div><label className="ft-search"><Search size={16}/><input aria-label="Search tools" value={query} onChange={e => setQuery(e.target.value)} placeholder="Find a tool…" /></label></div>
      <label className="ft-demo-toggle"><input type="checkbox" checked={example} onChange={e => setExample(e.target.checked)}/> Preview with fictional examples</label>
      {example && <p className="ft-example-note">EXAMPLE BOARD · These businesses and amounts are fictional. They are not advertisers or payments.</p>}
      {!example && loadError ? <div role="alert" className="ft-empty"><p>{loadError}</p><button onClick={() => setRetry(r => r + 1)}>Try again</button></div> : !example && !board ? <p role="status" className="ft-empty">Loading the directory…</p> : rows.length ? <ol className="ft-list">{rows.map((r, i) => <li key={r.id}>
        <span className="ft-rank">{String(i + 1).padStart(2, '0')}</span><div className="ft-monogram" aria-hidden="true">{r.name.replace('Example ', '').slice(0, 1)}</div><div className="ft-list-copy"><span className="ft-list-category">{r.category}</span><h3>{r.name}</h3><p>{r.description}</p><small>{example ? 'Fictional listing' : 'Sponsored placement'}</small></div><div className="ft-amount"><strong>{money(r.displayed)}</strong><span>{period === 'today' ? 'today’s spend' : 'total spend'}</span><ArrowUpRight size={20}/></div>
      </li>)}</ol> : <div className="ft-empty"><Layers size={32}/><h3>{query || category !== 'All' ? 'No matching listings yet.' : 'The first spot is still open.'}</h3><p>{query || category !== 'All' ? 'Try another category or clear your search.' : 'There are no sponsored listings yet. Submit your company for review.'}</p><a href="#ft-submit">Submit your company <ArrowUpRight size={16}/></a></div>}
      <div className="ft-board-foot"><span>{example ? 'Example data' : 'Only verified paid placements will appear'}</span><a href="#ft-rules">Read the rules ↓</a></div>
    </section>
    <aside id="ft-submit" className="ft-submit"><p className="ft-eyebrow">FOR COMPANIES & BUILDERS</p><h2>Get on the list.</h2><p>Tell us about your product. Applying is free. We’ll review your application and contact you by email with the next steps, including UPI payment details if approved.</p>
      <form onSubmit={submit}>
        <label>Company or product name<input required name="name" minLength={2} maxLength={70} value={form.name} onChange={change} placeholder="Your product" /></label>
        <label>Website<input required name="url" type="url" maxLength={300} value={form.url} onChange={change} placeholder="https://yourcompany.com" /></label>
        <label>Category<select name="category" value={form.category} onChange={change}>{categories.map(c => <option key={c}>{c}</option>)}</select></label>
        <label>What does it do?<textarea required name="description" minLength={20} maxLength={280} value={form.description} onChange={change} placeholder="Who it helps and what they can do with it." rows={3}/></label>
        <label>Indicative sponsorship budget (₹)<input required name="budget" type="number" min={1} max={1000000} step={1} value={form.budget} onChange={change} placeholder="Enter an amount" /></label>
        <small>A non-binding budget, not a bid or payment. Final prices and terms will be shown before purchase.</small>
        <label className="ft-consent"><input required name="authorized" type="checkbox" checked={form.authorized} onChange={change}/><span>I own or am authorised to represent this business. AGI may use my account email to respond to this application.</span></label>
        <button className="ft-primary" disabled={busy}>{busy ? 'Submitting…' : 'Submit for review'}<ArrowUpRight size={18}/></button>
      </form>
      {message && <p className="ft-success" role="status"><Check size={16}/>{message}</p>}{error && <p className="ft-error" role="alert">{error}</p>}
      <div className="ft-account-links"><Link to="/login?next=/finance-tools">Sign in / create account</Link><button onClick={loadMine}>My submissions</button></div>
      {mine && <section className="ft-mine"><h3>Your applications</h3>{mine.length ? mine.map(r => <div key={r.id}><strong>{r.name}</strong><span>{r.status === 'reviewed' ? 'Reviewed' : r.status}</span></div>) : <p>No applications yet.</p>}</section>}
      <p className="ft-private">Your application and email stay private. Submission does not reserve a rank. <Link to="/privacy">Privacy policy</Link></p>
    </aside></div>
    <section id="ft-rules" className="ft-rules"><div><p className="ft-eyebrow">A CLEAR EXCHANGE</p><h2>Visibility, with the rules<br/>out in the open.</h2></div><div><details open><summary>How will rankings work?</summary><p>The planned leaderboard will order approved listings by verified sponsorship payments. Submitting an application or indicating a budget does not create a listing or reserve a rank. We’ll confirm placement details directly after review.</p></details><details><summary>Does paying mean AGI recommends my product?</summary><p>No. These are sponsored placements. Payment will not influence AGI’s company research, investor data or investment analysis.</p></details><details><summary>What can I submit?</summary><p>Products, software and services across the listed categories that you are authorised to represent. We review applications for relevance and misleading claims. Approval is not guaranteed.</p></details><details><summary>What am I committing to now?</summary><p>Submitting an application is free and your budget expresses interest only. After review, AGI will contact you directly with the placement terms and UPI payment details if approved. We do not guarantee traffic, leads or sales.</p></details></div></section>
  </main>;
}
