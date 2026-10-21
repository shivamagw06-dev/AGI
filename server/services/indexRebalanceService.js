/**
 * Reading and writing index rebalance events.
 *
 * The read joins three tables that are deliberately separate: the event, the
 * entered rows, and the refreshed quotes. Keeping quotes apart means a bad
 * candle can never overwrite what an analyst typed - the row comes back with
 * its entered columns intact and a refresh_note saying why it has no price.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { parsePaste, exchangeSymbol } from './rebalancePaste.js';

function client() {
  if (!getSupabaseAdminCredentials()) throw new Error('Supabase admin credentials are not configured.');
  return createSupabaseAdmin();
}

/** Inflows first, then outflows, each ranked by size. Unpriced rows last. */
export function rankEntries(rows) {
  const withFlow = (row) => {
    const value = Number(row?.net_passive_flow_usd_mn);
    return Number.isFinite(value) ? value : null;
  };
  const inflows = (rows || []).filter((row) => (withFlow(row) ?? 0) > 0).sort((a, b) => withFlow(b) - withFlow(a));
  const outflows = (rows || []).filter((row) => (withFlow(row) ?? 0) < 0).sort((a, b) => withFlow(a) - withFlow(b));
  // A row with no flow estimate is still a real index change and still belongs
  // on the page. Dropping it would hide a constituent change because nobody
  // had sized it yet.
  const unsized = (rows || []).filter((row) => withFlow(row) === null || withFlow(row) === 0);
  return { inflows, outflows, unsized };
}

/** Per-sector totals, for the summary strip. */
export function sectorTotals(rows) {
  const totals = new Map();
  for (const row of rows || []) {
    const sector = String(row?.sector || 'Unclassified');
    const value = Number(row?.net_passive_flow_usd_mn);
    if (!Number.isFinite(value)) continue;
    totals.set(sector, (totals.get(sector) || 0) + value);
  }
  return [...totals.entries()]
    .map(([sector, net_flow_usd_mn]) => ({ sector, net_flow_usd_mn }))
    .sort((a, b) => b.net_flow_usd_mn - a.net_flow_usd_mn);
}

export async function listRebalanceEvents() {
  const db = client();
  const { data, error } = await db
    .from('index_rebalance_events')
    .select('id,provider,index_name,market,announced_on,effective_on,source_url,notes')
    .order('announced_on', { ascending: false })
    .limit(24);
  if (error) throw new Error(error.message);
  return data || [];
}

export async function getRebalanceEvent(eventId) {
  const db = client();
  const { data: event, error: eventError } = await db
    .from('index_rebalance_events').select('*').eq('id', eventId).maybeSingle();
  if (eventError) throw new Error(eventError.message);
  if (!event) return null;

  const { data: entries, error: entryError } = await db
    .from('index_rebalance_entries')
    .select('*,index_rebalance_quotes(*)')
    .eq('event_id', eventId);
  if (entryError) throw new Error(entryError.message);

  const rows = (entries || []).map((entry) => {
    const quote = Array.isArray(entry.index_rebalance_quotes)
      ? entry.index_rebalance_quotes[0]
      : entry.index_rebalance_quotes;
    const { index_rebalance_quotes: _drop, ...rest } = entry;
    return {
      ...rest,
      // Named so a reader can tell an unrefreshed row from one with no flow.
      quote: quote || null,
      priced: Boolean(quote?.last_price_inr),
    };
  });

  return { event, ...rankEntries(rows), sectors: sectorTotals(rows), total_entries: rows.length };
}

/** Parse a pasted table without writing anything, so it can be confirmed. */
export function previewPaste(text) {
  const parsed = parsePaste(text);
  return {
    ...parsed,
    rows: parsed.rows.map((row) => ({ ...row, exchange_symbol: exchangeSymbol(row.source_ticker) })),
  };
}

export async function publishRebalance({ event, text }) {
  const parsed = parsePaste(text);
  if (parsed.missing.length) throw new Error(`The pasted table is missing: ${parsed.missing.join(', ')}`);
  if (!parsed.rows.length) throw new Error('No usable rows were found in the pasted table.');

  const db = client();
  const { data: saved, error: eventError } = await db
    .from('index_rebalance_events')
    .upsert({
      provider: event.provider, index_name: event.index_name, market: event.market || 'india',
      announced_on: event.announced_on, effective_on: event.effective_on || null,
      source_url: event.source_url || null, notes: event.notes || null,
    }, { onConflict: 'provider,index_name,announced_on' })
    .select().single();
  if (eventError) throw new Error(eventError.message);

  const rows = parsed.rows.map((row) => ({
    event_id: saved.id,
    source_ticker: row.source_ticker,
    company_name: row.company_name || null,
    sector: row.sector || null,
    change_type: row.change_type,
    net_passive_flow_usd_mn: row.net_passive_flow_usd_mn,
    source_mkt_cap_usd_mn: row.source_mkt_cap_usd_mn,
    source_advt_usd_mn: row.source_advt_usd_mn,
    estimate_source: event.estimate_source || null,
    estimate_as_of: event.estimate_as_of || null,
  }));

  const { error: rowError } = await db
    .from('index_rebalance_entries')
    .upsert(rows, { onConflict: 'event_id,source_ticker' });
  if (rowError) throw new Error(rowError.message);

  return { event: saved, written: rows.length, rejected: parsed.rejected };
}
