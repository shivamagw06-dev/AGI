/**
 * One internal shape for holdings, whatever broker they came from.
 *
 * ISIN is the primary identifier and the symbol is not. A ticker is a display
 * label that brokers spell differently, exchanges reuse, and companies change:
 * the same ISIN trades as RELIANCE on NSE and 500325 on BSE, and a symbol that
 * means one company today can mean another after a rename. Keying on a symbol
 * is how one client's position becomes another's.
 *
 * Nothing here calls a broker. Adapters fetch and hand raw payloads to
 * `normaliseHolding`, so the mapping can be tested without credentials -- which
 * matters, because credentials are the thing we do not yet have.
 */

export const ASSET_TYPES = Object.freeze([
  'EQUITY', 'ETF', 'MUTUAL_FUND', 'BOND', 'REIT', 'INVIT', 'CASH', 'OTHER',
]);

const ISIN_RE = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;

/** Capital IQ and some brokers prefix an ISIN; strip before validating. */
export function cleanIsin(value) {
  const text = String(value ?? '').trim().toUpperCase().replace(/^I_/, '');
  return ISIN_RE.test(text) ? text : null;
}

function num(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(String(value).replace(/,/g, '').trim());
  return Number.isFinite(parsed) ? parsed : null;
}

function text(value) {
  const out = String(value ?? '').trim();
  return out || null;
}

/**
 * Broker field names for the same idea. Kept as data rather than as a switch
 * so adding a broker is a table entry, and so the differences are visible in
 * one place instead of spread across five adapters.
 */
export const BROKER_FIELDS = Object.freeze({
  UPSTOX: {
    isin: ['isin'],
    symbol: ['trading_symbol', 'tradingsymbol'],
    name: ['company_name'],
    exchange: ['exchange'],
    quantity: ['quantity'],
    averageCost: ['average_price'],
    assetType: ['instrument_type'],
  },
  ZERODHA: {
    isin: ['isin'],
    symbol: ['tradingsymbol'],
    name: ['tradingsymbol'],
    exchange: ['exchange'],
    quantity: ['quantity', 'opening_quantity'],
    averageCost: ['average_price'],
    assetType: ['product'],
  },
  ANGELONE: {
    isin: ['isin'],
    symbol: ['tradingsymbol'],
    name: ['tradingsymbol'],
    exchange: ['exchange'],
    quantity: ['quantity'],
    averageCost: ['averageprice'],
    assetType: ['producttype'],
  },
});

function pick(row, keys) {
  for (const key of keys || []) {
    if (row?.[key] !== undefined && row[key] !== null && row[key] !== '') return row[key];
  }
  return null;
}

/** Broker instrument labels are not our asset types; map explicitly. */
export function assetTypeOf(raw, { exchange, schemeCode } = {}) {
  const value = String(raw ?? '').trim().toUpperCase();
  if (schemeCode) return 'MUTUAL_FUND';
  if (['MF', 'MUTUALFUND', 'MUTUAL_FUND'].includes(value)) return 'MUTUAL_FUND';
  if (['ETF'].includes(value)) return 'ETF';
  if (['BOND', 'DEBT', 'NCD', 'SGB'].includes(value)) return 'BOND';
  if (['REIT'].includes(value)) return 'REIT';
  if (['INVIT'].includes(value)) return 'INVIT';
  if (String(exchange ?? '').toUpperCase() === 'MF') return 'MUTUAL_FUND';
  // CNC, DELIVERY, EQ and friends all describe a product, not an asset class.
  return 'EQUITY';
}

/**
 * @returns {{ok: true, holding: object} | {ok: false, reason: string, raw: object}}
 *
 * Returns a reason instead of throwing, and never guesses. A row we cannot
 * identify is surfaced to the client as unmatched rather than dropped -- a
 * silently missing position is worse than a visible gap, because the portfolio
 * still adds up and nobody notices it is short a holding.
 */
export function normaliseHolding(raw, { broker, asOf, connectionId } = {}) {
  const map = BROKER_FIELDS[broker];
  if (!map) return { ok: false, reason: `unsupported_broker:${broker}`, raw };

  const isin = cleanIsin(pick(raw, map.isin));
  const schemeCode = text(pick(raw, ['scheme_code', 'schemeCode', 'folio_number']));
  if (!isin && !schemeCode) return { ok: false, reason: 'no_isin_or_scheme_code', raw };

  const quantity = num(pick(raw, map.quantity));
  if (quantity === null) return { ok: false, reason: 'no_quantity', raw };

  const exchange = text(pick(raw, map.exchange));
  return {
    ok: true,
    holding: {
      assetType: assetTypeOf(pick(raw, map.assetType), { exchange, schemeCode }),
      isin,
      schemeCode,
      symbol: text(pick(raw, map.symbol)),
      exchange,
      name: text(pick(raw, map.name)) || text(pick(raw, map.symbol)),
      quantity,
      // Absent rather than zero. A zero average cost reads as a free holding
      // and produces an infinite return.
      averageCost: num(pick(raw, map.averageCost)),
      currency: 'INR',
      source: broker,
      connectionId: connectionId ?? null,
      asOf: asOf ?? new Date().toISOString(),
    },
  };
}

/** Normalise a payload, keeping rejects so the client can be shown them. */
export function normaliseHoldings(rows, context) {
  const holdings = [];
  const unmatched = [];
  for (const raw of rows || []) {
    const result = normaliseHolding(raw, context);
    if (result.ok) holdings.push(result.holding);
    else unmatched.push({ reason: result.reason, raw: result.raw });
  }
  return { holdings, unmatched, total: (rows || []).length };
}
