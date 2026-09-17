/**
 * Size, for Stage 2 of the screen.
 *
 * Upstox serves no company market cap and no share count. It does serve
 * P/B and, on a standalone basis, total assets and total liabilities - and
 * since P/B is price over book value per share, market cap is P/B times book
 * equity with no share count involved:
 *
 *   market cap = P/B x book equity
 *
 * That identity is exact. What is not exact is the basis. It holds only when
 * the P/B and the equity describe the same entity, and Upstox returns
 * consolidated statements empty while standalone statements carry rows, so
 * the equity available is standalone while the basis of the P/B is not
 * stated. For a single-operating-entity company the two books are close and
 * the derivation is sound. For a holding company they are not: Adani
 * Enterprises' standalone book is a fraction of its consolidated book, and
 * pairing a consolidated P/B with a standalone equity would understate its
 * market cap by a multiple rather than by a percent.
 *
 * So nothing here is presented as a disclosed figure. Every result is marked
 * derived, carries the inputs it came from, and must clear an independent
 * cross-check before a screen may use it. A derived market cap that no second
 * source agrees with is not a market cap, it is an arithmetic result.
 */

const numeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  // key-ratios values arrive as strings, sometimes with a percent sign.
  const parsed = Number(String(value).replace(/[%,\s]/g, ''));
  return Number.isFinite(parsed) ? parsed : null;
};

/** How far a derived market cap may sit from an independent one. */
export const CROSS_CHECK_TOLERANCE = 0.25;

/**
 * Book equity from a balance-sheet row.
 *
 * Upstox's standalone rows carry total_asset and total_liability and nothing
 * else, so equity is the difference. Returns the basis alongside it, because
 * the basis is the assumption that can invalidate everything downstream.
 */
export function bookEquityFrom(row, { basis = 'standalone' } = {}) {
  const assets = numeric(row?.total_asset);
  const liabilities = numeric(row?.total_liability);
  if (assets === null || liabilities === null) {
    return { equity: null, basis, period: row?.period ?? null, reason: 'NO_BALANCE_SHEET' };
  }
  const equity = assets - liabilities;
  if (equity <= 0) {
    return { equity: null, basis, period: row?.period ?? null, reason: 'NON_POSITIVE_EQUITY' };
  }
  return { equity, basis, period: row?.period ?? null, reason: null };
}

/** The free-float share, from the shareholding categories. */
export function freeFloatRatioFrom(shareHoldings) {
  const rows = Array.isArray(shareHoldings) ? shareHoldings : [];
  const promoters = rows.find((one) => /promoter/i.test(String(one?.category || '')));
  const latest = Array.isArray(promoters?.history) ? promoters.history[0] : null;
  const pct = numeric(latest?.value);
  if (pct === null) return { ratio: null, promoterPct: null, asOf: null, reason: 'NO_PROMOTER_HOLDING' };
  if (pct < 0 || pct > 100) return { ratio: null, promoterPct: pct, asOf: latest?.period ?? null, reason: 'IMPLAUSIBLE_PROMOTER_HOLDING' };
  // The categories should account for the whole register; if they do not,
  // the promoter figure may be on a different base than 100.
  const total = rows.reduce((sum, one) => {
    const value = numeric(Array.isArray(one?.history) ? one.history[0]?.value : null);
    return value === null ? sum : sum + value;
  }, 0);
  const accounted = Math.abs(total - 100) <= 1.5;
  return {
    ratio: (100 - pct) / 100,
    promoterPct: pct,
    asOf: latest?.period ?? null,
    categoriesSumTo: Number(total.toFixed(2)),
    reason: accounted ? null : 'CATEGORIES_DO_NOT_SUM_TO_100',
  };
}

const ratioNamed = (keyRatios, name) => {
  const rows = Array.isArray(keyRatios) ? keyRatios : [];
  const row = rows.find((one) => String(one?.name || '').trim().toLowerCase() === name);
  return numeric(row?.company_value);
};

/**
 * Free-float market cap, derived, with its lineage and its cross-check.
 *
 * `independentMarketCap` is required rather than optional. The identity is
 * exact and the basis assumption is not, so the only thing separating a
 * usable figure from a plausible-looking one is a second source agreeing with
 * it. Without one this refuses.
 */
export function freeFloatMarketCap({
  keyRatios, balanceSheetRow, shareHoldings, independentMarketCap = null,
  tolerance = CROSS_CHECK_TOLERANCE, basis = 'standalone',
}) {
  const pb = ratioNamed(keyRatios, 'p/b');
  const equity = bookEquityFrom(balanceSheetRow, { basis });
  const float = freeFloatRatioFrom(shareHoldings);

  const lineage = {
    formula: 'market_cap = pb * book_equity ; free_float_market_cap = market_cap * (1 - promoter_share)',
    inputs: {
      pb: { value: pb, source: 'upstox key-ratios', basis: 'not stated by the source' },
      book_equity: { value: equity.equity, source: `upstox balance-sheet (${equity.basis})`, period: equity.period },
      promoter_share: { value: float.promoterPct, source: 'upstox share-holdings', asOf: float.asOf },
    },
  };

  const missing = [];
  if (pb === null || pb <= 0) missing.push('pb');
  if (equity.equity === null) missing.push('book_equity');
  if (float.ratio === null) missing.push('free_float_ratio');
  if (missing.length) {
    return {
      value: null, marketCap: null, provenance: 'DERIVED', lineage,
      reason: `missing ${missing.join(', ')}`, crossCheck: null, usable: false,
    };
  }

  const marketCap = pb * equity.equity;
  const value = marketCap * float.ratio;

  const independent = numeric(independentMarketCap);
  if (independent === null || independent <= 0) {
    return {
      value: null, marketCap, provenance: 'DERIVED', lineage,
      reason: 'no independent market cap to check against; a derived figure nothing corroborates is arithmetic, not a market cap',
      crossCheck: { independent: null, gap: null, within: null }, usable: false,
    };
  }

  const gap = marketCap / independent - 1;
  const within = Math.abs(gap) <= tolerance;
  return {
    value: within ? value : null,
    marketCap,
    provenance: 'DERIVED',
    lineage,
    crossCheck: {
      independent,
      gap: Number(gap.toFixed(4)),
      within,
      tolerance,
    },
    // A gap this large is the basis mismatch showing itself - most likely a
    // consolidated P/B against a standalone book, which is exactly what a
    // holding company produces.
    reason: within ? null
      : `derived market cap is ${(gap * 100).toFixed(1)}% from the independent figure, beyond +/-${(tolerance * 100).toFixed(0)}%; the ${equity.basis} book is probably the wrong basis for this P/B`,
    usable: within,
    freeFloatRatio: float.ratio,
    freeFloatReason: float.reason,
  };
}
