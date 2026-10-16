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
  return String(value || '').replace(/^\uFEFF/, '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function numberValue(value, label, rowNumber) {
  const trimmed = String(value || '').trim();
  if (!trimmed || trimmed === '-' || trimmed.toLowerCase() === 'n/a') return null;
  const result = Number(trimmed.replace(/,/g, '').replace(/%$/, ''));
  if (!Number.isFinite(result)) throw new Error(`Row ${rowNumber}: ${label} must be a number.`);
  return result;
}

export function parseLowPeTables(tables) {
  if (!Array.isArray(tables) || !tables.length || tables.length > 2) {
    throw new Error('Paste one or two complete tables.');
  }
  const rows = [];
  const seen = new Set();
  for (const [tableIndex, text] of tables.entries()) {
    if (!String(text || '').trim()) continue;
    const parsed = parsePaste(String(text));
    const header = parsed[0] || [];
    if (header.length !== LOW_PE_HEADERS.length ||
      !header.every((name, index) => headerName(name) === headerName(LOW_PE_HEADERS[index]))) {
      throw new Error(`Table ${tableIndex + 1}: the 16-column header does not match the Low PE export.`);
    }
    for (const [index, cells] of parsed.slice(1).entries()) {
      const rowNumber = index + 2;
      if (cells.length !== keys.length) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: expected 16 columns, found ${cells.length}.`);
      }
      const row = Object.fromEntries(keys.map((key, column) => [
        key,
        numbers.has(key)
          ? numberValue(cells[column], LOW_PE_HEADERS[column], rowNumber)
          : String(cells[column] || '').trim(),
      ]));
      if (!row.stock || !row.sector || !row.isin || !/^IN[A-Z0-9]{10}$/.test(row.isin)) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: stock, sector and a valid ISIN are required.`);
      }
      if ([row.peTtm, row.pe3y, row.pe5y, row.pe10y].some((value) => value == null || value <= 0)) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: all four P/E values must be positive.`);
      }
      if (!(row.peTtm < row.pe3y && row.peTtm < row.pe5y && row.peTtm < row.pe10y)) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: P/E TTM must be below all three historical averages.`);
      }
      if (seen.has(row.isin)) throw new Error(`Duplicate ISIN ${row.isin} in the pasted tables.`);
      seen.add(row.isin);
      rows.push(row);
    }
  }
  if (!rows.length) throw new Error('No stock rows were found.');
  if (rows.length > 5000) throw new Error('A publication may contain at most 5,000 stocks.');
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
