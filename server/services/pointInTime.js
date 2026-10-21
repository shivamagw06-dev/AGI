/**
 * Point-in-time rules for the 13F backtest: when a disclosed portfolio first
 * becomes tradable, and which prices may be used to value it.
 *
 * Everything here replaces logic that was wrong in the same direction - each
 * defect flattered the manager - and that the UI simultaneously advertised as
 * correct ("Enter only after SEC acceptance, at the next available adjusted
 * close", persisted as `no_look_ahead: true`).
 *
 * What was wrong, in the order it mattered:
 *
 *   Entry took the acceptance day's own close. `priceAfter` searched with `>=`
 *   against the acceptance date, so a 13F accepted at 16:05 ET - after the
 *   close, which is when they cluster on the 45-day deadline - was entered at
 *   a price struck five minutes before the filing existed. The disclosed names
 *   tend to re-rate on the following session, so this handed the backtest the
 *   announcement move at every rebalance.
 *
 *   The date was derived in UTC. `new Date(x).toISOString().slice(0,10)` rolls
 *   over at 19:00 ET in winter and 20:00 ET in summer, so the boundary the code
 *   enforced was not the 16:00 ET close and moved by an hour twice a year.
 *   EDGAR acceptance timestamps are genuine UTC instants (verified: the same
 *   16:05 ET wall clock appears as 21:05Z in November and 20:05Z in August), so
 *   the offset is real, not a formatting artefact.
 *
 *   Missing prices were absorbed. A position with no price at either end was
 *   dropped and the remainder re-weighted to 100% - survivorship bias, since
 *   the names that go missing are disproportionately the delisted and acquired.
 *
 * The rules here are deliberately strict: when the data cannot answer, the
 * answer is "not calculable", never a number computed from what happens to be
 * present.
 */

const NY = 'America/New_York';

/** Wall-clock date and hour in US Eastern for a UTC instant. */
export function easternParts(instant) {
  const date = instant instanceof Date ? instant : new Date(instant);
  if (Number.isNaN(date.getTime())) return null;
  // en-CA gives ISO-ordered date parts, which is what we want to compare on.
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: NY,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(date).reduce((acc, part) => {
    acc[part.type] = part.value;
    return acc;
  }, {});
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    hour: Number(parts.hour),
    minute: Number(parts.minute),
  };
}

/** US equities close at 16:00 ET. A filing accepted at or after that is next-session news. */
export const MARKET_CLOSE_HOUR = 16;

/**
 * The first session a filing could actually have been traded on.
 *
 * Strictly after acceptance in every case. A filing accepted during a session
 * is still not tradable at that session's close for our purposes: the position
 * is only known once the filing is public, and treating the same close as
 * available is the look-ahead this whole module exists to remove. Entering on
 * the next session is the conservative reading, and conservative is the right
 * default for a number shown to a client.
 *
 * `sessions` is an ascending list of dates on which the market actually traded.
 * Deriving it from observed prices rather than a hardcoded holiday table means
 * it is correct for every year without maintenance, and automatically excludes
 * the half-days and unscheduled closures a static list forgets. The cost is
 * that a gap in price data looks like a holiday - which is why a position is
 * excluded rather than approximated when its series is incomplete.
 */
export function firstTradableSession(acceptedAt, sessions) {
  const parts = easternParts(acceptedAt);
  if (!parts || !Array.isArray(sessions) || !sessions.length) return null;
  // Every session strictly after the acceptance date qualifies. Acceptance at
  // or after the close on a trading day is already excluded by that, and so is
  // acceptance earlier in the same day.
  return sessions.find((session) => session > parts.date) || null;
}

/** Trading sessions observed in a price series, ascending and unique. */
export function sessionsFromPrices(rows) {
  const dates = new Set();
  for (const row of rows || []) {
    if (row?.price_date && row?.adjusted_close != null) dates.add(String(row.price_date));
  }
  return [...dates].sort();
}

/**
 * The adjusted close on an exact session.
 *
 * Exact, not nearest. A nearest-match lookup silently values a position at a
 * price from days or weeks away when its series has a hole, and reports the
 * result as though the data were there.
 */
export function closeOn(rows, date) {
  if (!date) return null;
  const row = (rows || []).find((candidate) => String(candidate.price_date) === date);
  const close = row?.adjusted_close;
  return close == null ? null : Number(close);
}

/**
 * Value a portfolio over one holding period.
 *
 * A position missing a price at either end is EXCLUDED and named. The weights
 * of the priced positions are not renormalized, so the return is reported
 * against the portfolio that was actually measurable and `coverage` states how
 * much of the disclosed portfolio that was. Renormalizing would present a
 * partial measurement as a complete one.
 */
export function periodReturn({ positions, prices, entryDate, exitDate, weightOf, keyOf }) {
  const weight = weightOf || ((row) => Number(row.value_usd) || 0);
  const key = keyOf || ((row) => row.ticker);

  const total = positions.reduce((sum, row) => sum + weight(row), 0);
  if (!total) return { value: null, coverage: 0, priced: 0, excluded: [], reason: 'no disclosed value' };

  const excluded = [];
  let weighted = 0;
  let covered = 0;

  for (const row of positions) {
    const series = prices.get(key(row)) || [];
    const start = closeOn(series, entryDate);
    const end = closeOn(series, exitDate);
    const share = weight(row) / total;

    if (start == null || end == null || start === 0) {
      excluded.push({
        key: key(row),
        weight: share,
        reason: start == null && end == null ? 'no price at entry or exit'
          : start == null ? 'no price at entry'
            : end == null ? 'no price at exit' : 'entry price was zero',
      });
      continue;
    }
    weighted += share * (end / start - 1);
    covered += share;
  }

  return {
    // Deliberately NOT weighted/covered. The excluded weight is treated as
    // holding flat, and coverage says how much of the portfolio that was, so a
    // thin period cannot masquerade as a complete one.
    value: covered > 0 ? weighted : null,
    coverage: covered,
    priced: positions.length - excluded.length,
    excluded,
  };
}

/**
 * Benchmark return over the same session pair as the portfolio.
 *
 * Returns null rather than zero when either end is missing. Zero was the
 * previous behaviour, and it meant a run with no SPY data reported
 * `spy_return: 0` and presented the entire strategy return as excess - status
 * still 'calculated'. A benchmark that was never measured must invalidate the
 * comparison, not win it.
 */
export function benchmarkReturn(series, entryDate, exitDate) {
  const start = closeOn(series, entryDate);
  const end = closeOn(series, exitDate);
  if (start == null || end == null || start === 0) return null;
  return end / start - 1;
}

/**
 * Order filings by when the market learned of them.
 *
 * Sorting by report_date is wrong once amendments exist: a 13F-HR/A for an
 * older quarter is accepted after later quarters' originals, so consecutive
 * pairs could produce an exit earlier than its entry - a negative holding
 * period, silently compounded. Ordering by acceptance and then discarding any
 * pair that does not advance keeps the chain monotonic.
 */
export function orderByAcceptance(filings) {
  return [...(filings || [])]
    .filter((filing) => filing?.accepted_at || filing?.filed_at)
    .sort((a, b) => String(a.accepted_at || a.filed_at).localeCompare(String(b.accepted_at || b.filed_at)));
}
