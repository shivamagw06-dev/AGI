import { useCallback, useMemo, useState } from 'react';
import { CheckCircle2, ClipboardPaste, Loader2, Upload } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { API_ORIGIN } from '@/config';
import { parsePaste } from '@/lib/pastedTable';
import './insiderTradesPaste.css';

const BASE = `${API_ORIGIN || ''}/api/intelligence/insider-trades`;

const REQUIRED = ['Stock', 'Client Name', 'Reported To/By Exchange', 'Quantity'];

function fmt(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString();
}

// Preview only. The server parses for real; this is so the desk sees the grid
// it pasted before sending it, rather than trusting a textarea.
function previewGrid(rows) {
  if (!rows.length) return null;
  // The embedded newlines are real data, but a cell three lines tall wrecks the
  // grid, so show it on one line here. Nothing is sent from this copy.
  return rows.slice(0, 6).map((r) => r.map((c) => c.replace(/\s+/g, ' ').trim()));
}

export default function InsiderTradesPaste() {
  const [country,setCountry]=useState(()=>new URLSearchParams(window.location.search).get('country')==='US'?'US':'IN');
  const [text, setText] = useState('');
  const [checked, setChecked] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  const rows = useMemo(() => parsePaste(text), [text]);
  const grid = useMemo(() => previewGrid(rows), [rows]);
  // Rows, not lines: a single trade can span several lines of the paste.
  const rowCount = rows.length;

  const call = useCallback(async (path, label) => {
    setBusy(label);
    setError(null);
    try {
      const {data:sessionData}=await supabase.auth.getSession();
      if(!sessionData?.session?.access_token)throw Error('Sign in with your administrator account to publish.');
      const resp = await fetch(`${BASE}/${path}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization:`Bearer ${sessionData.session.access_token}` },
        body: JSON.stringify({ text, country }),
      });
      const data = await resp.json();
      if (!resp.ok || data?.ok === false) {
        throw new Error(data?.hint || data?.detail || data?.error || `HTTP ${resp.status}`);
      }
      return data;
    } catch (err) {
      setError(err?.message || 'Request failed.');
      return null;
    } finally {
      setBusy(null);
    }
  }, [text,country]);

  const check = useCallback(async () => {
    setResult(null);
    setChecked(await call('preview', 'check'));
  }, [call]);

  const publish = useCallback(async () => {
    const data = await call('paste', 'publish');
    if (data) {
      setResult(data);
      setChecked(null);
      setText('');
    }
  }, [call]);

  return (
    <div className="itp">
      <header>
        <h1><ClipboardPaste size={20} /> Insider Trades — paste</h1>
        <p>
          Copy the rows from your insider export, header row included, and paste them
          below. Check first, then publish — it goes straight into the warehouse and is
          live immediately.
        </p>
      </header>

      <div className="itp-bar"><label>Market <select aria-label="Import market" disabled={!!busy} value={country} onChange={e=>{setCountry(e.target.value);setText('');setChecked(null);setResult(null);setError(null);}}><option value="IN">India · INR</option><option value="US">United States · USD</option></select></label>{country==='US'&&<a href="/templates/us-insider-trades.tsv" download>Download US paste template</a>}</div>
      {country==='US'&&<div className="itp-help"><h2>US paste format</h2><p>Use tabs from Excel/Sheets or CSV, with a header row. OpenInsider-style headers are supported. Dates must include a year; slash dates use US month/day/year. All values are USD. Unknown plan status remains unknown.</p><code>Company · Ticker · Insider Name · Title · Filing Date · Trade Date · Transaction Code · Quantity · Price · Value · Owned · 10b5-1 · SEC URL · Transaction ID · Derivative</code><p>P = purchase, S = sale, A = award, M = exercise, F = tax withholding, G = gift. P/S may be private transactions. Use a unique Transaction ID for otherwise identical trades. For Form 4/A amendments, reconcile the original before importing.</p></div>}
      {error ? <div className="itp-error">{error}</div> : null}

      {result ? (
        <div className="itp-ok">
          <CheckCircle2 size={17} />
          <div>
            <strong>Published.</strong>{' '}
            {fmt(result.row_count)} trades across {fmt(result.companies)} companies
            {result.first_reported ? `, ${result.first_reported} to ${result.last_reported}` : ''}.
            {' '}Inserted {fmt(result.written?.inserted)}, updated {fmt(result.written?.updated)},
            unchanged {fmt(result.written?.unchanged)}.
          </div>
        </div>
      ) : null}

      <textarea
        className="itp-paste"
        disabled={!!busy}
        value={text}
        onChange={(e) => { setText(e.target.value); setChecked(null); }}
        placeholder={country==='US'?'Company\tTicker\tInsider Name\tFiling Date\tTrade Date\tTransaction Code\tQuantity\tPrice\tValue\nPaste your US transactions here, including the header.':`${REQUIRED.join('\t')}\t…\nReliance Industries\tA N Other\t2026-08-22\t12,500\t…`}
        spellCheck={false}
        rows={10}
      />

      <div className="itp-bar">
        <span className="itp-count">
          {rowCount ? `${fmt(rowCount - 1)} rows + header` : 'nothing pasted yet'}
        </span>
        <button type="button" className="itp-ghost" onClick={check} disabled={!text.trim() || !!busy}>
          {busy === 'check' ? <Loader2 size={15} className="itp-spin" /> : null} Check
        </button>
        <button
          type="button"
          className="itp-go"
          onClick={publish}
          disabled={!checked?.ok || !!busy}
          title={checked?.ok ? 'Write to the warehouse' : 'Check the paste first'}
        >
          {busy === 'publish' ? <Loader2 size={15} className="itp-spin" /> : <Upload size={15} />}
          Publish
        </button>
      </div>

      {checked ? (
        <section className="itp-check">
          <div className="itp-stats">
            <div><span>Rows</span><strong>{fmt(checked.row_count)}</strong></div>
            <div><span>Companies</span><strong>{fmt(checked.companies)}</strong></div>
            <div>
              <span>With ticker</span>
              <strong>
                {checked.symbol_resolution === 'deferred_until_publish'
                  ? 'On publish'
                  : fmt(checked.with_symbol)}
              </strong>
            </div>
            <div><span>{country==='US'?'Purchases / sales (P/S)':'Open market'}</span><strong>{fmt(checked.open_market_rows)}</strong></div>
            <div><span>From</span><strong>{checked.first_reported || '—'}</strong></div>
            <div><span>To</span><strong>{checked.last_reported || '—'}</strong></div>
          </div>
          {country==='US'&&<><p>{checked.duplicate_rows||0} exact duplicate rows collapsed. Invalid rows block publication of the entire batch.</p>{checked.limitations?.map(note=><p className="itp-note" key={note}>{note}</p>)}<div className="itp-scroll"><table><thead><tr><th>Company</th><th>Code</th><th>Trade date</th><th>Shares</th><th>USD value</th><th>10b5-1</th></tr></thead><tbody>{checked.preview_rows?.map(row=><tr key={row.trade_id}><td>{row.company_name}</td><td>{row.transaction_code}</td><td>{row.transaction_date}</td><td>{fmt(row.quantity)}</td><td>{fmt(row.value)}</td><td>{row.planned}</td></tr>)}</tbody></table></div></>}
          {checked.dropped_rows > 0 ? (
            <p className="itp-warn">
              {fmt(checked.dropped_rows)} of {fmt(checked.pasted_rows)} pasted rows were
              dropped — each needs a company, a person, a reported date and a quantity.
            </p>
          ) : null}
          <p className="itp-note">
            {country==='US'?'Tickers are taken from your paste; missing tickers are not guessed.':checked.symbol_resolution === 'deferred_until_publish'
              ? 'Ticker matching runs when you publish. Rows without a match are still stored and can be linked after Company Master is updated.'
              : 'Rows without a ticker are still stored. The export covers a wider universe than company_master, so unmatched rows keep a blank symbol rather than a guessed one.'}
          </p>
        </section>
      ) : null}

      {grid ? (
        <section className="itp-grid-wrap">
          <h2>What you pasted <span>first {grid.length - 1} rows</span></h2>
          <div className="itp-scroll">
            <table>
              <thead><tr>{grid[0].map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
              <tbody>
                {grid.slice(1).map((r, i) => (
                  <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : country==='IN' ? (
        <section className="itp-help">
          <h2>Columns it reads</h2>
          <p>
            Paste the export unchanged — the header names below are what it looks for.
            Extra columns are ignored.
          </p>
          <code>
            Stock · Client Name · Client Category · Action · Reported To/By Exchange ·
            Quantity · Post Transaction Holding · Traded % · Avg. Price · Value · Period ·
            Regulation (Insider/SAST) · Security Type · Mode
          </code>
          <p className="itp-note">
            Tab-separated (straight from Excel or Sheets) or comma-separated both work.
            Re-pasting a day already loaded updates those rows rather than duplicating
            them, so overlapping ranges are safe.
          </p>
        </section>
      ):null}
    </div>
  );
}
