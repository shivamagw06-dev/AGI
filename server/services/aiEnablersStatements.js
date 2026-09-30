/**
 * Upstox statements, and the basis question they answer.
 *
 * The size derivation rests on one assumption: that the P/B from key-ratios
 * and the book equity from the balance sheet describe the same entity. Upstox
 * does not state the basis of its ratios, so until now that assumption was
 * recorded and carried rather than tested.
 *
 * The income statement settles it. P/E is price over earnings per share, and
 * `full_statement` carries EPS - Basic on whichever basis was requested. So
 * price divided by the consolidated EPS, and price divided by the standalone
 * EPS, can each be compared against the stated P/E: whichever matches is the
 * basis the ratios are on. That is a measurement, not an assumption, and it
 * is what lets the balance sheet be read on the matching basis rather than on
 * a hopeful one.
 */

const numeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(String(value).replace(/[%,\s+]/g, ''));
  return Number.isFinite(parsed) ? parsed : null;
};

/** The first payload that actually carries values, with its basis. */
export function statementFrom(payloads, { rowsAt }) {
  for (const [basis, payload] of payloads) {
    const body = payload?.data;
    const rows = rowsAt(body);
    if (!Array.isArray(rows) || !rows.length) continue;
    const carrying = rows.filter((one) => (Array.isArray(one?.history) ? one.history.length : 0) > 0);
    if (!carrying.length) continue;
    const units = String(body?.units_in || '').trim().toLowerCase();
    if (units && units !== 'crore') return { rows: null, basis, units, reason: 'UNEXPECTED_UNITS' };
    return { rows: carrying, basis, units: units || 'crore', full: body?.full_statement || [], reason: null };
  }
  return { rows: null, basis: null, units: null, full: [], reason: 'NO_STATEMENT_ON_ANY_BASIS' };
}

/** One income-statement category's history, newest first. */
export function categoryHistory(rows, category) {
  const row = (rows || []).find((one) => String(one?.category || '').trim().toLowerCase() === category);
  const history = Array.isArray(row?.history) ? row.history : [];
  return history
    .map((one) => ({ value: numeric(one?.value), period: one?.period ?? null }))
    .filter((one) => one.value !== null);
}

/** A named line from `full_statement`, newest-first by the order served. */
export function lineHistory(full, particular) {
  const row = (full || []).find((one) => String(one?.particular || '').trim().toLowerCase() === particular.toLowerCase());
  const history = Array.isArray(row?.history) ? row.history : [];
  return history
    .map((one) => ({ value: numeric(one?.value), period: one?.period ?? null }))
    .filter((one) => one.value !== null);
}

/**
 * Which basis the key-ratios P/E is quoted on.
 *
 * P/E is price over EPS, so dividing the live price by each basis's EPS and
 * comparing against the stated P/E identifies the basis by measurement. A
 * company reporting only one basis resolves trivially; one reporting both
 * resolves to whichever matches, and to neither when they both miss - which
 * is itself worth knowing, because it means the ratio is computed on
 * something this code does not have.
 */
export function resolveRatioBasis({ statedPe, price, epsByBasis, tolerance = 0.05 }) {
  const pe = numeric(statedPe);
  const last = numeric(price);
  if (pe === null || pe <= 0 || last === null || last <= 0) {
    return { basis: null, reason: 'NO_PE_OR_PRICE', candidates: [] };
  }
  const candidates = Object.entries(epsByBasis || {})
    .map(([basis, eps]) => {
      const value = numeric(eps);
      if (value === null || value <= 0) return { basis, eps: value, impliedPe: null, gap: null };
      const impliedPe = last / value;
      return { basis, eps: value, impliedPe, gap: Math.abs(impliedPe / pe - 1) };
    });
  const matches = candidates
    .filter((one) => one.gap !== null && one.gap <= tolerance)
    .sort((a, b) => a.gap - b.gap);
  if (!matches.length) {
    return {
      basis: null, candidates, statedPe: pe,
      reason: 'PE_MATCHES_NO_AVAILABLE_BASIS',
    };
  }
  return { basis: matches[0].basis, candidates, statedPe: pe, reason: null };
}

/**
 * Compound annual growth between the oldest and newest value in a history.
 *
 * Refuses rather than annualising a shorter span: three years of growth needs
 * four annual points, and computing it from two would overstate it badly.
 */
