import { useEffect, useMemo, useState } from 'react';
import { sortScreenerRows } from '@/lib/screenerTable';
export default function ScreenerTable({ columns = [], rows = [], identityColumn = 0, label = 'Stock table' }) {
  const [search, setSearch] = useState(''), [page, setPage] = useState(0), [sort, setSort] = useState(null);
  useEffect(() => { setPage(0); setSearch(''); setSort(null); }, [rows]);
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const matches = rows.filter(row => !q || row.some(value => String(value ?? '').toLowerCase().includes(q)));
    return sort ? sortScreenerRows(matches, sort.column, sort.direction) : matches;
  }, [rows, search, sort]);
  const pages = Math.max(1, Math.ceil(filtered.length / 50)), current = Math.min(page, pages - 1);
  const visible = filtered.slice(current * 50, current * 50 + 50);
  return <section className="sl-table-section" aria-label={label}>
    <div className="sl-table-tools"><label>Search table<input value={search} onChange={event => { setSearch(event.target.value); setPage(0); }} placeholder="Company, symbol or table value" /></label><span>{filtered.length.toLocaleString('en-IN')} matching rows · click a column to sort</span></div>
    <div className="sl-table-scroll"><table><caption className="sr-only">{label}</caption><thead><tr>{columns.map((name, i) => <th key={i} aria-sort={sort?.column === i ? sort.direction === 1 ? 'ascending' : 'descending' : 'none'}><button type="button" onClick={() => { setSort(s => ({ column: i, direction: s?.column === i ? -s.direction : 1 })); setPage(0); }}>{name}{sort?.column === i ? sort.direction === 1 ? ' ↑' : ' ↓' : ''}</button></th>)}</tr></thead><tbody>{visible.map((row, i) => <tr key={`${row[identityColumn]}-${i}`}>{columns.map((_, j) => <td key={j}>{row[j] == null || row[j] === '' ? '—' : String(row[j])}</td>)}</tr>)}{!visible.length && <tr><td colSpan={columns.length || 1}>No matching stocks.</td></tr>}</tbody></table></div>
    <div className="sl-pagination"><span>{filtered.length ? current * 50 + 1 : 0}–{Math.min((current + 1) * 50, filtered.length)} of {filtered.length} · page {current + 1} of {pages}</span><div><button type="button" disabled={current === 0} onClick={() => setPage(current - 1)}>Previous</button><button type="button" disabled={current + 1 === pages} onClick={() => setPage(current + 1)}>Next</button></div></div>
  </section>;
}
