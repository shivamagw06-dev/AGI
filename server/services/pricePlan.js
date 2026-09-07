/**
 * Deciding what price history to fetch, and what to do with what comes back.
 *
 * Kept apart from the script so the judgement calls can be tested without a
 * network or a database: which symbols are worth a request, how far back each
 * one needs, which rows get written, and when a run should stop rather than
 * carry on producing garbage.
 */

/** Symbols Yahoo cannot mean, and the junk the SEC's own ticker file carries. */
const REJECT = new Set(['NONE.', 'NONE', 'N/A', 'NA', '-', '']);

/**
 * A US ticker: one to five letters, optionally a share-class suffix.
 *
 * Anything else in this column came from a foreign venue - HO1 and 8QR are
 * Frankfurt line codes, ACLXGBX and HONGBP are US shares quoted abroad in
 * local currency. A 13F security is US-exchange-traded, so none of those can
 * be priced under that name and asking is a request spent to be told no.
 */
const US_TICKER = /^[A-Z]{1,5}(-[A-Z])?$/;

/**
 * Yahoo's symbol for a ticker, or null if the ticker is not usable.
 *
 * The SEC's company_tickers.json and Yahoo agree on share-class punctuation -
 * both write BRK-B - so this is close to identity. It is a function anyway
 * because the one time they disagreed (BRK.B is a 404 on Yahoo) the failure
 * was silent: the symbol simply returned no history and the security looked
 * delisted.
 */
export function yahooSymbol(ticker) {
  const t = String(ticker || '').trim().toUpperCase();
  if (!t || REJECT.has(t)) return null;
  if (!/^[A-Z0-9.\-]{1,12}$/.test(t)) return null;
  // A dot is Yahoo's suffix separator (RELIANCE.NS), not a share-class mark.
  // A US ticker carrying one is using the other convention, so translate it.
  return t.includes('.') ? t.replace(/\./g, '-') : t;
}

/**
 * Plan one request per symbol we hold.
 *
 * `from` is the earliest date the symbol is held, less a buffer: a backtest
 * that opens a position on the first report date needs a price on the session
 * before it to measure anything, and a quarter of slack costs one request.
 */
export function planFetches(holdings, { asOf, bufferDays = 120, freshness = null } = {}) {
  const bySymbol = new Map();
  const skipped = { unusableTicker: 0, alreadyFresh: 0, foreignVenue: 0 };
  const foreignVenueSymbols = new Set();

  for (const row of holdings || []) {
    const symbol = yahooSymbol(row?.ticker);
    if (!symbol) { skipped.unusableTicker += 1; continue; }
    // Known-unpriceable before a request is spent on it. These also skewed
    // the health check: they sort to the front of the alphabet, so the first
    // symbols processed were almost all of them and the run aborted on a
    // sample made of the one group already known to fail.
    if (!US_TICKER.test(symbol)) {
      if (!foreignVenueSymbols.has(symbol)) { foreignVenueSymbols.add(symbol); skipped.foreignVenue += 1; }
      continue;
    }
    const key = String(row?.security_key || '').trim().toUpperCase();
    if (!key) continue;

    if (!bySymbol.has(symbol)) {
      bySymbol.set(symbol, { symbol, ticker: row.ticker, securityKeys: new Set(), earliest: null, latest: null });
    }
    const plan = bySymbol.get(symbol);
    plan.securityKeys.add(key);
    const seen = row?.first_report_date || row?.report_date;
    if (seen && (!plan.earliest || seen < plan.earliest)) plan.earliest = seen;
    const last = row?.last_report_date || row?.report_date;
    if (last && (!plan.latest || last > plan.latest)) plan.latest = last;
  }

  const plans = [];
  for (const plan of bySymbol.values()) {
    // Skip a symbol whose stored history already reaches the run date. A
    // 3,400-symbol run gets interrupted; without this, resuming refetches
    // everything and the second attempt is as long as the first.
    const have = freshness?.get?.(plan.symbol);
    if (have && asOf && daysBetween(have, asOf) <= 4) { skipped.alreadyFresh += 1; continue; }

    const start = new Date(plan.earliest || asOf);
    start.setUTCDate(start.getUTCDate() - bufferDays);
    plans.push({
      symbol: plan.symbol,
      ticker: plan.ticker,
      securityKeys: [...plan.securityKeys].sort(),
      // The date the security is first held, kept separately from the buffered
      // request start because it is what the returned history has to cover.
      earliestHeld: plan.earliest || null,
      // Still held as at the most recent filings. A symbol in this set should
      // almost always be live, which is what makes it a usable health signal:
      // a delisted name failing is expected, a current holding failing is not.
      heldNow: Boolean(plan.latest && asOf && daysBetween(plan.latest, asOf) <= 200),
      from: start.toISOString().slice(0, 10),
      to: asOf,
    });
  }
  // Ordered by a hash of the symbol, not alphabetically. Alphabetical order
  // correlates with what a symbol is - digits and venue codes sort first - so
  // any statistic taken over the first N processed describes that group
  // rather than the run. The hash is deterministic, so a resumed run walks
  // the same order and stays reproducible.
  plans.sort((a, b) => spread(a.symbol) - spread(b.symbol) || a.symbol.localeCompare(b.symbol));
  return { plans, skipped, foreignVenueSymbols: [...foreignVenueSymbols].sort() };
}

