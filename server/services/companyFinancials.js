/**
 * The figures an underwriter derives from statements, and the refusals.
 *
 * Pure arithmetic over periods that were imported, never parsed. Every
 * function here returns either a number with the inputs it used, or null with
 * the reason it could not be computed - because a ratio built on a missing
 * denominator, a mismatched period or an assumed scale is worse than a blank
 * cell. A blank prompts a question; a wrong number ends one.
 *
 * Four refusals are enforced everywhere rather than remembered:
 *
 *   a missing input          - no figure, and the name of what was missing
 *   a zero denominator       - no ratio, rather than an infinity
 *   mismatched period types  - a quarter against a year is not growth
 *   mismatched scale or currency - crore against millions is a thousand-fold
 *                              error that looks exactly like a good year
 */

/** A computed figure with what produced it. */
const figure = (value, formula, inputs) => ({ value, formula, inputs, reason: null });

/** No figure, and why. */
const refused = (reason) => ({ value: null, formula: null, inputs: null, reason });

const has = (period, name) => period
  && period[name] !== null && period[name] !== undefined && Number.isFinite(Number(period[name]));

/** Every named input this period is missing. */
function missing(period, names) {
  return names.filter((name) => !has(period, name));
}

/**
 * Whether two periods may be compared at all.
 *
 * Returns null when they may, or the reason when they may not.
 */
export function comparable(a, b) {
  if (!a || !b) return 'one of the periods is missing';
  if (a.period_type !== b.period_type) {
    return `a ${b.period_type} cannot be compared against a ${a.period_type}`;
  }
  if (a.basis !== b.basis) {
    return `${b.basis} cannot be compared against ${a.basis}`;
  }
  if (a.currency !== b.currency) {
    return `${b.currency} cannot be compared against ${a.currency}`;
  }
  if (Number(a.scale) !== Number(b.scale)) {
    return `the periods are reported in different scales (${b.scale} and ${a.scale})`;
  }
  return null;
}

/** A ratio of two line items in one period. */
export function ratio(period, top, bottom, { as = null } = {}) {
  const absent = missing(period, [top, bottom]);
  if (absent.length) return refused(`${absent.join(' and ')} not reported`);
  const denominator = Number(period[bottom]);
  if (denominator === 0) return refused(`${bottom} is zero`);
  const value = Number(period[top]) / denominator;
  return figure(value, as || `${top} / ${bottom}`, { [top]: Number(period[top]), [bottom]: denominator });
}

/** Growth in one line item between two periods. */
export function growth(now, before, name) {
  const why = comparable(now, before);
  if (why) return refused(why);
  const absent = [...missing(now, [name]), ...missing(before, [name])];
  if (absent.length) return refused(`${name} not reported in both periods`);
  const was = Number(before[name]);
  if (was === 0) return refused(`${name} was zero in the earlier period`);
  const value = Number(now[name]) / was - 1;
  return figure(value, `${name} / prior ${name} - 1`, { now: Number(now[name]), before: was });
}

/**
 * Compound annual growth between two periods.
 *
 * The exponent is the number of years between the period ends, taken from the
 * dates rather than from how many rows sit between them: a company that
 * changed its financial year has periods that are not one year apart, and
 * counting rows would report a fifteen-month year as a year.
 */
export function cagr(now, before, name) {
  const why = comparable(now, before);
  if (why) return refused(why);
  const absent = [...missing(now, [name]), ...missing(before, [name])];
  if (absent.length) return refused(`${name} not reported in both periods`);
  const years = (new Date(now.period_end) - new Date(before.period_end)) / (365.2425 * 24 * 3600 * 1000);
  if (!(years > 0)) return refused('the periods are not in order');
  if (years < 0.9) return refused('the periods are less than a year apart');
  const was = Number(before[name]);
  const isNow = Number(now[name]);
  if (was <= 0) return refused(`${name} was not positive in the earlier period`);
  if (isNow <= 0) return refused(`${name} is not positive in the later period`);
  const value = (isNow / was) ** (1 / years) - 1;
  return figure(value, `(${name} / prior ${name}) ^ (1 / ${years.toFixed(2)} years) - 1`,
    { now: isNow, before: was, years: Number(years.toFixed(2)) });
}

