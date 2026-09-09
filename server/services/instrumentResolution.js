/**
 * Matching a research table's ticker to an NSE instrument.
 *
 * A research note names an Indian stock the way Bloomberg does, and Bloomberg
 * is not NSE. Measured against a real FTSE review table, an exact match on the
 * symbol resolved 20 of 38 names. The other 18 fail in two distinct ways:
 *
 *   Bloomberg caps a ticker at eight characters, so a longer NSE symbol is
 *   truncated - ACMESOLA for ACMESOLAR, METROBRA for METROBRAND.
 *
 *   Established names carry a legacy ticker that shares nothing with the
 *   exchange symbol - INFO for INFY, IIB for INDUSINDBK, WPRO for WIPRO.
 *
 * The company name in the same row resolves 16 of those 18, so it is the
 * strong tier and it runs before the prefix.
 *
 * That order is not cosmetic. INFO prefix-matches INFOMEDIA and INFOBEANS,
 * neither of which is Infosys; the uniqueness guard refuses it and the name
 * finds INFY. A prefix rule that fired first, or that resolved ambiguity by
 * taking the first row, would price a different company - and that failure is
 * silent, because a wrong instrument returns perfectly good candles.
 */

const SUFFIXES = /\b(LIMITED|LTD|PVT|PRIVATE|CORPORATION|CORP|COMPANY|CO|INC|PLC|THE)\b/g;

/**
 * A company name reduced to something comparable.
 *
 * Suffixes go because "Bata India" and "BATA INDIA LTD" are the same company
 * and the difference is a filing convention, not information.
 */
export function normalizeName(text) {
  return String(text || '')
    .toUpperCase()
    .replace(/&/g, ' AND ')
    .replace(SUFFIXES, ' ')
    .replace(/[^A-Z0-9]/g, '');
}

/** Bloomberg's ticker length limit, and therefore its truncation signature. */
export const BLOOMBERG_TICKER_LENGTH = 8;

/**
 * Pick an instrument, or refuse and say why.
 *
 * `instruments` is the whole NSE cash list - about two thousand six hundred
 * rows, small enough to match in memory, which keeps every rule here pure and
 * testable rather than spread across SQL.
 *
 * Refusing is a real outcome. An unresolved entry keeps a null instrument_key
 * and stays visible on the page with its entered columns; a wrongly resolved
 * one prices a different company and reports days-of-ADVT for a business
 * nobody flagged. The second is much worse and never errors.
 */
export function resolveInstrument({ ticker, company } = {}, instruments = []) {
  const symbol = String(ticker || '').trim().toUpperCase();
  if (!symbol) return { instrument_key: null, matched_by: null, reason: 'no ticker' };

  const exact = instruments.filter((row) => String(row?.trading_symbol || '').toUpperCase() === symbol);
  if (exact.length === 1) return { instrument_key: exact[0].instrument_key, matched_by: 'symbol', reason: null };

  const wantedName = normalizeName(company);
  if (wantedName.length >= 4) {
    // Prefix rather than equality: the exchange writes "SKF IND (INDUSTRIAL)
    // LTD" where a note writes "SKF India". Requiring four characters keeps a
    // two-letter fragment from matching half the exchange.
    const byName = instruments.filter((row) => normalizeName(row?.name).startsWith(wantedName));
    if (byName.length === 1) return { instrument_key: byName[0].instrument_key, matched_by: 'name', reason: null };
    if (byName.length > 1) {
      return { instrument_key: null, matched_by: null, reason: `company name matches ${byName.length} instruments` };
    }
  }

  // Only at the truncation length. A short ticker prefix-matching a longer
  // symbol is coincidence, not truncation - and it is the coincidences that
  // silently price the wrong company.
  if (symbol.length >= BLOOMBERG_TICKER_LENGTH) {
    const byPrefix = instruments.filter((row) => String(row?.trading_symbol || '').toUpperCase().startsWith(symbol));
    if (byPrefix.length === 1) return { instrument_key: byPrefix[0].instrument_key, matched_by: 'truncated symbol', reason: null };
    if (byPrefix.length > 1) {
      return { instrument_key: null, matched_by: null, reason: `truncated symbol matches ${byPrefix.length} instruments` };
    }
  }

  return { instrument_key: null, matched_by: null, reason: 'no NSE instrument matched this ticker or company name' };
}

/** Resolve a batch, and summarise how each tier performed. */
export function resolveAll(rows = [], instruments = []) {
  const resolved = [];
  const unresolved = [];
  const byTier = new Map();

  for (const row of rows || []) {
    const result = resolveInstrument({ ticker: row?.exchange_symbol || row?.source_ticker, company: row?.company_name }, instruments);
    if (result.instrument_key) {
      resolved.push({ ...row, ...result });
      byTier.set(result.matched_by, (byTier.get(result.matched_by) || 0) + 1);
    } else {
      unresolved.push({ ...row, ...result });
    }
  }
  return { resolved, unresolved, tiers: Object.fromEntries(byTier) };
}
