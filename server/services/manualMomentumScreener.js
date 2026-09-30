import { parsePaste } from '../../src/lib/pastedTable.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { validateAsOf } from './manualLowPeScreener.js';

export const MOMENTUM_HEADERS = [
  'Stock Name', 'NSE Code', 'BSE Code', 'Stock Code', 'ISIN',
  'Industry Name', 'sector_name', 'Current Price', 'Market Capitalization', 'Trendlyne Momentum Score', 'Day Volume', 'Week change %', 'Nifty50 Week change %', 'Current Price',
];

const keys = [
  'stock', 'nseCode', 'bseCode', 'stockCode', 'isin',
  'industry', 'sector', 'price', 'marketCapCr', 'score', 'volume', 'weekChange', 'niftyWeekChange', 'repeatedPrice',
];

function normalizeHeader(value) {
  return String(value || '').replace(/^\uFEFF/, '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function numericValue(value, label, rowNumber) {
  const raw = String(value ?? '').trim();
  if (!raw) throw new Error(`Row ${rowNumber}: ${label} is required.`);
  const number = Number(raw.replace(/,/g, ''));
  if (!Number.isFinite(number)) throw new Error(`Row ${rowNumber}: ${label} must be a number.`);
  return number;
}

export function parseMomentumTables(tables) {
  if (!Array.isArray(tables) || !tables.length || tables.length > 2) {
    throw new Error('Paste one or two complete tables.');
  }
  const rows = [];
  const seen = new Set();
  for (const [tableIndex, text] of tables.entries()) {
    if (!String(text || '').trim()) continue;
    const parsed = parsePaste(String(text));
    const header = [...(parsed[0] || [])];
    while (header.length > MOMENTUM_HEADERS.length && !String(header.at(-1) || '').trim()) header.pop();
    if (header.length !== MOMENTUM_HEADERS.length ||
      !header.every((name, index) => normalizeHeader(name) === normalizeHeader(MOMENTUM_HEADERS[index]))) {
      throw new Error(`Table ${tableIndex + 1}: the 14-column header does not match the Momentum workbook.`);
    }
    for (const [index, original] of parsed.slice(1).entries()) {
      const rowNumber = index + 2;
      const cells = [...original];
      while (cells.length > keys.length && !String(cells.at(-1) || '').trim()) cells.pop();
      if (cells.length !== keys.length) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: expected 14 columns, found ${cells.length}.`);
      }
      const row = Object.fromEntries(keys.map((key, column) => [key, String(cells[column] || '').trim()]));
      row.price = numericValue(cells[7], 'Current Price', rowNumber);
      row.marketCapCr = numericValue(cells[8], 'Market Capitalization', rowNumber);
      row.score = numericValue(cells[9], 'Trendlyne Momentum Score', rowNumber);
      if (!row.stock || !row.isin || !/^IN[A-Z0-9]{10}$/.test(row.isin) || !row.sector || !row.industry) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: stock, sector, industry and a valid ISIN are required.`);
      }
      if (row.score < 0 || row.score > 100) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: Momentum Score must be between 0 and 100.`);
      }
      row.volume = numericValue(cells[10], 'Day Volume', rowNumber);
      row.weekChange = numericValue(cells[11], 'Week change %', rowNumber);
      row.niftyWeekChange = numericValue(cells[12], 'Nifty50 Week change %', rowNumber);
      if (numericValue(cells[13], 'Repeated Current Price', rowNumber) !== row.price) throw new Error(`Row ${rowNumber}: repeated prices must match.`);
      if (!Number.isInteger(row.volume) || row.volume < 0) throw new Error(`Row ${rowNumber}: volume must be a nonnegative integer.`);
      delete row.repeatedPrice;
      row.relativeWeekChange = Number((row.weekChange - row.niftyWeekChange).toFixed(8));
      if (row.price <= 0 || row.marketCapCr < 0) {
        throw new Error(`Table ${tableIndex + 1}, row ${rowNumber}: price must be positive and market cap cannot be negative.`);
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

export async function latestMomentumSnapshot() {
  const { data, error } = await database().from('manual_momentum_screener_snapshots')
    .select('id,as_of,created_at,row_count,rows').order('id', { ascending: false }).limit(1).maybeSingle();
  if (error) throw error;
  return data;
}

export async function publishMomentumSnapshot({ asOf, rows, actorId }) {
  const { data, error } = await database().from('manual_momentum_screener_snapshots')
    .insert({ as_of: validateAsOf(asOf), row_count: rows.length, rows, published_by: actorId })
    .select('id,as_of,created_at,row_count').single();
  if (error) throw error;
  return data;
}
