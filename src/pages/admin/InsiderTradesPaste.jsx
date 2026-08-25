import { useCallback, useMemo, useState } from 'react';
import { CheckCircle2, ClipboardPaste, Loader2, Upload } from 'lucide-react';
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
      const resp = await fetch(`${BASE}/${path}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
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
  }, [text]);

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
        value={text}
        onChange={(e) => { setText(e.target.value); setChecked(null); }}
        placeholder={`${REQUIRED.join('\t')}\t…\nReliance Industries\tA N Other\t2026-08-22\t12,500\t…`}
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
            <div><span>With ticker</span><strong>{fmt(checked.with_symbol)}</strong></div>
            <div><span>Open market</span><strong>{fmt(checked.open_market_rows)}</strong></div>
            <div><span>From</span><strong>{checked.first_reported || '—'}</strong></div>
            <div><span>To</span><strong>{checked.last_reported || '—'}</strong></div>
          </div>
          {checked.dropped_rows > 0 ? (
            <p className="itp-warn">
              {fmt(checked.dropped_rows)} of {fmt(checked.pasted_rows)} pasted rows were
              dropped — each needs a company, a person, a reported date and a quantity.
            </p>
          ) : null}
          <p className="itp-note">
            Rows without a ticker are still stored. The export covers a wider universe than
            company_master, so about two thirds do not resolve and keep a blank symbol
            rather than a guessed one.
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
      ) : (
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
      )}
    </div>
  );
}
