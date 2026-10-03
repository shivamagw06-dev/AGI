/**
 * Which missing prices are blocking the backtest, and for how many managers.
 *
 *   node server/scripts/missingBacktestPrices.mjs
 *   node server/scripts/missingBacktestPrices.mjs --quarters 20 --top 10
 *
 * Read-only. It writes nothing and fetches nothing; it reports.
 *
 * Five of fifty-one managers can be stated. The other forty-six fail the same
 * way - price coverage below the 95% floor in one quarter - and the coverage
 * figure is of the top ten positions, not of the whole book. So a manager at
 * 86.7% is missing roughly one position in ten, by value, in one quarter out
 * of twenty. That is a handful of securities, not a broken pipeline, and
 * nothing has ever said which securities.
 *
 * The floor is not the thing to relax. A compounded return multiplies every
 * period, so one quarter at half coverage carries its gap through every period
 * after it - which is why the floor exists and why it is 95% rather than 70%.
 * The answer is to price the names, and to price the ones that unblock the most
 * managers first.
 *
 * A ticker is reported when it appears in a manager's top ten and has no
 * adjusted close at all, or has none within the window the strategy would have
 * held it. The second case is the one a count of rows would miss: a security
 * with two years of prices looks covered until a period needs a third.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { backtestInputs, paged } from '../services/institutionalResearchLayerService.js';

const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const QUARTERS = Number(argOf('--quarters') || 20);
const TOP_N = Number(argOf('--top') || 10);
const LIMIT = Number(argOf('--limit') || 60);

if (!getSupabaseAdminCredentials()) {
  console.error('[prices] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(0);
const money = (value) => `$${(Number(value || 0) / 1e9).toFixed(1)}bn`;

async function main() {
  const managers = await paged(
    () => client.from('institutional_managers').select('id,slug,display_name').order('display_name'),
    { label: 'managers' },
  );
  console.log(`[prices] ${managers.length} manager(s), top ${TOP_N} over ${QUARTERS} quarters`);

  // ticker -> what needs it
  const needed = new Map();
  for (const manager of managers) {
    try {
      const { holdings } = await backtestInputs(client, manager.slug, QUARTERS, { topN: TOP_N });
      for (const row of holdings) {
        const ticker = String(row.ticker || '').trim().toUpperCase();
        if (!ticker) continue;
        const date = String(row.report_date || '').slice(0, 10);
        if (!needed.has(ticker)) needed.set(ticker, { ticker, managers: new Set(), value: 0, earliest: date, latest: date });
        const entry = needed.get(ticker);
        entry.managers.add(manager.display_name);
        entry.value += Number(row.value_usd) || 0;
        if (date && date < entry.earliest) entry.earliest = date;
        if (date && date > entry.latest) entry.latest = date;
      }
    } catch (error) {
      console.warn(`[prices] ${manager.display_name}: ${error.message}`);
    }
  }
  console.log(`[prices] ${needed.size.toLocaleString()} distinct securities are held in a top-${TOP_N} book  (${elapsed()}s)`);

  // What the price table actually covers for each of them. Asked in batches
  // rather than one ticker at a time: fifteen hundred round trips to answer a
  // question about coverage would cost more than the backtest it is diagnosing.
  const covered = new Map();
  const tickers = [...needed.keys()];
  for (let index = 0; index < tickers.length; index += 200) {
    const slice = tickers.slice(index, index + 200);
    const rows = await paged(
      () => client.from('institutional_security_prices')
        .select('ticker,price_date').in('ticker', slice).order('ticker').order('price_date'),
      { maxRows: 2_000_000, label: 'prices' },
    );
    for (const row of rows) {
      const current = covered.get(row.ticker);
      if (!current) { covered.set(row.ticker, { first: row.price_date, last: row.price_date, rows: 1 }); continue; }
      if (row.price_date < current.first) current.first = row.price_date;
      if (row.price_date > current.last) current.last = row.price_date;
      current.rows += 1;
    }
  }
  console.log(`[prices] price history read for ${covered.size.toLocaleString()} of them  (${elapsed()}s)`);

  const absent = [];
  const short = [];
  for (const entry of needed.values()) {
    const have = covered.get(entry.ticker);
    if (!have) { absent.push({ ...entry, reason: 'no adjusted close at all' }); continue; }
    // Held from its first appearance to its last, plus the quarter after -
    // a position disclosed at a quarter end is exited at the next one.
    if (have.first > entry.earliest) short.push({ ...entry, reason: `prices start ${have.first}, first held ${entry.earliest}` });
    else if (have.last < entry.latest) short.push({ ...entry, reason: `prices end ${have.last}, last held ${entry.latest}` });
  }

  const rank = (list) => list.sort((a, b) => (b.managers.size - a.managers.size) || (b.value - a.value));
  const show = (title, list) => {
    console.log('');
    console.log(`[prices] ${list.length.toLocaleString()} ${title}`);
    for (const row of rank(list).slice(0, LIMIT)) {
      console.log(`[prices]   ${row.ticker.padEnd(10)} ${String(row.managers.size).padStart(3)} manager(s)  ${money(row.value).padStart(9)}  ${row.reason}`);
    }
    if (list.length > LIMIT) console.log(`[prices]   ... and ${(list.length - LIMIT).toLocaleString()} more`);
  };

  show('with no price history at all', absent);
  show('whose price history does not span when they were held', short);

  const blocked = new Set([...absent, ...short].flatMap((row) => [...row.managers]));
  console.log('');
  console.log(`[prices] ${blocked.size} of ${managers.length} managers hold at least one security that cannot be priced`);
  console.log(`[prices] pricing the ${Math.min(LIMIT, absent.length + short.length)} listed above would reach ${blocked.size} of them`);
}

main().catch((error) => {
  console.error(`[prices] ${error.message}`);
  process.exit(1);
});
