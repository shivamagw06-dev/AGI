/**
 * What a disclosed position would be worth now.
 *
 * A 13F is stale the moment it is published - forty-five days after the
 * quarter it describes, and older every day after that. The most useful thing
 * prices add, short of a backtest, is the size of that gap.
 *
 * Two things decide whether the number is honest.
 *
 * The first is what it claims. A manager trades continuously between filings,
 * so "this position is worth X" asserts a holding nobody has disclosed. What
 * is computed here is a counterfactual - what the disclosed shares would be
 * worth at the latest close - and it has to be labelled as one wherever it is
 * shown. The difference is between reporting a filing and inventing a
 * portfolio.
 *
 * The second is the arithmetic. Yahoo's close is retroactively split-adjusted:
 * Apple's 2020-08-28 close comes back as 124.81, not the 499.23 it traded at.
 * A 13F share count is as-of the filing, so multiplying disclosed shares by
 * today's price is wrong by any split since. Taking the ratio of two closes on
 * the same adjusted basis makes splits cancel, and needs no share count at all:
 *
 *   value_now = disclosed_value * (close_now / close_on_report_date)
 *
 * Close rather than adjusted close, deliberately. Adjusted close folds in
 * dividends, which answers what the position would have returned - a different
 * question from what it is worth.
 */

const n = (value) => (Number.isFinite(Number(value)) ? Number(value) : 0);

/**
 * Revalue one position, or explain why it cannot be.
 *
 * A missing price at either end is not a zero and not a carry-forward: with no
 * close on the report date there is nothing to measure the move against, and
 * with no recent close the position has stopped trading or was never matched.
 */
export function revaluePosition(holding, prices) {
  const disclosed = n(holding?.value_usd);
  if (!disclosed) return { disclosed: 0, current: null, changePct: null, reason: 'no disclosed value' };

  const then = n(prices?.at_report_date);
  const now = n(prices?.at_latest_close);
  if (then <= 0) return { disclosed, current: null, changePct: null, reason: 'no price on the report date' };
  if (now <= 0) return { disclosed, current: null, changePct: null, reason: 'no recent price' };

  const current = disclosed * (now / then);
  return { disclosed, current, changePct: ((now - then) / then) * 100, reason: null };
}

/**
 * Revalue a book, and say how much of it could be revalued.
 *
 * The unpriced part is reported rather than dropped. A total that silently
 * omits what it could not price reads as the whole portfolio and understates
 * it by however much is missing - the same failure as re-weighting a backtest
 * to a hundred per cent after discarding the delisted names.
 */
export function revalueBook(holdings, pricesByKey, keyOf) {
  let disclosedTotal = 0;
  let currentTotal = 0;
  let pricedDisclosed = 0;
  const unpriced = [];

  for (const holding of holdings || []) {
    if (holding?.put_call) continue;
    const disclosed = n(holding.value_usd);
    disclosedTotal += disclosed;

    const result = revaluePosition(holding, pricesByKey?.get?.(keyOf(holding)));
    if (result.current === null) {
      if (disclosed > 0) unpriced.push({ key: keyOf(holding), disclosed, reason: result.reason });
      continue;
    }
    pricedDisclosed += disclosed;
    currentTotal += result.current;
  }

  if (!pricedDisclosed) {
    return {
      disclosed_total: disclosedTotal, current_total: null, change_pct: null,
      priced_share_pct: 0, unpriced_count: unpriced.length, unpriced_value: disclosedTotal,
    };
  }

  return {
    disclosed_total: disclosedTotal,
    // The revalued figure covers only the priced part of the book, and says so.
    // Scaling it up to the whole would invent the movement of what it could
    // not see.
    current_total: currentTotal,
    priced_disclosed: pricedDisclosed,
    change_pct: ((currentTotal - pricedDisclosed) / pricedDisclosed) * 100,
    priced_share_pct: disclosedTotal ? (pricedDisclosed / disclosedTotal) * 100 : 0,
    unpriced_count: unpriced.length,
    unpriced_value: disclosedTotal - pricedDisclosed,
  };
}
