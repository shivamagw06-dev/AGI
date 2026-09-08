/**
 * The positions a manager moved most this quarter.
 *
 * Ranked by change in portfolio weight rather than by share count or dollars,
 * because weight is the manager's own scaling. Ten million dollars is a
 * conviction for one filer and a rounding error for another, and a table
 * sorted on it says more about fund size than about what anybody decided.
 *
 * Two distinctions the ranking keeps rather than flattening.
 *
 * A new position and an addition to an existing one are different acts. A
 * manager opening at three per cent has committed to something it did not
 * hold; one moving from twelve to fifteen has not. Both appear, labelled.
 *
 * And an exit is not a reduction. The weight change of an exit is the whole
 * previous position, so an exit will outrank every trim on that measure - it
 * should, but a reader has to be able to see which it is.
 */

const n = (value) => (Number.isFinite(Number(value)) ? Number(value) : 0);

const BUY_TYPES = new Set(['new', 'increased']);
const SELL_TYPES = new Set(['reduced', 'exited']);

/**
 * Rank the quarter's changes into buys and sells.
 *
 * `valueByCusip` supplies the disclosed value where a position still exists,
 * so a row can state what it is worth as well as what it weighs. An exited
 * position has no current value and says so rather than showing zero.
 */
export function topTrades(changes, { valueByCusip = null, limit = 6 } = {}) {
  const rows = (changes || []).map((row) => {
    const weightChange = n(row.weight_change);
    // A new position has no previous weight, so a percentage change is
    // infinite. The move is the weight itself, which the reader can see.
    const sharePct = n(row.previous_shares) > 0 ? row.share_change_pct : null;
    return {
      cusip: row.cusip,
      ticker: row.ticker,
      issuer_name: row.issuer_name,
      change_type: row.change_type,
      weight_change: weightChange,
      current_weight: n(row.current_weight),
      previous_weight: n(row.previous_weight),
      share_change: n(row.share_change),
      share_change_pct: sharePct === null || sharePct === undefined ? null : Number(sharePct),
      // Null for an exit: there is no position left to value, and zero would
      // read as a holding worth nothing.
      current_value_usd: row.change_type === 'exited' ? null : (valueByCusip?.get?.(row.cusip) ?? null),
      opened: row.change_type === 'new',
      closed: row.change_type === 'exited',
    };
  });

  const buys = rows.filter((r) => BUY_TYPES.has(r.change_type) && r.weight_change > 0)
    .sort((a, b) => b.weight_change - a.weight_change).slice(0, limit);
  // Sorted by the size of the reduction, so the largest retreat leads.
  const sells = rows.filter((r) => SELL_TYPES.has(r.change_type) && r.weight_change < 0)
    .sort((a, b) => a.weight_change - b.weight_change).slice(0, limit);

  return {
    buys,
    sells,
    // Counted over everything, not just what is shown, so a table of six is
    // not mistaken for the whole quarter.
    total_buys: rows.filter((r) => BUY_TYPES.has(r.change_type)).length,
    total_sells: rows.filter((r) => SELL_TYPES.has(r.change_type)).length,
    opened: rows.filter((r) => r.opened).length,
    closed: rows.filter((r) => r.closed).length,
  };
}
