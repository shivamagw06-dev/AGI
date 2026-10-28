import { parsePaste } from '../../src/lib/pastedTable.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

export const LOW_PE_HEADERS = [
  'Sl No', 'Stock', 'PE TTM', 'PE 3Yr Average', 'PE 5Yr Average',
  'PE 10Yr Average', 'Day Chg %', 'Week Chg %', 'Qtr Chg %',
  'Market Cap', 'Sector', 'Rev Growth Qtr YoY %',
  'Net Profit Qtr Growth YoY %', 'NSE Code', 'BSE Code', 'ISIN',
];

const keys = [
  'serial', 'stock', 'peTtm', 'pe3y', 'pe5y', 'pe10y', 'dayChange',
  'weekChange', 'quarterChange', 'marketCapCr', 'sector',
  'revenueGrowth', 'profitGrowth', 'nseCode', 'bseCode', 'isin',
];
const numbers = new Set([
  'serial', 'peTtm', 'pe3y', 'pe5y', 'pe10y', 'dayChange',
  'weekChange', 'quarterChange', 'marketCapCr', 'revenueGrowth', 'profitGrowth',
]);

function headerName(value) {
  return String(value || '').replace(/^\uFEFF/, '').trim().replace(/_/g, ' ').replace(/\s+/g, ' ').toLowerCase();
}

const aliases = new Map(keys.flatMap((key, index) => [[headerName(LOW_PE_HEADERS[index]), key]]));
for (const [name, key] of Object.entries({
  'stock name': 'stock', 'pe ttm price to earnings': 'peTtm',
  'day change %': 'dayChange', 'week change %': 'weekChange', 'qtr change %': 'quarterChange',
  'market capitalization': 'marketCapCr', 'sector name': 'sector',
  'revenue growth qtr yoy %': 'revenueGrowth',
})) aliases.set(name, key);

function mapHeaders(header, tableNumber) {
  const columns = new Map();
  header.forEach((name, index) => {
    const key = aliases.get(headerName(name));
    if (key) columns.set(key, [...(columns.get(key) || []), index]);
  });
  const missing = keys.filter((key) => key !== 'serial' && !columns.has(key));
  if (missing.length) {
    throw new Error(`Table ${tableNumber}: missing required columns: ${missing.map((key) => LOW_PE_HEADERS[keys.indexOf(key)]).join(', ')}. Include the complete header row from the export.`);
  }
  // Trendlyne repeats sector and market cap in the expanded export. Other
  // repeated fields are ambiguous and must not silently replace an input.
  for (const [key, indexes] of columns) {
    if (indexes.length > 1 && !['marketCapCr', 'sector'].includes(key)) {
      throw new Error(`Table ${tableNumber}: duplicate column ${LOW_PE_HEADERS[keys.indexOf(key)]}.`);
    }
  }
  return columns;
}

function numberValue(value, label, rowNumber) {
  const trimmed = String(value || '').trim();
  if (!trimmed || trimmed === '-' || trimmed.toLowerCase() === 'n/a') return null;
  const result = Number(trimmed.replace(/,/g, '').replace(/%$/, ''));
  if (!Number.isFinite(result)) throw new Error(`Row ${rowNumber}: ${label} must be a number.`);
  return result;
}

function parseTables(tables, { review = false } = {}) {
  if (!Array.isArray(tables) || !tables.length || tables.length > 2) {
    throw new Error('Paste one or two complete tables.');
  }
  const rows = [];
  const excludedRows = [];
  const seen = new Set();
  let inputRows = 0;
  for (const [tableIndex, text] of tables.entries()) {
    if (!String(text || '').trim()) continue;
    const parsed = parsePaste(String(text));
    const header = parsed[0] || [];
    const columns = mapHeaders(header, tableIndex + 1);
    for (const [index, cells] of parsed.slice(1).entries()) {
      const rowNumber = index + 2;
      if (++inputRows > 5000) throw new Error('A publication may contain at most 5,000 stocks.');
      if (cells.length !== header.length) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: expected ${header.length} columns from the header, found ${cells.length}.`);
      }
      const row = Object.fromEntries(keys.map((key, column) => {
        const indexes = columns.get(key);
        if (!indexes) return [key, inputRows]; // expanded export has no serial
        const values = indexes.map((index) => numbers.has(key)
          ? numberValue(cells[index], LOW_PE_HEADERS[column], rowNumber)
          : String(cells[index] || '').trim());
        if (values.some((value) => value !== values[0])) {
          throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: repeated ${LOW_PE_HEADERS[column]} columns disagree. Check the source export.`);
        }
        return [key, values[0]];
      }));
      if (!row.stock || !row.sector || !row.isin || !/^IN[A-Z0-9]{10}$/.test(row.isin)) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: stock, sector and a valid ISIN are required.`);
      }
      if (seen.has(row.isin)) throw new Error(`Duplicate ISIN ${row.isin} in the pasted tables.`);
      seen.add(row.isin);
      const reason = [row.peTtm, row.pe3y, row.pe5y, row.pe10y].some((value) => value == null || value <= 0)
        ? 'All four P/E values must be positive.'
        : !(row.peTtm < row.pe3y && row.peTtm < row.pe5y && row.peTtm < row.pe10y)
          ? 'P/E TTM must be below all three historical averages.' : null;
      if (reason) {
        if (!review) throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: ${reason}`);
        excludedRows.push({ ...row, tableNumber: tableIndex + 1, rowNumber, reason });
        continue;
      }
      rows.push(row);
    }
  }
  if (!inputRows) throw new Error('No stock rows were found.');
  return { rows, excludedRows, inputRows };
}

export function parseLowPeTables(tables) { return parseTables(tables).rows; }
export function reviewLowPeTables(tables) { return parseTables(tables, { review: true }); }

export function lowPePublicationRows(tables, excludeNonQualifying) {
  const { rows, excludedRows } = reviewLowPeTables(tables);
  if (!rows.length) throw new Error('No stock rows meet the Low P/E rules. Nothing was published.');
  if (excludedRows.length && excludeNonQualifying !== true) {
    throw new Error(`Table contains ${excludedRows.length} stocks that do not meet the Low P/E rules. Review and acknowledge their exclusion before publishing.`);
  }
  return rows;
}

export function validateAsOf(value) {
  const date = String(value || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(`${date}T00:00:00Z`)) ||
    new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date) {
    throw new Error('Choose a valid data date.');
  }
  return date;
}

function database() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Screener storage is not configured.');
  return client;
}

export async function latestLowPeSnapshot() {
  const { data, error } = await database().from('manual_low_pe_screener_snapshots')
    .select('id,as_of,created_at,row_count,rows').order('id', { ascending: false }).limit(1).maybeSingle();
  if (error) throw error;
  return data;
}

export async function publishLowPeSnapshot({ asOf, rows, actorId }) {
  const { data, error } = await database().from('manual_low_pe_screener_snapshots')
    .insert({ as_of: validateAsOf(asOf), row_count: rows.length, rows, published_by: actorId })
    .select('id,as_of,created_at,row_count').single();
  if (error) throw error;
  return data;
}
