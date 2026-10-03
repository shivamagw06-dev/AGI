/**
 * Load the NSE instrument master from Upstox.
 *
 *   node server/scripts/loadNseInstruments.mjs            # dry run
 *   node server/scripts/loadNseInstruments.mjs --apply
 *
 * Everything that prices an Indian stock here needs an instrument_key like
 * "NSE_EQ|INE0ONG01011", and every research table names the stock the way
 * Bloomberg does - "MEESHO IS". Nothing in the codebase bridged the two.
 *
 * Deriving the key by rule is not an option: the mapping is arbitrary, it is
 * an ISIN, and guessing produces a key that is well-formed and wrong. A wrong
 * key does not error - it returns empty candles, which reads as a stock that
 * did not trade.
 *
 * Upstox publishes the file without authentication, so this does not depend on
 * a token being fresh. Roughly two thousand equities; the whole thing is a few
 * megabytes and a single request.
 */
import { gunzipSync } from 'node:zlib';
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';

const APPLY = process.argv.includes('--apply');
const SOURCE = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz';
const CHUNK = 500;

if (!getSupabaseAdminCredentials()) {
  console.error('[instruments] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();

/**
 * Equities only.
 *
 * The file is mostly derivatives - every strike of every option on every
 * expiry. Those outnumber the cash names by orders of magnitude and none of
 * them can be the subject of an index rebalance.
 */
function isCashEquity(row) {
  const segment = String(row?.segment || '').toUpperCase();
  const type = String(row?.instrument_type || '').toUpperCase();
  return segment === 'NSE_EQ' && (type === 'EQ' || type === 'EQUITY');
}

function normalise(row) {
  const instrument_key = String(row?.instrument_key || '').trim();
  const trading_symbol = String(row?.trading_symbol || row?.tradingsymbol || '').trim();
  // Both are required to be useful: the key is how it is priced, the symbol is
  // how it is found. A row missing either is not a mapping.
  if (!instrument_key.includes('|') || !trading_symbol) return null;
  return {
    instrument_key,
    exchange: String(row?.exchange || 'NSE').trim(),
    segment: String(row?.segment || '').trim() || null,
    trading_symbol,
    name: String(row?.name || '').trim() || null,
    isin: String(row?.isin || '').trim() || null,
    instrument_type: String(row?.instrument_type || '').trim() || null,
    lot_size: Number.isFinite(Number(row?.lot_size)) ? Number(row.lot_size) : null,
    tick_size: Number.isFinite(Number(row?.tick_size)) ? Number(row.tick_size) : null,
    refreshed_at: new Date().toISOString(),
  };
}

async function main() {
  console.log(`[instruments] fetching ${SOURCE}`);
  const response = await fetch(SOURCE, { headers: { Accept: 'application/gzip,*/*' } });
  if (!response.ok) throw new Error(`Upstox instruments: HTTP ${response.status}`);

  const buffer = Buffer.from(await response.arrayBuffer());
  // The endpoint has served both gzip and plain JSON. Sniffing the magic bytes
  // is cheaper than depending on a content-type header being right.
  const isGzip = buffer[0] === 0x1f && buffer[1] === 0x8b;
  const parsed = JSON.parse((isGzip ? gunzipSync(buffer) : buffer).toString('utf8'));
  const all = Array.isArray(parsed) ? parsed : (parsed?.data || []);
  if (!all.length) throw new Error('Upstox instruments returned no rows');

  const rows = all.filter(isCashEquity).map(normalise).filter(Boolean);
  console.log(`[instruments] ${all.length.toLocaleString()} instruments, ${rows.length.toLocaleString()} cash equities`);

  // A collapse in the equity count means the file changed shape or the filter
  // stopped matching. Writing that would delete the mapping every downstream
  // price lookup depends on, so it refuses instead.
  if (rows.length < 1000) {
    throw new Error(`only ${rows.length} equities parsed, which is too few to be the NSE cash list - refusing to write`);
  }

  const sample = rows.slice(0, 3).map((row) => `${row.trading_symbol} -> ${row.instrument_key}`);
  console.log(`[instruments] sample: ${sample.join(', ')}`);

  if (!APPLY) {
    console.log('[instruments] dry run only. Re-run with --apply to write.');
    return;
  }

  let written = 0;
  for (let index = 0; index < rows.length; index += CHUNK) {
    const batch = rows.slice(index, index + CHUNK);
    const { error } = await client.from('nse_instruments').upsert(batch, { onConflict: 'instrument_key' });
    if (error) throw new Error(`writing instruments at ${index}: ${error.message}`);
    written += batch.length;
  }
  // Upserted rather than replaced. A delisted symbol keeps its row with an old
  // refreshed_at, so an entry stored against it still resolves to something
  // explicable instead of to nothing.
  console.log(`[instruments] ${written.toLocaleString()} rows written`);
}

main().catch((error) => {
  console.error(`[instruments] ${error.message}`);
  process.exit(1);
});
