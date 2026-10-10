import { parsePaste } from '../../src/lib/pastedTable.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { validateAsOf } from './manualLowPeScreener.js';

export const PROMOTER_HEADERS = [
  'Sl No', 'Stock', 'Promoter holding change QoQ %', 'Shareholding Date',
  'LTP', 'Market Cap', 'Latest Financial Result', 'PE TTM', 'PBV Adjusted',
  'Revenue QoQ Growth %', 'Net Profit QoQ Growth %', 'NSE Code', 'BSE Code', 'ISIN',
];

const keys = [
  'serial', 'stock', 'promoterChange', 'shareholdingDate', 'ltp', 'marketCapCr',
  'financialResultDate', 'peTtm', 'pbv', 'revenueGrowth', 'profitGrowth',
  'nseCode', 'bseCode', 'isin',
];
const numbers = new Set([
  'serial', 'promoterChange', 'ltp', 'marketCapCr', 'peTtm', 'pbv',
  'revenueGrowth', 'profitGrowth',
]);

function normalizeHeader(value) {
  return String(value || '').replace(/^\uFEFF/, '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function numericValue(value, label, rowNumber) {
  const trimmed = String(value ?? '').trim();
  if (!trimmed || trimmed === '-' || trimmed.toLowerCase() === 'n/a') return null;
  const number = Number(trimmed.replace(/,/g, '').replace(/%$/, ''));
  if (!Number.isFinite(number)) throw new Error(`Row ${rowNumber}: ${label} must be a number.`);
  return number;
}

function optionalDate(value, label, rowNumber, asOf) {
  const date = String(value || '').trim();
  if (!date || date === '-') return null;
  try {
    validateAsOf(date);
  } catch {
    throw new Error(`Row ${rowNumber}: ${label} must be a valid YYYY-MM-DD date.`);
  }
  if (date > asOf) throw new Error(`Row ${rowNumber}: ${label} cannot be after the data date.`);
  return date;
}

export function parsePromoterTables(tables, asOfInput) {
  const asOf = validateAsOf(asOfInput);
  if (!Array.isArray(tables) || !tables.length || tables.length > 2) {
    throw new Error('Paste one or two complete tables.');
  }
  const rows = [];
  const seen = new Set();
  for (const [tableIndex, text] of tables.entries()) {
    if (!String(text || '').trim()) continue;
    const parsed = parsePaste(String(text));
    const header = parsed[0] || [];
    if (header.length !== PROMOTER_HEADERS.length ||
      !header.every((name, index) => normalizeHeader(name) === normalizeHeader(PROMOTER_HEADERS[index]))) {
      throw new Error(`Table ${tableIndex + 1}: the 14-column header does not match the promoter-holdings export.`);
    }
    for (const [index, cells] of parsed.slice(1).entries()) {
      const rowNumber = index + 2;
      if (cells.length !== keys.length) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: expected 14 columns, found ${cells.length}.`);
      }
      const row = Object.fromEntries(keys.map((key, column) => [
        key,
        numbers.has(key)
          ? numericValue(cells[column], PROMOTER_HEADERS[column], rowNumber)
          : String(cells[column] || '').trim(),
      ]));
      row.shareholdingDate = optionalDate(row.shareholdingDate, 'Shareholding Date', rowNumber, asOf);
      row.financialResultDate = optionalDate(row.financialResultDate, 'Latest Financial Result', rowNumber, asOf);
      if (!row.stock || !row.isin || !/^IN[A-Z0-9]{10}$/.test(row.isin)) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: stock and a valid ISIN are required.`);
      }
      if (row.promoterChange == null || row.promoterChange <= 0.1 || !row.shareholdingDate) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: a shareholding date and promoter increase above 0.1% are required.`);
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

function database() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Screener storage is not configured.');
  return client;
}

export async function latestPromoterSnapshot() {
  const { data, error } = await database().from('manual_promoter_screener_snapshots')
    .select('id,as_of,created_at,row_count,rows').order('id', { ascending: false }).limit(1).maybeSingle();
  if (error) throw error;
  return data;
}

export async function publishPromoterSnapshot({ asOf, rows, actorId }) {
  const { data, error } = await database().from('manual_promoter_screener_snapshots')
    .insert({ as_of: validateAsOf(asOf), row_count: rows.length, rows, published_by: actorId })
    .select('id,as_of,created_at,row_count').single();
  if (error) throw error;
  return data;
}
