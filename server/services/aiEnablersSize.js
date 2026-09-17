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

/**
 * The balance sheet on the basis that actually carries data.
 *
 * Upstox defaults to consolidated and returns it empty for a company that has
 * no consolidated statements to report - which is not a fault but a fact
 * about the company: a business with no subsidiaries has only a standalone
 * book, and for it standalone *is* the whole company. The basis question that
 * makes this derivation risky therefore does not arise for those names at
 * all. It arises for holding companies, which do have both - so consolidated
 * is preferred wherever it exists, and the basis actually used is recorded
 * rather than assumed.
 *
 * `units_in` is read rather than trusted. Upstox documents crore, and the
 * whole derivation is denominated in it.
 */
export function balanceSheetRowFrom(payloads) {
  for (const [basis, payload] of payloads) {
    const body = payload?.data;
    const history = Array.isArray(body?.history) ? body.history : [];
    if (!history.length) continue;
    const units = String(body?.units_in || '').trim().toLowerCase();
    if (units && units !== 'crore') {
      return { row: null, basis, units, reason: 'UNEXPECTED_UNITS' };
    }
    // Upstox's own "Equity Capital" line, when the detailed breakdown was
    // asked for. It equals total assets less total liabilities in their
    // documented example, so where both are present they must agree - and a
    // disagreement means the row is not what it is taken to be.
    const stated = (Array.isArray(body?.full_statement) ? body.full_statement : [])
      .find((one) => /^equity capital$/i.test(String(one?.particular || '').trim()));
    const statedValue = numeric(Array.isArray(stated?.history)
      ? stated.history.find((one) => one?.period === history[0]?.period)?.value
      : null);
    return {
      row: history[0], basis, units: units || 'crore', statedEquity: statedValue, reason: null,
      periods: history.length,
    };
  }
  return { row: null, basis: null, units: null, reason: 'NO_BALANCE_SHEET_ON_ANY_BASIS' };
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

/**
 * Market cap the other way round: P/E times net income.
 *
 * An independent path to the same quantity, and the point of having it is the
 * disagreement. Both ratios come from key-ratios and both are price-relative,
 * but this one runs through the income statement while the P/B route runs
 * through the balance sheet. For a single-operating-entity company they land
 * in the same place. For a holding company priced on consolidated ratios but
 * measured on standalone statements they do not, because net income and book
 * equity do not scale between the two books by the same factor - which is
 * exactly the error that would otherwise pass unseen.
 *
 * Weaker than a third party, and it is not presented as one: this checks
 * internal consistency, not external truth. Two figures agreeing here means
 * the basis is coherent, not that the market agrees with either.
 */
export function marketCapFromEarnings({ keyRatios, netIncome }) {
  const pe = ratioNamed(keyRatios, 'p/e');
  const income = numeric(netIncome);
  if (pe === null || pe <= 0) return { value: null, reason: 'NO_PE' };
  if (income === null) return { value: null, reason: 'NO_NET_INCOME' };
  // A loss-making company has no meaningful P/E-implied market cap; the ratio
  // is either negative or omitted, and multiplying by a negative income
  // would produce a positive number for the wrong reason.
  if (income <= 0) return { value: null, reason: 'NON_POSITIVE_NET_INCOME' };
  return { value: pe * income, reason: null };
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

/**
 * Size for every admitted member, Upstox derived and Yahoo checked.
 *
 * Fetchers are injected so this is testable without a network and without
 * credentials. Yahoo is a cross-check and never a source: where it is
 * unreachable, every member comes back unusable with that reason, because a
 * derivation nothing corroborates must not quietly become a screen input.
 */
export async function sizeForUniverse(universe, {
  fetchFundamentals, fetchMarketCaps = null, tolerance = CROSS_CHECK_TOLERANCE,
  // Consolidated first, standalone second. time_period is not a parameter
  // this endpoint takes - only type and fs - so it is not sent.
  balanceSheetBases = ['consolidated', 'standalone'],
  crossCheckSource = fetchMarketCaps ? 'external' : 'earnings',
  netIncomeFor = null,
} = {}) {
  const members = (universe?.members || []).filter((one) => one.admitted !== false);
  // An external cross-check is used when one is supplied and reachable.
  // Yahoo's quote endpoint began returning 401, so the fallback is the
  // earnings route: P/E times net income, independent of the balance sheet.
  const external = fetchMarketCaps
    ? await fetchMarketCaps(members.map((one) => one.symbol))
    : { bySymbol: {}, error: null };
  const caps = external.bySymbol;
  const capsError = external.error;

  const rows = {};
  for (const member of members) {
    const independent = caps?.[member.symbol] || null;
    try {
      const [keyRatios, shareHoldings, ...sheets] = await Promise.all([
        fetchFundamentals(member.isin, 'key-ratios', {}),
        fetchFundamentals(member.isin, 'share-holdings', {}),
        ...balanceSheetBases.map((type) => fetchFundamentals(member.isin, 'balance-sheet', { type, fs: true })),
      ]);
      const chosen = balanceSheetRowFrom(balanceSheetBases.map((type, i) => [type, sheets[i]]));
      // Prefer an external figure; fall back to the earnings route when
      // there is none, so a dead third party does not make every size
      // unverifiable.
      const earnings = netIncomeFor
        ? marketCapFromEarnings({ keyRatios: keyRatios?.data, netIncome: await netIncomeFor(member) })
        : { value: null, reason: 'NO_EARNINGS_SOURCE' };
      const checkAgainst = independent?.crore ?? earnings.value ?? null;
      const checkedBy = independent?.crore != null ? crossCheckSource : (earnings.value != null ? 'earnings' : null);

      const size = freeFloatMarketCap({
        keyRatios: keyRatios?.data,
        balanceSheetRow: chosen.row,
        shareHoldings: shareHoldings?.data,
        independentMarketCap: checkAgainst,
        tolerance,
        basis: chosen.basis || 'unknown',
      });
      if (size.crossCheck) size.crossCheck.checkedBy = checkedBy;

      // Upstox's own Equity Capital line against the subtraction. They are
      // the same quantity, so a gap means the row is not what it is taken
      // to be and the derivation should not proceed on it.
      if (chosen.statedEquity != null && size.lineage?.inputs?.book_equity?.value != null) {
        const computed = size.lineage.inputs.book_equity.value;
        const drift = Math.abs(chosen.statedEquity / computed - 1);
        size.lineage.inputs.book_equity.statedEquityCapital = chosen.statedEquity;
        size.lineage.inputs.book_equity.agreesWithStated = drift < 0.005;
        if (drift >= 0.005) {
          size.usable = false;
          size.value = null;
          size.reason = `total assets less total liabilities (${computed.toFixed(2)}) disagrees with the Equity Capital line (${chosen.statedEquity.toFixed(2)})`;
        }
      }
      if (chosen.reason === 'UNEXPECTED_UNITS') {
        size.usable = false;
        size.value = null;
        size.reason = `balance sheet reported in ${chosen.units}, not crore`;
      }
      rows[member.symbol] = {
        ...size,
        basisUsed: chosen.basis,
        basisPeriods: chosen.periods ?? 0,
        independent: {
          crore: checkAgainst,
          source: checkedBy,
          unit: 'inr_crore',
          reason: checkAgainst === null
            ? (capsError || independent?.reason || earnings.reason || 'NOT_RETURNED')
            : null,
        },
        earningsRoute: earnings,
      };
    } catch (error) {
      rows[member.symbol] = {
        value: null, marketCap: null, provenance: 'DERIVED', usable: false,
        reason: String(error?.message || error), lineage: null, crossCheck: null,
        independent: { crore: independent?.crore ?? null, source: 'yahoo', unit: 'inr_crore', reason: independent?.reason ?? null },
      };
    }
  }

  const usable = Object.entries(rows).filter(([, one]) => one.usable).map(([symbol]) => symbol);
  return {
    bySymbol: rows,
    usable,
    refused: Object.entries(rows).filter(([, one]) => !one.usable).map(([symbol, one]) => ({ symbol, reason: one.reason })),
    crossCheckSource,
    crossCheckError: capsError,
  };
}

/** Just the sizes a screen may use, in the shape stageTwo reads. */
export function sizeRows(sizes, liquidity = {}) {
  return Object.entries(sizes?.bySymbol || {}).map(([symbol, one]) => ({
    symbol,
    freeFloatMarketCap: one.usable ? one.value : null,
    medianDailyTurnover: liquidity?.[symbol] ?? null,
  }));
}
