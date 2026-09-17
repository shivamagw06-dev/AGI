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
