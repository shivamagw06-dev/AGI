import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { SCREENER_CATEGORIES, screenerPath, screenerSlug } from '@/lib/screenerLibrary';
import { libraryRequest, screenerRequest, screenerDate } from '@/lib/screenerLibraryApi';
import ScreenerTable from '@/components/screeners/ScreenerTable';
import '@/pages/agi/screenerLibrary.css';
const today = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
const blankDefinition = () => ({ display_name: '', slug: '', category: 'Value', description: '', rule_notes: '', default_source_url: '' });
function previewGrid(preview) {
  if (preview.columns) return { columns: preview.columns, rows: preview.rows, identityColumn: preview.identityColumn };
  const keys = Object.keys(preview.rows?.[0] || {});
  const labels = { serial: 'No.', stock: 'Stock', nseCode: 'NSE code', bseCode: 'BSE code', isin: 'ISIN', peTtm: 'P/E TTM', pe3y: '3Y average', pe5y: '5Y average', pe10y: '10Y average', marketCapCr: 'Market cap (₹ cr)', dayChange: 'Day change %', weekChange: 'Week change %', quarterChange: 'Quarter change %', revenueGrowth: 'Revenue growth %', profitGrowth: 'Profit growth %' };
  return { columns: keys.map(key => labels[key] || key.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, c => c.toUpperCase())), rows: (preview.rows || []).map(row => keys.map(key => row[key] ?? '')), identityColumn: Math.max(0, keys.indexOf('isin')) };
}
export default function ScreenerImporter() {
  const [params] = useSearchParams(), [screens, setScreens] = useState([]), [selected, setSelected] = useState(params.get('screen') || 'low-pe'), [drafts, setDrafts] = useState({}), [preview, setPreview] = useState(null), [reviewed, setReviewed] = useState(false), [exclude, setExclude] = useState(false), [busy, setBusy] = useState(''), [error, setError] = useState(''), [notice, setNotice] = useState(''), [editor, setEditor] = useState(blankDefinition), [mode, setMode] = useState('');
  const screen = screens.find(s => s.slug === selected), draft = Object.hasOwn(drafts, selected) ? drafts[selected] : { text: '', secondText: '', asOf: today(), sourceUrl: screen?.default_source_url || '', identityHeader: '' };
  async function load() { try { setScreens((await libraryRequest('/admin/catalogue')).screens); } catch (e) { setError(e.message); } }
  useEffect(() => { load(); }, []);
  function resetPreview() { setPreview(null); setReviewed(false); setExclude(false); setError(''); setNotice(''); }
  function edit(field, value) { setDrafts(previous => ({ ...previous, [selected]: { ...draft, [field]: value } })); resetPreview(); }
  function choose(slug) { setSelected(slug); setMode(''); resetPreview(); }
  async function submit(action) {
    setBusy(action); setError(''); setNotice('');
    try {
      const payload = screen.kind === 'legacy'
        ? await screenerRequest(`/api/manual-screeners/${screen.slug}/${action}`, { method: 'POST', body: { asOf: draft.asOf, tables: [draft.text, draft.secondText].filter(t => t.trim()), excludeNonQualifying: exclude } })
        : await libraryRequest(`/${screen.slug}/${action}`, { method: 'POST', body: { ...draft, reviewed } });
      if (action === 'preview') { setPreview(payload); setReviewed(false); setExclude(false); }
      else { setPreview(null); setReviewed(false); setExclude(false); setNotice(payload.snapshot.already_saved ? 'This exact snapshot is already saved. No duplicate was created; the latest publication is unchanged.' : `Published ${payload.snapshot.row_count} stocks for ${payload.snapshot.as_of}. Previous snapshots remain saved.`); await load(); }
    } catch (e) { setError(e.message); } finally { setBusy(''); }
  }
  function openEditor(kind) {
    resetPreview(); setMode(kind);
    setEditor(kind === 'new' ? blankDefinition() : { slug: screen.slug, display_name: screen.display_name, category: screen.category, description: screen.description, rule_notes: screen.rule_notes || '', default_source_url: screen.default_source_url || '' });
  }
  async function saveDefinition(event) {
    event.preventDefault(); setBusy('definition'); setError(''); setNotice('');
    try { const data = await libraryRequest(mode === 'new' ? '' : `/${editor.slug}`, { method: mode === 'new' ? 'POST' : 'PATCH', body: editor }); await load(); setSelected(data.screen.slug); setMode(''); setPreview(null); setNotice(mode === 'new' ? 'Screener created. Paste its first table below.' : 'Definition saved. Earlier snapshots keep their original definition.'); }
    catch (e) { setError(e.message); } finally { setBusy(''); }
  }
  const grid = preview ? previewGrid(preview) : null;
  return <main className="sl-page sl-admin"><header className="sl-header"><div><p className="sl-eyebrow">ADMIN / SCREENER LIBRARY</p><h1>One importer. Every screen.</h1><p>Choose a screener, paste a dated table, review it and publish. Create additional screens whenever you need them.</p></div><Link to="/agi/screeners" className="sl-secondary" target="_blank">Open library ↗</Link></header>
    <section className="sl-panel"><div className="sl-form-grid"><label>Choose screener<select value={selected} onChange={e => choose(e.target.value)} disabled={!!busy}>{SCREENER_CATEGORIES.map(category => <optgroup key={category} label={category}>{screens.filter(s => s.category === category).map(s => <option key={s.slug} value={s.slug}>{s.display_name}</option>)}</optgroup>)}</select></label><div className="sl-inline-actions"><button type="button" onClick={() => openEditor('new')} disabled={!!busy}>+ Create screener</button>{screen?.kind === 'imported' && <button type="button" onClick={() => openEditor('edit')} disabled={!!busy}>Edit definition</button>}</div></div>{screen && <p className="sl-muted">{screen.row_count === null ? 'No table published yet.' : `Currently published: ${screen.row_count} stocks · ${screenerDate(screen.as_of)}`} · <Link to={screenerPath(screen)} target="_blank">View screener ↗</Link></p>}</section>
    {mode && <form className="sl-panel" onSubmit={saveDefinition}><h2>{mode === 'new' ? 'Create a screener' : 'Edit screen definition'}</h2><p className="sl-muted">Definitions are visible in the library. Stock results appear only after you publish a table.</p><div className="sl-form-grid"><label>Name<input required minLength={3} maxLength={120} value={editor.display_name} onChange={e => setEditor(s => ({ ...s, display_name: e.target.value, slug: mode === 'new' && (!s.slug || s.slug === screenerSlug(s.display_name)) ? screenerSlug(e.target.value) : s.slug }))} disabled={!!busy} /></label><label>Category<select value={editor.category} onChange={e => setEditor(s => ({ ...s, category: e.target.value }))} disabled={!!busy}>{SCREENER_CATEGORIES.map(c => <option key={c}>{c}</option>)}</select></label></div><label>URL name<input required pattern="[a-z0-9]+(-[a-z0-9]+)*" minLength={3} maxLength={80} value={editor.slug} onChange={e => setEditor(s => ({ ...s, slug: e.target.value }))} disabled={!!busy || mode !== 'new'} /></label><label>Short description<textarea maxLength={1000} rows={2} value={editor.description} onChange={e => setEditor(s => ({ ...s, description: e.target.value }))} disabled={!!busy} /></label><label>Reference rules and timeframe (notes, not executable filters)<textarea maxLength={3000} rows={3} value={editor.rule_notes} onChange={e => setEditor(s => ({ ...s, rule_notes: e.target.value }))} disabled={!!busy} /></label><label>Default source URL (optional, HTTPS)<input type="url" value={editor.default_source_url} onChange={e => setEditor(s => ({ ...s, default_source_url: e.target.value }))} disabled={!!busy} /></label><button className="sl-primary" disabled={!!busy}>Save definition</button><button type="button" onClick={() => setMode('')} disabled={!!busy}>Cancel</button></form>}
    {screen && <section className="sl-panel"><h2>Paste the stock table</h2><p>{screen.kind === 'legacy' ? 'This existing screen keeps its financial-rule validation and expected export columns.' : 'Include all column headers. CSV, tab-separated spreadsheet copies and differing column counts are supported. The importer validates structure and identities; it does not recalculate the financial screening rules.'}</p><div className="sl-form-grid"><label>Data as of<input type="date" value={draft.asOf} onChange={e => edit('asOf', e.target.value)} disabled={!!busy} required /></label>{screen.kind !== 'legacy' && <label>Source URL (optional, HTTPS)<input type="url" value={draft.sourceUrl} onChange={e => edit('sourceUrl', e.target.value)} disabled={!!busy} placeholder="https://…" /></label>}</div>
      {screen.kind !== 'legacy' && <label>Identifier column (optional: automatically prefer ISIN, then a stock code)<input value={draft.identityHeader} onChange={e => edit('identityHeader', e.target.value)} disabled={!!busy} placeholder="For a different layout, enter its exact unique identifier header" /></label>}
      <label className="sl-upload">Load CSV or TSV<input type="file" accept=".csv,.tsv,text/csv,text/tab-separated-values,text/plain" disabled={!!busy} onChange={async e => { try { const file = e.target.files?.[0]; if (file) { if (file.size > 1500000) throw Error('File is too large. Maximum 1.5 MB.'); edit('text', await file.text()); } } catch (err) { setError(err.message); } }} /></label>
      <label>Table 1<textarea rows={11} value={draft.text} onChange={e => edit('text', e.target.value)} disabled={!!busy} placeholder="Paste the complete table, including the header row…" /></label><details><summary>Second part (optional)</summary><label>Table 2 — include its header<textarea rows={6} value={draft.secondText} onChange={e => edit('secondText', e.target.value)} disabled={!!busy} /></label></details>
      <p className="sl-muted">Limits: 5,000 rows. New library screens accept up to 120 columns. Identical repeated columns are combined; conflicting repeats, duplicate stock identifiers and incomplete rows are rejected. Draft text stays available when switching screens in this tab.</p>
      <button className="sl-secondary" type="button" onClick={() => submit('preview')} disabled={!!busy || (!draft.text.trim() && !draft.secondText.trim())}>{busy === 'preview' ? 'Checking…' : 'Check table'}</button>{screen.kind === 'legacy' && <Link to={screen.adminPath} className="sl-original">Original specialised importer ↗</Link>}
    </section>}
    {error && <p className="sl-error" role="alert">{error}</p>}{notice && <p className="sl-success" role="status">{notice}</p>}
    {preview && <section className="sl-panel"><h2>Review: {preview.rowCount} stock rows · {screenerDate(preview.asOf)}</h2>{preview.identityHeader && <p>Matching stocks by <b>{preview.identityHeader}</b>. {preview.repeatedColumnsCollapsed || 0} repeated columns combined.</p>}
      {!!preview.excludedRows?.length && <div className="sl-warning"><h3>{preview.excludedRows.length} stocks do not meet this screen’s rules</h3><ul>{preview.excludedRows.map(row => <li key={row.isin}><b>{row.stock}</b> — {row.reason} P/E {row.peTtm}; averages {row.pe3y}, {row.pe5y}, {row.pe10y}.</li>)}</ul><label className="sl-check"><input type="checkbox" checked={exclude} onChange={e => setExclude(e.target.checked)} disabled={!!busy} />I reviewed and accept excluding these {preview.excludedRows.length} stocks.</label></div>}
      <ScreenerTable {...grid} label="Import preview" />
      <label className="sl-check"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} disabled={!!busy} />I reviewed the screener, data date and {preview.rowCount} rows. Publish this table for members.</label><p className="sl-muted">Publishing replaces the latest displayed list and retains previous snapshots. New library screens also retain their source, definition and entry/exit history.</p>
      <button className="sl-primary" type="button" onClick={() => submit('publish')} disabled={!!busy || !reviewed || !preview.rowCount || (!!preview.excludedRows?.length && !exclude)}>{busy === 'publish' ? 'Publishing…' : `Publish ${preview.rowCount} stock rows`}</button>
    </section>}
  </main>;
}
