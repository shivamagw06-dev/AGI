/**
 * Market value of the admitted members, by layer and by sector.
 *
 *   market value = last close x equity shares outstanding
 *
 * The close is the exchange's, from Upstox daily candles. The share count is
 * each company's own, from its latest exchange filing, checked in with the
 * filing and the line it came from (config/india-ai-enablers.shares.json).
 * Upstox serves no share count, and neither its shareholding percentages nor
 * its "equity capital" row (which is total equity) can be turned into one.
 *
 * This is the market value of the whole company, not of its AI business.
 * Most members are NOT_ATTRIBUTABLE: no filing states what part of revenue or
 * assets serves data centres. A layer's total therefore says how much listed
 * value carries a filed AI-infrastructure link, and nothing about how much of
 * that value the link explains.
 *
 * Two checks stand between a product and a published figure:
 *
 * - A share count dated before a bonus, split or rights ex-date that falls on
 *   or before the close is out of date by construction. That member is left
 *   out of every total, with the reason, until the count is refreshed.
 * - P/B x book equity is an independent route to the same quantity. A gap
 *   beyond the tolerance is flagged, not excluded: for a holding company the
 *   P/B route is the one that is wrong (see aiEnablersSize.js), and the filed
 *   share count times the exchange close is the more direct figure.
 */

export const CRORE = 1e7;
export const MARKET_VALUE_TOLERANCE = 0.25;

/**
 * Upstox spells some sectors two ways. Only those spellings are merged, so
 * one industry is one bar; every other label is Upstox's as given, and the
 * original label travels with each row.
 */
export const SECTOR_ALIASES = Object.freeze({
  Cables: 'Cable',
  'Capital Goods - Electrical Equipment': 'Electric Equipment',
});

export const canonicalSector = (label) => (label ? SECTOR_ALIASES[label] || label : null);

/**
 * Stage 2 rows on filed shares.
 *
 *   free-float market value = close x filed shares x (1 - promoter share)
 *
 * Replaces P/B x book as the size basis: measured against the filed counts
 * that route missed by more than five times (GE Vernova T&D) and in both
 * directions, so a floor applied to it would have screened on the error.
 * The promoter share is the member's own BSE shareholding pattern where it
 * has been read (the filing its share count came from), and Upstox's
 * shareholding figure otherwise; each row says which. A member with no
 * market value or no float is unscreened with the reason, not sized.
 *
 * `floats`: { [symbol]: { ratio, asOf, reason } }
 * `turnover`: { [symbol]: INR }
 */
export function filedSizeRows(rows, { floats = {}, turnover = {} } = {}) {
  return rows.map((row) => {
    const float = floats[row.symbol] || {};
    const ratio = Number.isFinite(float.ratio) && float.ratio > 0 && float.ratio <= 1 ? float.ratio : null;
    let reason = null;
    if (row.marketValueCr == null) reason = row.status;
    else if (ratio === null) reason = 'NO_FREE_FLOAT_RATIO';
    return {
      symbol: row.symbol,
      marketValueCr: row.marketValueCr,
      freeFloatRatio: ratio,
      floatAsOf: float.asOf ?? null,
      floatSource: float.source ?? null,
      floatNote: float.reason ?? null,
      freeFloatMarketCap: reason ? null : Number((row.marketValueCr * ratio).toFixed(2)),
      medianDailyTurnover: turnover[row.symbol] ?? null,
      reason,
    };
  });
}

/** The last close on or before `through`, from a Map(date -> close). */
export function lastCloseThrough(closes, through) {
  let found = null;
  for (const [date, close] of closes || []) {
    if (date <= through && (!found || date > found.date)) found = { date, close };
  }
  return found;
}

/**
 * One row per member.
 *
 * `shares`: { [symbol]: { shares, asOf, source } }
 * `closes`: { [symbol]: { date, close } }
 * `exDates`: { [symbol]: Set(date) }
 * `pbMarketCaps`: { [symbol]: crore }, P/B x book, may be missing
 */
export function marketValueRows({
  members = [], shares = {}, closes = {}, exDates = {}, pbMarketCaps = {}, tolerance = MARKET_VALUE_TOLERANCE,
} = {}) {
  return members.map((member) => {
    const base = { symbol: member.symbol, name: member.name, layer: member.layer };
    const filed = shares[member.symbol];
    const last = closes[member.symbol];
    if (!filed || !(filed.shares > 0)) return { ...base, marketValueCr: null, status: 'NO_SHARE_COUNT' };
    if (!last || !(last.close > 0)) return { ...base, marketValueCr: null, status: 'NO_CLOSE', shares: filed.shares, sharesAsOf: filed.asOf };
    const stale = [...(exDates[member.symbol] || [])].filter((date) => date > filed.asOf && date <= last.date).sort();
    const common = {
      ...base, close: last.close, closeDate: last.date, shares: filed.shares, sharesAsOf: filed.asOf, sharesSource: filed.source,
    };
    if (stale.length) {
      return { ...common, marketValueCr: null, status: 'SHARE_COUNT_PREDATES_CORPORATE_ACTION', exDate: stale[0] };
    }
    const marketValueCr = Number(((last.close * filed.shares) / CRORE).toFixed(2));
    const pb = Number(pbMarketCaps[member.symbol]);
    let crossCheck = { pbBookCr: null, gap: null, within: null };
    if (Number.isFinite(pb) && pb > 0) {
      const gap = marketValueCr / pb - 1;
      crossCheck = { pbBookCr: Number(pb.toFixed(2)), gap: Number(gap.toFixed(4)), within: Math.abs(gap) <= tolerance };
    }
    return { ...common, marketValueCr, status: 'OK', crossCheck };
  });
}

/**
 * Totals by a key, over the rows that have a market value.
 *
 * Rows without one are listed, never silently dropped: a layer total that
 * omits a member has to say which.
 */
export function totalsBy(rows, keyOf) {
  const priced = rows.filter((row) => row.marketValueCr != null);
  const total = priced.reduce((sum, row) => sum + row.marketValueCr, 0);
  const groups = new Map();
  for (const row of priced) {
    const key = keyOf(row) || 'Not stated';
    const group = groups.get(key) || { key, marketValueCr: 0, members: [] };
    group.marketValueCr += row.marketValueCr;
    group.members.push(row.symbol);
    groups.set(key, group);
  }
  return {
    totalCr: Number(total.toFixed(2)),
    groups: [...groups.values()]
      .map((group) => ({
        ...group,
        marketValueCr: Number(group.marketValueCr.toFixed(2)),
        share: total > 0 ? Number((group.marketValueCr / total).toFixed(4)) : null,
      }))
      .sort((a, b) => b.marketValueCr - a.marketValueCr),
    leftOut: rows.filter((row) => row.marketValueCr == null).map((row) => ({ symbol: row.symbol, status: row.status })),
  };
}
