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

export default function PiotroskiScreenerPaste() {
  const [asOf, setAsOf] = useState(todayIst);
  const [table, setTable] = useState('');
  const [fileName, setFileName] = useState('');
  const [preview, setPreview] = useState(null);
  const [current, setCurrent] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    fetch(`${API_ORIGIN || ''}/api/manual-screeners/piotroski`, { cache: 'no-store' })
      .then((response) => response.json())
      .then((data) => setCurrent(data.snapshot))
      .catch(() => {});
  }, []);

  function editTable(value) {
    setTable(value); setPreview(null); setError(''); setNotice('');
  }

  async function loadFile(file) {
    if (!file) return;
    setBusy('reading'); setError('');
    try {
      let text;
      if (/\.xlsx?$/i.test(file.name)) {
        const XLSX = await import('xlsx');
        const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array' });
        const sheetName = workbook.SheetNames.find((name) => {
          const header = XLSX.utils.sheet_to_json(workbook.Sheets[name], { header: 1, range: 0 })[0] || [];
          return header.some((cell) => String(cell || '').trim() === 'Piotroski Score');
        });
        if (!sheetName) throw new Error('No sheet has the expected Piotroski Score header.');
        text = XLSX.utils.sheet_to_csv(workbook.Sheets[sheetName], { blankrows: false });
      } else {
        text = await file.text();
      }
      editTable(text);
      setFileName(file.name);
    } catch (cause) { setError(cause.message); }
    finally { setBusy(''); }
  }

  async function submit(action) {
    setBusy(action); setError(''); setNotice('');
    try {
      const { data } = await supabase.auth.getSession();
      if (!data?.session?.access_token) throw new Error('Sign in as an administrator first.');
      const response = await fetch(`${API_ORIGIN || ''}/api/manual-screeners/piotroski/${action}`, {
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
    <header className="low-pe-admin__head"><div><span className="low-pe-admin__eyebrow">ADMIN / SCREENERS</span><h1>High Piotroski Score</h1><p>Upload the daily workbook or paste its complete table, review, then publish.</p></div><Link to="/agi/screeners/piotroski" target="_blank">Open public page ↗</Link></header>
    <div className="low-pe-admin__meta"><label>Table date <input type="date" value={asOf} onChange={(event) => { setAsOf(event.target.value); setPreview(null); }} disabled={!!busy} /></label><span>Currently published: {current ? `${current.row_count} stocks · ${current.as_of}` : 'No snapshot yet'}</span></div>
    <p className="low-pe-admin__guide">Upload the .xlsx file or paste the Data Downloader sheet with all 10 headers. Scores must be 8 or 9. Publishing replaces the public list; the previous snapshot remains saved. Prices and scores are shown as supplied, not recalculated by AGI.</p>
    <section className="low-pe-admin__input"><div><h2>Complete table</h2><label className="low-pe-admin__file">{fileName || 'Load Excel or CSV file'}<input type="file" accept=".xlsx,.xls,.csv,.tsv" onChange={(event) => void loadFile(event.target.files?.[0])} disabled={!!busy} /></label></div><textarea rows={13} aria-label="Piotroski score table" placeholder="Paste the table with its header here…" value={table} onChange={(event) => { setFileName(''); editTable(event.target.value); }} disabled={!!busy} /></section>
    {error && <p className="low-pe-admin__error" role="alert">{error}</p>}
    {notice && <p className="low-pe-admin__notice" role="status">{notice} <Link to="/agi/screeners/piotroski" target="_blank">View page ↗</Link></p>}
    <div className="low-pe-admin__actions"><button type="button" onClick={() => void submit('preview')} disabled={!!busy || !table.trim() || !asOf}>{busy === 'preview' ? 'Checking…' : 'Check table'}</button><button type="button" className="primary" onClick={() => void submit('publish')} disabled={!!busy || !preview}>{busy === 'publish' ? 'Publishing…' : 'Publish complete list'}</button></div>
    {preview && <section className="low-pe-admin__preview"><div><span>READY TO PUBLISH</span><h2>{preview.rowCount} stocks · {preview.asOf}</h2><p>{preview.rows.filter((row) => row.score === 9).length} scored 9 · {preview.rows.filter((row) => row.score === 8).length} scored 8 · {preview.rows.filter((row) => !row.nseCode).length} have no NSE code.</p></div><div className="low-pe-admin__scroll"><table><thead><tr><th>Stock</th><th>Score</th><th>Sector</th><th>Price</th><th>NSE</th><th>BSE</th><th>ISIN</th></tr></thead><tbody>{preview.rows.map((row) => <tr key={row.isin}><td>{row.stock}</td><td>{row.score}</td><td>{row.sector}</td><td>{row.price}</td><td>{row.nseCode || '—'}</td><td>{row.bseCode || '—'}</td><td>{row.isin}</td></tr>)}</tbody></table></div></section>}
  </main>;
}
