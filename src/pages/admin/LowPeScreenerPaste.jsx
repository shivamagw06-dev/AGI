import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient';
import { API_ORIGIN } from '@/config';
import './lowPeScreenerPaste.css';

const todayIst = () => {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date()).map(({ type, value }) => [type, value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
};

export default function LowPeScreenerPaste() {
  const [asOf, setAsOf] = useState(todayIst);
  const [tables, setTables] = useState(['', '']);
  const [preview, setPreview] = useState(null);
  const [current, setCurrent] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    fetch(`${API_ORIGIN || ''}/api/manual-screeners/low-pe`, { cache: 'no-store' })
      .then((response) => response.json())
      .then((data) => setCurrent(data.snapshot))
      .catch(() => {});
  }, []);

  function editTable(index, value) {
    setTables((previous) => previous.map((item, itemIndex) => itemIndex === index ? value : item));
    setPreview(null); setError(''); setNotice('');
  }

  async function loadFile(index, file) {
    if (!file) return;
    editTable(index, await file.text());
  }

  async function submit(action) {
    setBusy(action); setError(''); setNotice('');
    try {
      const { data } = await supabase.auth.getSession();
      if (!data?.session?.access_token) throw new Error('Sign in as an administrator first.');
      const response = await fetch(`${API_ORIGIN || ''}/api/manual-screeners/low-pe/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${data.session.access_token}` },
        body: JSON.stringify({ asOf, tables: tables.filter((value) => value.trim()) }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Could not process the tables.');
      if (action === 'preview') setPreview(payload);
      else {
        setCurrent(payload.snapshot);
        setPreview(null);
        setNotice(`Published ${payload.snapshot.row_count} stocks for ${payload.snapshot.as_of}.`);
      }
    } catch (cause) { setError(cause.message); }
    finally { setBusy(''); }
  }

  return <main className="low-pe-admin">
    <header className="low-pe-admin__head">
      <div><span className="low-pe-admin__eyebrow">ADMIN / SCREENERS</span><h1>Low P/E table</h1><p>Paste the daily CSV export, review the rows, then publish the complete list.</p></div>
      <Link to="/agi/screeners" target="_blank">Open public page ↗</Link>
    </header>
    <div className="low-pe-admin__meta"><label>Data date <input type="date" value={asOf} onChange={(event) => { setAsOf(event.target.value); setPreview(null); }} disabled={!!busy} /></label><span>Currently published: {current ? `${current.row_count} stocks · ${current.as_of}` : 'No snapshot yet'}</span></div>
    <p className="low-pe-admin__guide">Include all 16 column headers. Paste one complete table, or split it across the two boxes if your export comes in parts. CSV and copied spreadsheet cells are accepted. Publishing replaces the public list; the previous snapshot remains saved.</p>
    {tables.map((value, index) => <section className="low-pe-admin__input" key={index}>
      <div><h2>{index === 0 ? 'Table 1' : 'Table 2 · optional'}</h2><label className="low-pe-admin__file">Load CSV file<input type="file" accept=".csv,text/csv,.tsv,text/tab-separated-values" onChange={(event) => void loadFile(index, event.target.files?.[0])} disabled={!!busy} /></label></div>
      <textarea rows={index === 0 ? 12 : 7} aria-label={`Table ${index + 1}`} placeholder="Paste rows with the header here…" value={value} onChange={(event) => editTable(index, event.target.value)} disabled={!!busy} />
    </section>)}
    {error && <p className="low-pe-admin__error" role="alert">{error}</p>}
    {notice && <p className="low-pe-admin__notice" role="status">{notice} <Link to="/agi/screeners" target="_blank">View page ↗</Link></p>}
    <div className="low-pe-admin__actions"><button type="button" onClick={() => void submit('preview')} disabled={!!busy || !tables.some((value) => value.trim()) || !asOf}>{busy === 'preview' ? 'Checking…' : 'Check tables'}</button><button type="button" className="primary" onClick={() => void submit('publish')} disabled={!!busy || !preview}>{busy === 'publish' ? 'Publishing…' : 'Publish complete list'}</button></div>
    {preview && <section className="low-pe-admin__preview"><div><span>READY TO PUBLISH</span><h2>{preview.rowCount} stocks · {preview.asOf}</h2><p>Review the rows below. Publishing makes all {preview.rowCount} rows public.</p></div><div className="low-pe-admin__scroll"><table><thead><tr><th>Stock</th><th>NSE code</th><th>P/E TTM</th><th>3Y avg</th><th>5Y avg</th><th>10Y avg</th></tr></thead><tbody>{preview.rows.map((row) => <tr key={row.isin}><td>{row.stock}</td><td>{row.nseCode || '—'}</td><td>{row.peTtm}</td><td>{row.pe3y}</td><td>{row.pe5y}</td><td>{row.pe10y}</td></tr>)}</tbody></table></div></section>}
  </main>;
}