/** A stable pseudo-random ordering key. FNV-1a, chosen for being short. */
function spread(symbol) {
  let h = 2166136261;
  for (let i = 0; i < symbol.length; i += 1) {
    h ^= symbol.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function daysBetween(a, b) {
  const d = (Date.parse(b) - Date.parse(a)) / 86_400_000;
  return Number.isFinite(d) ? d : Infinity;
}

/**
 * Turn one symbol's bars into rows, one per security key holding it.
 *
 * A ticker can belong to more than one key when a share-class merge left two
 * identifiers sharing a symbol. Both get the series rather than one of them
 * being picked, because picking would leave the other silently priceless.
 */
export function priceRows(plan, bars, { source, listingStatus, sourceAsOf }) {
  const rows = [];
  for (const key of plan.securityKeys) {
    for (const bar of bars) {
      rows.push({
        security_key: key,
        ticker: plan.ticker,
        security_type: 'equity',
        price_date: bar.price_date,
        close: bar.close,
        adjusted_close: bar.adjusted_close,
        currency: bar.currency,
        listing_status: listingStatus,
        source,
        source_as_of: sourceAsOf,
      });
    }
  }
  return rows;
}

/**
 * Whether a run has gone wrong badly enough that it should stop.
 *
 * A backfill that keeps going while every request fails does not produce a
 * partial history - it produces a confident-looking table with holes in it,
 * and nothing downstream can tell the holes from genuinely untraded days. The
 * thresholds only apply once there is enough of a sample to mean anything.
 */
export function abortReason(tally, { minSample = 40, maxNotFound = 0.25, maxFailed = 0.25 } = {}) {
  const done = tally.ok + tally.empty + tally.notFound + tally.failed;
  if (done < minSample) return null;

  // Unknown symbols are measured only over securities still held, because
  // Yahoo drops delisted tickers entirely - Twitter, Activision and VMware
  // all 404 - and a seven-year holdings history is full of them. Counting
  // those as breakage would abort every healthy run; ignoring current
  // holdings would miss a genuinely broken ticker mapping.
  // Without a current-holdings sample there is no way to tell a wave of
  // delistings from a broken mapping, so unknown symbols are not judged at
  // all rather than guessed at. Callers always pass one; this is the floor.
  const live = tally.live;
  if (live && live.done >= minSample && live.notFound / live.done > maxNotFound) {
    return `${pct(live.notFound, live.done)} of ${live.done} currently-held symbols unknown to Yahoo`
      + ' - the ticker mapping or the symbol convention is wrong, not the individual symbols';
  }
  if (tally.failed / done > maxFailed) {
    return `${pct(tally.failed, done)} of ${done} requests failed - upstream is refusing traffic; the history would have holes that look like untraded days`;
  }
  return null;
}

const pct = (n, d) => `${((n / d) * 100).toFixed(1)}%`;


/**
 * Does this history actually belong to the security we hold?
 *
 * A ticker outlives the company that used it. Facebook became META in 2022;
 * ask Yahoo for FB today and it answers - not with an error, and not with
 * Facebook, but with a live and unrelated company that took the symbol over,
 * whose history begins in 2025. Nothing in the response marks the handover.
 * Stored against a 2019 Facebook holding it would price that position off
 * another company's chart, and every number built on it would be wrong while
 * looking entirely healthy.
 *
 * The tell is coverage: a security held on a date traded on that date, so its
 * history has to reach back to it. When the history begins long after the
 * position does, the symbol has changed hands and the series is not ours.
 */
export function coverageProblem(plan, bars, { graceDays = 10, minBars = 20 } = {}) {
  if (!bars?.length) return 'no history returned';
  const held = plan?.earliestHeld;
  if (!held) return null;

  const firstBar = bars[0].price_date;
  const gap = daysBetween(held, firstBar);
  if (gap <= graceDays) return null;

  // Two different things produce history that begins after the position, and
  // saying which is which matters because one of them names a cause.
  //
  // A full series starting years late is a ticker that changed hands: FB is
  // a live company with thousands of bars, none of them Facebook's.
  //
  // A handful of bars is not that. RMAX, HTZWW and AUROW each come back with
  // exactly one bar on one recent day - a stub, not another company's chart.
  // Calling that a reassignment asserts a cause nobody has established. It is
  // refused either way, since one bar prices nothing, but the reason given
  // has to be something the response actually shows.
  if (bars.length < minBars) {
    return `only ${bars.length} bar${bars.length === 1 ? '' : 's'} returned`
      + ` (${firstBar}${bars.length > 1 ? `..${bars.at(-1).price_date}` : ''}),`
      + ` no usable history for a position held from ${held}`;
  }
  return `history starts ${firstBar} but the position is held from ${held}`
    + ` (${Math.round(gap)} days) - the symbol now belongs to a different security`;
}
