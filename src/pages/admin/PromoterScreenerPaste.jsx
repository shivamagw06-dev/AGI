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

function olderCount(rows, asOf) {
  return rows.filter((row) => row.shareholdingDate &&
    (Date.parse(`${asOf}T00:00:00Z`) - Date.parse(`${row.shareholdingDate}T00:00:00Z`)) > 180 * 86400000).length;
}

export default function PromoterScreenerPaste() {
  const [asOf, setAsOf] = useState(todayIst);
  const [table, setTable] = useState('');
  const [preview, setPreview] = useState(null);
  const [current, setCurrent] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    fetch(`${API_ORIGIN || ''}/api/manual-screeners/promoter-holdings`, { cache: 'no-store' })
      .then((response) => response.json())
      .then((data) => setCurrent(data.snapshot))
      .catch(() => {});
  }, []);

  function editTable(value) {
    setTable(value); setPreview(null); setError(''); setNotice('');
  }

  async function submit(action) {
    setBusy(action); setError(''); setNotice('');
    try {
      const { data } = await supabase.auth.getSession();
      if (!data?.session?.access_token) throw new Error('Sign in as an administrator first.');
      const response = await fetch(`${API_ORIGIN || ''}/api/manual-screeners/promoter-holdings/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${data.session.access_token}` },
        body: JSON.stringify({ asOf, tables: [table] }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Could not process the table.');
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
    <header className="low-pe-admin__head"><div><span className="low-pe-admin__eyebrow">ADMIN / SCREENERS</span><h1>Promoter holdings table</h1><p>Paste the complete export, check its rows and dates, then publish.</p></div><Link to="/agi/screeners/promoter-holdings" target="_blank">Open public page ↗</Link></header>
    <div className="low-pe-admin__meta"><label>Table date <input type="date" value={asOf} onChange={(event) => { setAsOf(event.target.value); setPreview(null); }} disabled={!!busy} /></label><span>Currently published: {current ? `${current.row_count} stocks · ${current.as_of}` : 'No snapshot yet'}</span></div>
    <p className="low-pe-admin__guide">Include all 14 column headers. CSV and copied spreadsheet cells are accepted. Publishing replaces the visible list; the previous snapshot remains saved. Rows with shareholding dates more than 180 days before the table date are hidden by default on the public page, but remain available there.</p>
    <section className="low-pe-admin__input"><div><h2>Complete table</h2><label className="low-pe-admin__file">Load CSV file<input type="file" accept=".csv,text/csv,.tsv,text/tab-separated-values" onChange={(event) => { const file = event.target.files?.[0]; if (file) void file.text().then(editTable); }} disabled={!!busy} /></label></div><textarea rows={14} aria-label="Promoter holdings table" placeholder="Paste rows with the header here…" value={table} onChange={(event) => editTable(event.target.value)} disabled={!!busy} /></section>
    {error && <p className="low-pe-admin__error" role="alert">{error}</p>}
    {notice && <p className="low-pe-admin__notice" role="status">{notice} <Link to="/agi/screeners/promoter-holdings" target="_blank">View page ↗</Link></p>}
    <div className="low-pe-admin__actions"><button type="button" onClick={() => void submit('preview')} disabled={!!busy || !table.trim() || !asOf}>{busy === 'preview' ? 'Checking…' : 'Check table'}</button><button type="button" className="primary" onClick={() => void submit('publish')} disabled={!!busy || !preview}>{busy === 'publish' ? 'Publishing…' : 'Publish complete list'}</button></div>
    {preview && <section className="low-pe-admin__preview"><div><span>READY TO PUBLISH</span><h2>{preview.rowCount} stocks · {preview.asOf}</h2><p>{olderCount(preview.rows, preview.asOf)} rows have shareholding dates more than 180 days older than the table date. Review them before publishing.</p></div><div className="low-pe-admin__scroll"><table><thead><tr><th>Stock</th><th>Promoter change QoQ</th><th>Shareholding date</th><th>NSE code</th><th>ISIN</th></tr></thead><tbody>{preview.rows.map((row) => <tr key={row.isin}><td>{row.stock}</td><td>+{row.promoterChange}%</td><td>{row.shareholdingDate}</td><td>{row.nseCode || '—'}</td><td>{row.isin}</td></tr>)}</tbody></table></div></section>}
  </main>;
}
