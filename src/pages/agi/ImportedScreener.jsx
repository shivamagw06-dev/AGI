import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { usePlus } from '@/contexts/PlusContext';
import { libraryRequest, screenerDate, recordedTime } from '@/lib/screenerLibraryApi';
import ScreenerTable from '@/components/screeners/ScreenerTable';
import './screenerLibrary.css';
export default function ImportedScreener() {
  const { slug } = useParams(), [params, setParams] = useSearchParams(), selected = params.get('snapshot') || '', plus = usePlus();
  const [data, setData] = useState(null), [history, setHistory] = useState([]), [error, setError] = useState(''), [loading, setLoading] = useState(true), [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; setLoading(true); setError(''); setData(null); setHistory([]);
    Promise.all([libraryRequest(`/${encodeURIComponent(slug)}${selected ? `?snapshot=${encodeURIComponent(selected)}` : ''}`), libraryRequest(`/${encodeURIComponent(slug)}/history`)]).then(([detail, list]) => { if (active) { setData(detail); setHistory(list.snapshots); } }).catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; };
  }, [slug, selected, retry]);
  if (loading) return <main className="sl-page"><p role="status">Loading screener…</p></main>;
  if (error) return <main className="sl-page"><Link to="/agi/screeners">← Screener library</Link><p className="sl-error" role="alert">{error}</p><button onClick={() => setRetry(v => v + 1)}>Retry</button></main>;
  const { screen, snapshot, changes } = data, definition = snapshot?.definition || screen;
  return <main className="sl-page"><Link to="/agi/screeners" className="sl-back">← Screener library</Link><header className="sl-header"><div><p className="sl-eyebrow">{definition.category} / IMPORTED TABLE</p><h1>{definition.display_name}</h1><p>{definition.description}</p></div>{plus.isAdmin && <Link className="sl-primary" to={`/admin/screener-import?screen=${encodeURIComponent(slug)}`}>Update this table ↗</Link>}</header>
    <section className="sl-definition"><h2>Screen definition</h2><p>{definition.rule_notes || 'No additional screening notes were supplied.'}</p><p className="sl-muted">These are imported candidates. Financial rules and provider scores are not independently recalculated by this importer.</p></section>
    {!snapshot ? <section className="sl-empty"><h2>Awaiting first import</h2><p>This definition is ready. No stock results, counts or performance are claimed until a table is published.</p></section> : <>
      <div className="sl-overview"><div><strong>{snapshot.row_count}</strong><span>stocks</span></div><div><strong>{screenerDate(snapshot.as_of)}</strong><span>data as of</span></div><div><strong>{snapshot.columns.length}</strong><span>source columns</span></div><p>Recorded {recordedTime(snapshot.created_at)}{snapshot.source_url && <> · <a href={snapshot.source_url} target="_blank" rel="noopener noreferrer">Source ↗</a></>}</p></div>
      <div className="sl-history"><label>Saved publications (up to 100 most recent)<select value={selected} onChange={e => setParams(e.target.value ? { snapshot: e.target.value } : {})}><option value="">Latest publication</option>{history.map(s => <option key={s.id} value={s.id}>{screenerDate(s.as_of)} · {s.row_count} stocks · recorded {recordedTime(s.created_at)}</option>)}</select></label><p>Showing {selected ? 'a saved historical publication' : 'the latest published table'}. Dates describe the source snapshot, not a live quote.</p></div>
      <section className="sl-changes"><h2>Changes since the previous publication</h2>{!changes?.available ? <p>{changes?.reason}</p> : <><p><b>{changes.addedCount} entered</b> · <b>{changes.removedCount} left</b> · {changes.retainedCount} retained · compared with {screenerDate(changes.previousAsOf)}. List membership changes are not buy/sell instructions.</p><details><summary>See entries and exits</summary><div className="sl-change-columns">{[['Entered', changes.added], ['Left', changes.removed]].map(([title, list]) => <div key={title}><h3>{title} ({list.length})</h3><ul>{list.slice(0,100).map(item => <li key={item.identifier}>{item.name} <small>{item.identifier !== item.name ? item.identifier : ''}</small></li>)}</ul>{!list.length && <p>None.</p>}{list.length > 100 && <p>First 100 shown. Use saved tables to inspect the full lists.</p>}</div>)}</div></details></>}</section>
      <ScreenerTable columns={snapshot.columns} rows={snapshot.rows} identityColumn={snapshot.identity_column} label={`${definition.display_name} stocks`} />
    </>}
  </main>;
}
