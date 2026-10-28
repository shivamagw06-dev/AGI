import { parsePaste } from './pastedTable.js';
export const cleanHeader = value => String(value ?? '').replace(/^\uFEFF/, '').trim().replace(/_/g, ' ').replace(/\s+/g, ' ').toLowerCase();
const cleanCell = value => String(value ?? '').replace(/\u0000/g, '').trim();
const identifier = value => cleanCell(value).replace(/\s+/g, ' ').toUpperCase();
function equivalent(a, b) {
  if (a === b) return true;
  const number = v => /^[-+]?\d[\d,]*(\.\d+)?%?$/.test(v) ? Number(v.replace(/[, %]/g, '')) : NaN;
  return Number.isFinite(number(a)) && number(a) === number(b) && a.endsWith('%') === b.endsWith('%');
}
export function parseScreenerTable(text, identityHeader = '') {
  if (typeof text !== 'string' || !text.trim()) throw Error('Paste a complete table including its header row.');
  if (text.length > 1500000) throw Error('The table is too large. Use at most 1.5 million characters.');
  let quoted = false;
  for (let i = 0; i < text.length; i++) { if (text[i] === '"') { if (quoted && text[i + 1] === '"') i++; else quoted = !quoted; } }
  if (quoted) throw Error('The table contains an unclosed quoted field. Copy the complete table or load its CSV file.');
  const parsed = parsePaste(text);
  if (parsed.length < 2) throw Error('Include the header and at least one stock row.');
  if (parsed.length > 5001) throw Error('Use at most 5,000 stock rows per snapshot.');
  const original = parsed[0].map(cleanCell);
  if (original.length < 2 || original.length > 120 || original.some(v => !v || v.length > 160)) throw Error('Use 2–120 non-empty column headers, each at most 160 characters. Copy spreadsheet cells or upload CSV/TSV; space-aligned text is not a table.');
  const groups = new Map();
  original.forEach((name, i) => { const key = cleanHeader(name); groups.set(key, [...(groups.get(key) || []), i]); });
  const columns = [...groups.values()].map(indices => original[indices[0]]);
  const rowGroups = [...groups.values()];
  const rows = parsed.slice(1).map((cells, index) => {
    if (cells.length !== original.length) throw Error(`Row ${index + 2}: expected ${original.length} columns, found ${cells.length}.`);
    if (cells.some(v => String(v).length > 4000)) throw Error(`Row ${index + 2}: a cell exceeds 4,000 characters.`);
    return rowGroups.map((indices, col) => {
      const values = indices.map(i => cleanCell(cells[i]));
      if (values.some(v => !equivalent(v, values[0]))) throw Error(`Row ${index + 2}: repeated ${columns[col]} columns disagree.`);
      return values[0];
    });
  });
  if (rows.length > 5000) throw Error('Use at most 5,000 stock rows per snapshot.');
  const normalized = columns.map(cleanHeader);
  const aliases = ['isin', 'nse code', 'symbol', 'ticker', 'stock code', 'bse code', 'stock name', 'stock', 'company name', 'company', 'security name'];
  const chosen = identityHeader ? cleanHeader(identityHeader) : aliases.find(name => normalized.includes(name));
  const identityColumn = normalized.indexOf(chosen);
  if (identityColumn < 0) throw Error('Choose a unique stock identifier column, such as ISIN, NSE Code, Symbol or Stock Name.');
  const seen = new Set();
  rows.forEach((row, i) => {
    const key = identifier(row[identityColumn]);
    if (!key || ['-', '—', 'N/A', 'NA'].includes(key)) throw Error(`Row ${i + 2}: ${columns[identityColumn]} is missing. Choose a complete identifier column such as ISIN.`);
    if (chosen === 'isin' && !/^[A-Z]{2}[A-Z0-9]{9}\d$/.test(key)) throw Error(`Row ${i + 2}: invalid ISIN.`);
    if (seen.has(key)) throw Error(`Row ${i + 2}: duplicate stock identifier ${key}.`);
    seen.add(key);
  });
  return { columns, rows, identityColumn, identityHeader: columns[identityColumn], rowCount: rows.length, repeatedColumnsCollapsed: original.length - columns.length };
}
export function compareScreenerSnapshots(current, previous) {
  if (!previous) return { available: false, reason: 'First saved snapshot; no earlier list to compare.' };
  if (cleanHeader(current.columns[current.identity_column]) !== cleanHeader(previous.columns[previous.identity_column])) return { available: false, reason: 'The identifier column changed. Entry and exit counts are not comparable.' };
  const map = snap => new Map(snap.rows.map(row => {
    const labelIndex = snap.columns.findIndex(c => ['stock name', 'stock', 'company name', 'company', 'security name'].includes(cleanHeader(c)));
    return [identifier(row[snap.identity_column]), { identifier: row[snap.identity_column], name: row[labelIndex >= 0 ? labelIndex : snap.identity_column] }];
  }));
  const next = map(current), prior = map(previous);
  const added = [...next].filter(([id]) => !prior.has(id)).map(([, item]) => item);
  const removed = [...prior].filter(([id]) => !next.has(id)).map(([, item]) => item);
  return { available: true, previousAsOf: previous.as_of, previousId: previous.id, addedCount: added.length, removedCount: removed.length, retainedCount: [...next.keys()].filter(id => prior.has(id)).length, added, removed };
}
export function sortScreenerRows(rows, column, direction = 1) {
  const numeric = v => { const raw = String(v).trim().replace(/[,₹$%]/g, ''); return raw && /^[-+]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw) ? Number(raw) : null; };
  return [...rows].sort((a, b) => {
    const x = numeric(a[column]), y = numeric(b[column]);
    return direction * (x !== null && y !== null ? x - y : String(a[column]).localeCompare(String(b[column])));
  });
}
export function parseScreenerTables(tables, identityHeader = '') {
  if (!Array.isArray(tables) || tables.length < 1 || tables.length > 2) throw Error('Paste one complete table, or two parts with a header in each.');
  const parts = tables.filter(t => typeof t === 'string' && t.trim()).map(t => parseScreenerTable(t, identityHeader));
  if (!parts.length) throw Error('Paste a complete table including its header row.');
  const first = parts[0], keys = first.columns.map(cleanHeader), seen = new Set();
  const rows = parts.flatMap(part => {
    const other = part.columns.map(cleanHeader);
    if (other.length !== keys.length || keys.some(k => !other.includes(k))) throw Error('The two parts must contain the same column headers.');
    return part.rows.map(row => keys.map(key => row[other.indexOf(key)]));
  });
  if (rows.length > 5000) throw Error('Use at most 5,000 stock rows per snapshot.');
  for (const row of rows) { const key = identifier(row[first.identityColumn]); if (seen.has(key)) throw Error(`Duplicate stock identifier ${key} across the two table parts.`); seen.add(key); }
  return { ...first, rows, rowCount: rows.length, repeatedColumnsCollapsed: parts.reduce((sum, p) => sum + p.repeatedColumnsCollapsed, 0) };
}