export function cagr(history, { years = 3 } = {}) {
  const points = (history || []).filter((one) => Number.isFinite(one?.value));
  if (points.length < years + 1) return { value: null, reason: 'INSUFFICIENT_PERIODS', have: points.length, need: years + 1 };
  const latest = points[0];
  const base = points[years];
  if (!(base.value > 0)) return { value: null, reason: 'NON_POSITIVE_BASE', have: points.length };
  return {
    value: (latest.value / base.value) ** (1 / years) - 1,
    from: base.period, to: latest.period, reason: null,
  };
}

/* ── cash flow ──────────────────────────────────────────────────────── */

/**
 * What the cash-flow statement does and does not carry.
 *
 * Operating cash flow is served, both as a category and as a line. Capital
 * expenditure is not, on either. The categories are operating, investing and
 * financing, and the line items run from profit before tax to cash at the end
 * of the year with nothing for purchases of property, plant or equipment.
 *
 * Investing cash flow is not a substitute. It nets acquisitions, purchases
 * and sales of investments and proceeds from asset disposals against capital
 * spending, and for a holding company it is mostly stake buying. Reading it
 * as capex would be most wrong for exactly the companies where capex matters
 * most to this screen.
 */
export const CAPEX_AVAILABLE_FROM_CASH_FLOW = false;

export function operatingCashFlow(picked) {
  const fromCategory = categoryHistory(picked?.rows, 'operating');
  if (fromCategory.length) return { history: fromCategory, from: 'category', reason: null };
  const fromLine = lineHistory(picked?.full, 'Cash flow from Operations');
  if (fromLine.length) return { history: fromLine, from: 'full_statement', reason: null };
  return { history: [], from: null, reason: 'NO_OPERATING_CASH_FLOW' };
}

/**
 * Capex, which this source does not have.
 *
 * Returned as a refusal rather than omitted, so a caller asking for it gets
 * the reason instead of an empty array it might read as zero spending.
 */
export function capexFrom() {
  return {
    history: [], value: null,
    reason: 'CAPEX_NOT_IN_CASH_FLOW_STATEMENT',
    detail: 'Upstox cash-flow serves operating, investing and financing only. Investing nets '
      + 'acquisitions and disposals against capital spending and is not a capex proxy.',
  };
}

/* ── corporate actions ──────────────────────────────────────────────── */

const MONTHS = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };

/** "14 Aug 2025" to a UTC date, or null. */
export function parseActionDate(value) {
  const match = /^(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})$/.exec(String(value || '').trim());
  if (!match) return null;
  const month = MONTHS[match[2].toLowerCase()];
  if (month === undefined) return null;
  return Date.UTC(Number(match[3]), month, Number(match[1]));
}

/** Actions that change the share count, and so the price, on their ex-date. */
const DILUTIVE = /^(bonus|split|rights)/i;

/**
 * Corporate actions that would make a price move look like a return.
 *
 * A one-for-one bonus halves the quoted price overnight. If the previous
 * close a feed reports is not adjusted for it, the basket reads a 50% loss
 * that did not happen - and nothing downstream catches it, because the
 * residual check compares contributions against the index return and a wrong
 * member return flows consistently into both.
 *
 * So the ex-dates are read ahead and the member is flagged. A flag is not a
 * correction: it says this member's return cannot be trusted today, which is
 * the honest state when the adjustment cannot be verified.
 */
export function actionsNear(payload, { now = Date.now(), windowDays = 1 } = {}) {
  const rows = Array.isArray(payload?.data) ? payload.data : [];
  const window = windowDays * 86_400_000;
  const today = Math.floor(now / 86_400_000) * 86_400_000;
  const near = [];
  for (const row of rows) {
    const name = String(row?.name || '').trim();
    const exDate = parseActionDate(row?.expiry_date);
    if (exDate === null) continue;
    if (Math.abs(exDate - today) > window) continue;
    near.push({
      name,
      exDate: new Date(exDate).toISOString().slice(0, 10),
      ratio: row?.ratio ?? null,
      amount: row?.amount ?? null,
      // A dividend moves the price by the dividend, which is a real return to
      // a holder and needs no flag. A bonus, split or rights issue changes
      // the share count and does not.
      dilutive: DILUTIVE.test(name),
    });
  }
  return {
    actions: near,
    priceBreak: near.some((one) => one.dilutive),
    reason: near.some((one) => one.dilutive) ? 'DILUTIVE_ACTION_ON_OR_NEAR_EX_DATE' : null,
  };
}
