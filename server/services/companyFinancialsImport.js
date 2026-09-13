/**
 * Reading a file of financial statements, strictly.
 *
 * The import exists so nothing has to parse an annual report. That only helps
 * if the import itself refuses to guess: a row missing its currency, its scale
 * or its period type is rejected rather than defaulted, because every one of
 * those defaults is a number that later reads as a fact nobody checked.
 *
 * A scale is the one to be hardest about. "Revenue 11,400" is eleven thousand
 * four hundred crore or eleven thousand four hundred rupees depending on a
 * field nobody looks at twice, and the two differ by ten million.
 */

const SCALES = new Map([
  ['1', 1], ['unit', 1], ['units', 1], ['absolute', 1],
  ['thousand', 1e3], ['thousands', 1e3], ['000', 1e3],
  ['lakh', 1e5], ['lakhs', 1e5],
  ['million', 1e6], ['millions', 1e6], ['mn', 1e6],
  ['crore', 1e7], ['crores', 1e7], ['cr', 1e7],
  ['billion', 1e9], ['billions', 1e9], ['bn', 1e9],
]);

export const LINE_ITEMS = [
  'revenue', 'cost_of_sales', 'gross_profit', 'operating_expense', 'ebitda', 'ebit',
  'depreciation', 'interest_expense', 'pre_tax_income', 'tax_expense', 'net_income',
  'share_based_comp', 'cash', 'receivables', 'inventories', 'payables', 'gross_debt',
  'total_equity', 'invested_capital', 'operating_cash_flow', 'capex', 'acquisitions',
  'dividends', 'buybacks', 'shares_issued', 'share_count',
];

/** A scale written as a word or a number, or null if it is neither. */
export function scaleOf(value) {
  if (value === null || value === undefined || value === '') return null;
  const text = String(value).trim().toLowerCase();
  if (SCALES.has(text)) return SCALES.get(text);
  const asNumber = Number(text.replace(/[, _]/g, ''));
  return Number.isFinite(asNumber) && asNumber > 0 ? asNumber : null;
}

/** A figure, or null. Blank means not reported, which is not the same as zero. */
function figureOf(value) {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (!text || text === '-' || text === '—' || text.toLowerCase() === 'na'
    || text.toLowerCase() === 'n/a') return null;
  // Accounting parentheses are a minus sign.
  const negative = /^\(.*\)$/.test(text);
  const cleaned = text.replace(/[()]/g, '').replace(/[, ]/g, '').replace(/^[₹$€£]/, '');
  const asNumber = Number(cleaned);
  if (!Number.isFinite(asNumber)) return null;
  return negative ? -asNumber : asNumber;
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * One row from a file, as a period ready to store, or the reasons it is not.
 *
 * Returns { row } or { errors }. Never both, and never a row with a field
 * quietly defaulted.
 */
export function readPeriod(input, { at = 0 } = {}) {
  const raw = input || {};
  const errors = [];
  const ticker = String(raw.ticker || '').trim().toUpperCase();
  if (!ticker) errors.push('ticker is missing');

  const periodEnd = String(raw.period_end || '').trim();
  if (!ISO_DATE.test(periodEnd)) {
    errors.push(`period_end must be YYYY-MM-DD, got "${raw.period_end ?? ''}"`);
  } else if (Number.isNaN(Date.parse(periodEnd))) {
    errors.push(`period_end "${periodEnd}" is not a date`);
  }

  const periodType = String(raw.period_type || '').trim().toLowerCase();
  if (!['annual', 'quarter'].includes(periodType)) {
    errors.push(`period_type must be annual or quarter, got "${raw.period_type ?? ''}"`);
  }

  const basis = String(raw.basis || 'consolidated').trim().toLowerCase();
  if (!['consolidated', 'standalone'].includes(basis)) {
    errors.push(`basis must be consolidated or standalone, got "${raw.basis}"`);
  }

  const currency = String(raw.currency || '').trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(currency)) {
    errors.push(`currency must be a three-letter code, got "${raw.currency ?? ''}"`);
  }

  // Never defaulted. A missing scale silently treated as 1 turns crore into
  // rupees and a leverage ratio into a rounding error.
  const scale = scaleOf(raw.scale);
  if (scale === null) errors.push(`scale is missing or unreadable ("${raw.scale ?? ''}")`);

  const figures = {};
  let reported = 0;
  for (const name of LINE_ITEMS) {
    const value = figureOf(raw[name]);
    figures[name] = value;
    if (value !== null) reported += 1;
  }
  if (!reported) errors.push('the row reports no line items at all');

  if (errors.length) return { errors: errors.map((why) => `row ${at + 1}: ${why}`) };
  return {
    row: {
      ticker,
      period_end: periodEnd,
      period_type: periodType,
      basis,
      currency,
      scale,
      restated: raw.restated === true || String(raw.restated).toLowerCase() === 'true',
      ...figures,
      source_file: raw.source_file ? String(raw.source_file) : null,
    },
  };
}

/**
 * A whole file. Every row is read before anything is reported, so a caller
 * sees all the problems at once rather than one per attempt.
 *
 * Duplicate periods are an error rather than a last-one-wins, because the file
 * cannot say which reading of a year was meant.
 */
export function readFinancials(rows) {
  const ok = [];
  const errors = [];
  const seen = new Map();
  (rows || []).forEach((raw, at) => {
    const read = readPeriod(raw, { at });
    if (read.errors) { errors.push(...read.errors); return; }
    const key = [read.row.ticker, read.row.period_end, read.row.period_type, read.row.basis].join('|');
    if (seen.has(key)) {
      errors.push(`row ${at + 1}: ${read.row.ticker} ${read.row.period_end} `
        + `${read.row.period_type} ${read.row.basis} also appears at row ${seen.get(key) + 1}`);
      return;
    }
    seen.set(key, at);
    ok.push(read.row);
  });
  return { rows: ok, errors };
}
