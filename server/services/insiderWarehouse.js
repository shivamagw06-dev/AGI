/**
 * Insider disclosures, read from the warehouse rather than Supabase.
 *
 * The Supabase copy is fed by hand through the admin upload screen and is three
 * days behind with 247 fewer rows. The warehouse copy is loaded by the engine
 * importer, carries the pledge filings the Supabase normaliser drops, and marks
 * which trades happened at a market price.
 *
 * That last flag is what the page is built around. A promoter buying on the open
 * market and a director receiving an ESOP allotment are both "acquisitions", and
 * a page that adds them together turns a signal into noise.
 *
 * Value is reported on only about two thirds of filings. Every count here is
 * therefore taken over all rows, every rupee figure is taken over the rows that
 * carry one, and the coverage is returned alongside so the page can say which is
 * which instead of implying a total it does not have.
 */

const TAB = 'insider_trades';
const ROW_LIMIT = 5000;

// A cluster is several different insiders buying the same company at a market
// price within a few weeks. One promoter buying is a data point; four separate
// people buying is the pattern that has survived out-of-sample testing.
export const CLUSTER_WINDOW_DAYS = 30;
export const CLUSTER_MIN_BUYERS = 3;

const BUY_ACTIONS = new Set(['acquisition', 'purchase', 'buy']);
const SELL_ACTIONS = new Set(['disposal', 'sale', 'sell']);
const PLEDGE_CREATE = /creation|pledge creation|invocation/i;
const PLEDGE_RELEASE = /release|revoke|revocation/i;

const lower = (value) => String(value ?? '').trim().toLowerCase();
const num = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

