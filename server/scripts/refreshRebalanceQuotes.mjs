/**
 * Keep the moving columns of a rebalance table current.
 *
 *   node server/scripts/refreshRebalanceQuotes.mjs           # dry run
 *   node server/scripts/refreshRebalanceQuotes.mjs --apply
 *   node server/scripts/refreshRebalanceQuotes.mjs --apply --event <uuid>
 *
 * A published rebalance table is a photograph. The flow estimate in it stays
 * true, because it describes a fixed index event - but price, traded value and
 * return since announcement all drift from the day it was printed, and the
 * ratio that decides whether a name is tradeable is flow divided by *current*
 * traded value. Six weeks between announcement and effective date is long
 * enough for that ratio to stop meaning anything.
 *
 * So the entered columns are never touched here. This writes only to
 * index_rebalance_quotes, which is a separate table for exactly that reason: a
 * bad candle leaves an analyst's input intact and the row visibly unrefreshed,
 * rather than overwriting it.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { getHistoricalCandles } from '../providers/upstox.js';
import { quoteFor } from '../services/rebalanceQuoteMath.js';
import { exchangeSymbol } from '../services/rebalancePaste.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const EVENT = argOf('--event');
const SESSIONS = Number(argOf('--sessions')) || 60;

if (!getSupabaseAdminCredentials()) {
  console.error('[rebalance] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const iso = (date) => date.toISOString().slice(0, 10);

/**
 * Enough calendar days to hold the requested sessions plus the gap back to the
 * announcement. Weekends and holidays mean a sixty-session window needs about
 * ninety calendar days, and asking for sixty would quietly measure six weeks.
 */
function fromDate(announcedOn) {
  const bySessions = new Date(Date.now() - (SESSIONS * 1.6 + 10) * 86_400_000);
  const announced = announcedOn ? new Date(`${String(announcedOn).slice(0, 10)}T00:00:00Z`) : null;
  if (announced && !Number.isNaN(announced.getTime())) {
    // Reach a few sessions before the announcement, because the return is
    // measured from the last close on or before it.
    const before = new Date(announced.getTime() - 10 * 86_400_000);
    if (before < bySessions) return iso(before);
  }
  return iso(bySessions);
}

/** USD/INR, or null. Null is handled: the quote math refuses to mix currencies. */
async function usdInr() {
  try {
    const payload = await getHistoricalCandles('GLOBAL_INDICATOR|USDINR', {
      unit: 'days', interval: 1, from: iso(new Date(Date.now() - 15 * 86_400_000)), to: iso(new Date()),
    });
    const candles = payload?.data?.candles || [];
    // Newest first from Upstox, but the close is taken by scanning for the
    // first usable one rather than trusting position.
    for (const candle of candles) {
      const close = Number(candle?.[4]);
      if (Number.isFinite(close) && close > 0) return close;
    }
  } catch (error) {
    console.warn(`[rebalance] USD/INR unavailable: ${error.message}`);
  }
  return null;
}

/**
 * Fill in instrument_key for entries that have none.
 *
 * The Bloomberg ticker in a research table is not the exchange symbol, so this
 * is a lookup and not a transform. An entry that cannot be resolved keeps a
 * null key and says so - it stays visible on the page with its entered
 * columns, unpriced, rather than disappearing.
 */
async function resolveInstruments(entries) {
  const unresolved = entries.filter((row) => !row.instrument_key);
  if (!unresolved.length) return new Map();

  const symbols = [...new Set(unresolved.map((row) => exchangeSymbol(row.source_ticker)).filter(Boolean))];
  const { data, error } = await client
    .from('nse_instruments')
    .select('instrument_key,trading_symbol')
    .in('trading_symbol', symbols);
  if (error) {
    console.warn(`[rebalance] instrument lookup: ${error.message}`);
    return new Map();
  }

  const bySymbol = new Map((data || []).map((row) => [String(row.trading_symbol).toUpperCase(), row.instrument_key]));
  const resolved = new Map();
  for (const row of unresolved) {
    const key = bySymbol.get(String(exchangeSymbol(row.source_ticker) || '').toUpperCase());
    if (key) resolved.set(row.id, key);
  }
  console.log(`[rebalance] resolved ${resolved.size} of ${unresolved.length} unmapped ticker(s)`);
  return resolved;
}

async function main() {
  let query = client
    .from('index_rebalance_entries')
    .select('id,source_ticker,company_name,instrument_key,net_passive_flow_usd_mn,event_id,index_rebalance_events!inner(announced_on,index_name)');
  if (EVENT) query = query.eq('event_id', EVENT);
  const { data: entries, error } = await query;
  if (error) throw new Error(`reading entries: ${error.message}`);
  if (!entries?.length) {
    console.log('[rebalance] no rebalance entries to refresh.');
    return;
  }

  const rate = await usdInr();
  console.log(`[rebalance] ${entries.length} entr(ies), USD/INR ${rate ?? 'unavailable'}`);
  console.log(`[rebalance] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  const resolved = await resolveInstruments(entries);
  const quotes = [];
  const unpriced = [];

  for (const entry of entries) {
    const instrumentKey = entry.instrument_key || resolved.get(entry.id) || null;
    const announcedOn = entry.index_rebalance_events?.announced_on || null;

    if (!instrumentKey) {
      unpriced.push({ entry_id: entry.id, refresh_note: 'no instrument_key: the ticker did not match the NSE instrument master' });
      continue;
    }

    let candles = [];
    try {
      const payload = await getHistoricalCandles(instrumentKey, {
        unit: 'days', interval: 1, from: fromDate(announcedOn), to: iso(new Date()),
      });
      candles = payload?.data?.candles || [];
    } catch (err) {
      // Recorded against the row rather than aborting the run. One delisted
      // instrument must not stop the other twenty-four from refreshing.
      unpriced.push({ entry_id: entry.id, refresh_note: `candles failed: ${err.message}`.slice(0, 300) });
      continue;
    }

    const quote = quoteFor({
      candles,
      announcedOn,
      flowUsdMn: entry.net_passive_flow_usd_mn,
      usdInr: rate,
      sessions: SESSIONS,
    });
    quotes.push({ entry_id: entry.id, ...quote, refreshed_at: new Date().toISOString() });

    const days = quote.days_of_advt;
    console.log(`[rebalance]   ${String(entry.source_ticker).padEnd(14)} ${quote.last_price_inr ?? '-'} INR  ${days === null ? 'days -' : `${days.toFixed(1)}d ADVT`}  ${quote.refresh_note || ''}`);
  }

  const rows = quotes.concat(unpriced.map((row) => ({ ...row, refreshed_at: new Date().toISOString() })));
  console.log(`[rebalance] ${quotes.length} priced, ${unpriced.length} unpriced`);

  if (!APPLY) {
    console.log('[rebalance] dry run only. Re-run with --apply to write.');
    return;
  }
  const { error: writeError } = await client.from('index_rebalance_quotes').upsert(rows, { onConflict: 'entry_id' });
  if (writeError) throw new Error(`writing quotes: ${writeError.message}`);

  // Resolutions are written back so the next run does not repeat the lookup,
  // and so the page can show which rows are mapped.
  for (const [id, instrument_key] of resolved) {
    const { error: mapError } = await client.from('index_rebalance_entries').update({ instrument_key }).eq('id', id);
    if (mapError) console.warn(`[rebalance] mapping ${id}: ${mapError.message}`);
  }
  console.log(`[rebalance] ${rows.length} quote(s) written`);
}

main().catch((error) => {
  console.error(`[rebalance] ${error.message}`);
  process.exit(1);
});