/** Free cash flow: what the business generated after keeping itself running. */
export function freeCashFlow(period) {
  const absent = missing(period, ['operating_cash_flow', 'capex']);
  if (absent.length) return refused(`${absent.join(' and ')} not reported`);
  // Capex is stored as reported. A cash-flow statement shows it as an outflow,
  // so the sign is taken from the magnitude rather than trusted: a file that
  // records it positive and one that records it negative must not produce free
  // cash flows that differ by twice the capex.
  const capex = Math.abs(Number(period.capex));
  const value = Number(period.operating_cash_flow) - capex;
  return figure(value, 'operating_cash_flow - |capex|',
    { operating_cash_flow: Number(period.operating_cash_flow), capex });
}

/** Net debt, and the leverage an underwriter reads first. */
export function netDebt(period) {
  const absent = missing(period, ['gross_debt', 'cash']);
  if (absent.length) return refused(`${absent.join(' and ')} not reported`);
  const value = Number(period.gross_debt) - Number(period.cash);
  return figure(value, 'gross_debt - cash',
    { gross_debt: Number(period.gross_debt), cash: Number(period.cash) });
}

export function netDebtToEbitda(period) {
  const debt = netDebt(period);
  if (debt.reason) return debt;
  if (!has(period, 'ebitda')) return refused('ebitda not reported');
  const ebitda = Number(period.ebitda);
  if (ebitda === 0) return refused('ebitda is zero');
  if (ebitda < 0) return refused('ebitda is negative, so leverage is not a multiple');
  return figure(debt.value / ebitda, '(gross_debt - cash) / ebitda',
    { net_debt: debt.value, ebitda });
}

export function interestCover(period) {
  const absent = missing(period, ['ebit', 'interest_expense']);
  if (absent.length) return refused(`${absent.join(' and ')} not reported`);
  const interest = Math.abs(Number(period.interest_expense));
  if (interest === 0) return refused('interest expense is zero');
  return figure(Number(period.ebit) / interest, 'ebit / |interest_expense|',
    { ebit: Number(period.ebit), interest_expense: interest });
}

/**
 * Whether a balance-sheet item is outgrowing sales.
 *
 * The question an underwriter asks of receivables and inventories, and the one
 * that turns a good year into a cash-conversion problem.
 */
export function outgrowingSales(now, before, name) {
  const item = growth(now, before, name);
  if (item.reason) return refused(item.reason);
  const sales = growth(now, before, 'revenue');
  if (sales.reason) return refused(sales.reason);
  return {
    value: item.value - sales.value,
    formula: `${name} growth - revenue growth`,
    inputs: { [`${name}_growth`]: item.value, revenue_growth: sales.value },
    reason: null,
  };
}

/** Cash conversion, the figure the worked example turns on. */
export function cashConversion(period) {
  const fcf = freeCashFlow(period);
  if (fcf.reason) return fcf;
  if (!has(period, 'ebitda')) return refused('ebitda not reported');
  const ebitda = Number(period.ebitda);
  if (ebitda <= 0) return refused('ebitda is not positive');
  return figure(fcf.value / ebitda, '(operating_cash_flow - |capex|) / ebitda',
    { free_cash_flow: fcf.value, ebitda });
}

/**
 * Share count in actual shares, whatever unit the filing used.
 *
 * The only place a stored figure is converted rather than read back as
 * reported, because a count compared across periods must be in one unit and
 * "shares in millions" one year against actual shares the next is a
 * million-fold error that looks like a buyback.
 */
export function sharesOf(period) {
  if (!has(period, 'share_count')) return refused('share_count not reported');
  const scale = Number(period.share_scale);
  if (!Number.isFinite(scale) || scale <= 0) return refused('share_scale not reported');
  return figure(Number(period.share_count) * scale, 'share_count * share_scale',
    { share_count: Number(period.share_count), share_scale: scale });
}

/**
 * Whether the share count rose or fell - questions 76 and 77.
 *
 * Compared in actual shares, so a filing that changes how it reports the count
 * cannot produce a change that never happened.
 */
export function shareCountChange(now, before) {
  const why = comparable(now, before);
  if (why) return refused(why);
  const a = sharesOf(now);
  if (a.reason) return refused(`later period: ${a.reason}`);
  const b = sharesOf(before);
  if (b.reason) return refused(`earlier period: ${b.reason}`);
  if (b.value === 0) return refused('the earlier share count is zero');
  return figure(a.value / b.value - 1, 'shares now / shares before - 1',
    { now: a.value, before: b.value });
}