function engineConfig() {
  let baseUrl = (process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  return { baseUrl, token: (process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim() };
}

async function fetchRows({ timeoutMs = 60_000 } = {}) {
  const { baseUrl, token } = engineConfig();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${baseUrl}/v1/warehouse/tab/${TAB}?limit=${ROW_LIMIT}`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
      signal: controller.signal,
    });
    if (!response.ok) throw Error(`warehouse ${TAB} responded ${response.status}`);
    const body = await response.json();
    return Array.isArray(body?.rows) ? body.rows : [];
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Collapse rows the warehouse holds twice for one filing.
 *
 * insider_trades was first keyed on the ticker, then re-keyed on the company
 * name once it became clear most of these companies have no ticker in the
 * master. The re-key changed every row id, so the second import inserted
 * alongside the first rather than updating it, and 87 trades are stored twice.
 * Only the newer copy records how its ticker was resolved, so that field
 * distinguishes them.
 *
 * The stale copies are being retired, but a page that double-counts while that
 * happens is worse than one that de-duplicates on read, and this stays correct
 * either way.
 */
export function dedupe(rows) {
  const best = new Map();
  for (const row of rows || []) {
    const key = [row.company_name, row.reported_on, row.person, row.action, row.quantity, row.mode]
      .map(lower).join('|');
    const held = best.get(key);
    if (!held || (!held.symbol_match && row.symbol_match)) best.set(key, row);
  }
  return [...best.values()];
}

export function side(row) {
  const action = lower(row.action);
  if (BUY_ACTIONS.has(action)) return 'buy';
  if (SELL_ACTIONS.has(action)) return 'sell';
  return 'other';
}

export const isOpenMarket = (row) => String(row.is_open_market) === 'true';

/** Filings a market price was actually paid for, one side or the other. */
const conviction = (rows) => rows.filter((row) => isOpenMarket(row) && side(row) !== 'other');

/**
 * Net open-market flow per day, and the running total behind it.
 *
 * Counts rather than rupees: a third of filings report no value, so a rupee
 * line would step down on days when the missing ones happen to be the large
 * trades. The rupee figures ride alongside for the days that do report them.
 */
export function dailyFlow(rows) {
  const byDate = new Map();
  for (const row of conviction(rows)) {
    const date = String(row.reported_on || '').slice(0, 10);
    if (!date) continue;
    if (!byDate.has(date)) {
      byDate.set(date, { date, buys: 0, sells: 0, buyValue: 0, sellValue: 0, valued: 0 });
    }
    const day = byDate.get(date);
    const value = num(row.value);
    if (side(row) === 'buy') {
      day.buys += 1;
      if (value) { day.buyValue += value; day.valued += 1; }
    } else {
      day.sells += 1;
      if (value) { day.sellValue += value; day.valued += 1; }
    }
  }
  const days = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
  let running = 0;
  for (const day of days) {
    day.net = day.buys - day.sells;
    day.netValue = day.buyValue - day.sellValue;
    running += day.net;
    day.cumulativeNet = running;
  }
  return days;
}

/** Companies several different insiders bought at a market price at once. */
export function clusters(rows, { windowDays = CLUSTER_WINDOW_DAYS, minBuyers = CLUSTER_MIN_BUYERS } = {}) {
  const buys = conviction(rows).filter((row) => side(row) === 'buy' && row.reported_on);
  if (!buys.length) return [];
  const latest = buys.map((row) => row.reported_on).sort().at(-1);
  const cutoff = new Date(`${latest}T00:00:00Z`);
  cutoff.setUTCDate(cutoff.getUTCDate() - windowDays);
  const from = cutoff.toISOString().slice(0, 10);

  const byCompany = new Map();
  for (const row of buys) {
    if (String(row.reported_on) < from) continue;
    const name = row.company_name;
    if (!byCompany.has(name)) {
      byCompany.set(name, {
        company: name, symbol: row.symbol || null, buyers: new Set(),
        filings: 0, quantity: 0, value: 0, valued: 0, lastReported: row.reported_on,
      });
    }
    const entry = byCompany.get(name);
    entry.buyers.add(lower(row.person));
    entry.filings += 1;
    entry.quantity += num(row.quantity) || 0;
    const value = num(row.value);
    if (value) { entry.value += value; entry.valued += 1; }
    if (row.reported_on > entry.lastReported) entry.lastReported = row.reported_on;
  }
  return [...byCompany.values()]
    .filter((entry) => entry.buyers.size >= minBuyers)
    .map(({ buyers, ...rest }) => ({ ...rest, buyers: buyers.size }))
    .sort((a, b) => b.buyers - a.buyers || b.value - a.value);
}

/**
 * Pledge activity, which the Supabase normaliser has no branch for and drops.
 *
 * A promoter pledging shares has borrowed against the company; a release means
 * the loan is settled. It is a risk disclosure, not a conviction one, so it is
 * reported on its own rather than folded into the buy and sell counts.
 */
export function pledges(rows) {
  const byCompany = new Map();
  for (const row of rows || []) {
    const text = `${row.action} ${row.mode}`;
    const created = PLEDGE_CREATE.test(text);
    const released = PLEDGE_RELEASE.test(text);
    if (!created && !released) continue;
    const name = row.company_name;
    if (!byCompany.has(name)) {
      byCompany.set(name, { company: name, symbol: row.symbol || null, created: 0, released: 0, quantity: 0, lastReported: row.reported_on });
    }
    const entry = byCompany.get(name);
    if (created) entry.created += 1; else entry.released += 1;
    entry.quantity += num(row.quantity) || 0;
    if (row.reported_on > entry.lastReported) entry.lastReported = row.reported_on;
  }
  return [...byCompany.values()].sort((a, b) => b.created - a.created || b.quantity - a.quantity);
}

/** How the shares actually changed hands, which is the whole point. */
export function modeBreakdown(rows) {
  const counts = new Map();
  for (const row of rows || []) {
    const label = String(row.mode || 'unspecified');
    if (!counts.has(label)) counts.set(label, { mode: label, count: 0, openMarket: isOpenMarket(row) });
    counts.get(label).count += 1;
  }
  return [...counts.values()].sort((a, b) => b.count - a.count);
}

// An insider filing is a director or promoter trading their own company. A SAST
// filing is an acquirer crossing a shareholding threshold under the takeover
// code - a market transaction, but not an insider one. They are counted apart
// because SAST filings never carry a price, so a combined value coverage figure
// reads as missing data when it is really two populations.
export const regimeOf = (row) => (String(row.regime || '').toLowerCase() === 'sast'
  || /sast/i.test(String(row.regulation || '')) ? 'sast' : 'insider');

export function summarise(rows, query = {}) {
  const all = dedupe(rows);
  const search = lower(query.search);
  const from = query.from ? String(query.from) : null;
  const to = query.to ? String(query.to) : null;

  const filtered = all.filter((row) => {
    const date = String(row.reported_on || '');
    if (from && date < from) return false;
    if (to && date > to) return false;
    if (search && !lower(`${row.company_name} ${row.person} ${row.symbol || ''}`).includes(search)) return false;
    if (query.signal === 'open_market' && !isOpenMarket(row)) return false;
    if (query.signal === 'buy' && side(row) !== 'buy') return false;
    if (query.signal === 'sell' && side(row) !== 'sell') return false;
    if (query.regime === 'insider' || query.regime === 'sast') {
      if (regimeOf(row) !== query.regime) return false;
    }
    return true;
  });

  const open = filtered.filter(isOpenMarket);
  const valued = filtered.filter((row) => num(row.value));
  const insider = filtered.filter((row) => regimeOf(row) === 'insider');
  const dates = filtered.map((row) => row.reported_on).filter(Boolean).sort();

  return {
    ok: true,
    source: 'warehouse',
    trades: filtered
      .slice()
      .sort((a, b) => String(b.reported_on).localeCompare(String(a.reported_on))
        || (num(b.value) || 0) - (num(a.value) || 0)),
    daily: dailyFlow(filtered),
    clusters: clusters(filtered),
    pledges: pledges(filtered),
    modes: modeBreakdown(filtered),
    stats: {
      records: filtered.length,
      companies: new Set(filtered.map((row) => lower(row.company_name))).size,
      openMarket: open.length,
      buys: open.filter((row) => side(row) === 'buy').length,
      sells: open.filter((row) => side(row) === 'sell').length,
      withTicker: filtered.filter((row) => row.symbol).length,
      firstDate: dates[0] || null,
      latestDate: dates.at(-1) || null,
      // Stated on the filings that report one. Presented separately from the
      // counts because a third of filings report no value at all, and adding a
      // partial total to a complete count would read as one number.
      valuedRecords: valued.length,
      observedValue: valued.reduce((sum, row) => sum + (num(row.value) || 0), 0),
      // Reported against insider filings alone. Coverage across everything
      // would read 61% and look like a collection failure; it is that SAST
      // filings disclose a shareholding change, not a price.
      insiderRecords: insider.length,
      sastRecords: filtered.length - insider.length,
      valueCoveragePct: insider.length
        ? Math.round((insider.filter((row) => num(row.value)).length / insider.length) * 1000) / 10
        : null,
    },
  };
}

export async function getInsiderActivityFromWarehouse(query = {}) {
  return summarise(await fetchRows(), query);
}
