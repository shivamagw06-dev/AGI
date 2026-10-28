/**
 * The underwriting questions that are arithmetic, answered from stored
 * statements.
 *
 * The register says fifty-one questions are computed. Twenty-two of them come
 * out of the scalar line items `company_financials` holds; the rest need
 * shapes it does not store yet - segment revenue and EBIT, a debt maturity
 * schedule, a price and volume bridge - and are reported as still needing
 * them rather than approximated from what is nearby.
 *
 * Every answer carries the formula and the inputs that produced it, or the
 * reason it could not be produced. Nothing here estimates: a company that does
 * not report EBITDA has no leverage multiple, and saying so is the answer.
 */
import {
  ratio, growth, cagr, freeCashFlow, netDebt, netDebtToEbitda,
  interestCover, outgrowingSales, cashConversion, shareCountChange,
} from './companyFinancials.js';

const refused = (reason) => ({ value: null, formula: null, inputs: null, reason });

/** A line item as reported, or the reason it is not there. */
function reported(period, name) {
  const value = period?.[name];
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return refused(`${name} not reported`);
  }
  return { value: Number(value), formula: name, inputs: { [name]: Number(value) }, reason: null };
}

/**
 * Answers for one company, newest period first.
 *
 * `periods` are rows from company_financials. Annual only: a quarter mixed
 * into a series produces growth against three months, which the comparison
 * rules refuse individually but which has no business being assembled here.
 */
export function computedAnswers(periods = []) {
  const annual = [...periods]
    .filter((row) => row?.period_type === 'annual')
    .sort((a, b) => String(b.period_end).localeCompare(String(a.period_end)));
  const answers = new Map();
  if (!annual.length) return answers;

  const [now, before] = annual;
  const threeBack = annual[3] || null;
  const fiveBack = annual[5] || null;
  const put = (n, result) => answers.set(n, result);
  const needsPrior = refused('only one period is stored, so nothing can be compared');

  put(11, before ? growth(now, before, 'revenue') : needsPrior);
  put(12, threeBack ? cagr(now, threeBack, 'revenue')
    : refused('four annual periods are needed for a three-year rate'));
  put(19, refused('needs this year’s growth against last year’s, so three periods'));
  put(21, ratio(now, 'gross_profit', 'revenue', { as: 'gross_profit / revenue' }));
  put(22, before ? growth(now, before, 'gross_profit') : needsPrior);
  put(23, ratio(now, 'ebitda', 'revenue'));
  put(24, ratio(now, 'ebit', 'revenue'));
  put(25, ratio(now, 'net_income', 'revenue'));
  put(31, reported(now, 'ebitda'));
  put(41, reported(now, 'operating_cash_flow'));
  put(42, freeCashFlow(now));
  put(43, cashConversion(now));
  put(44, ratio(now, 'operating_cash_flow', 'net_income'));
  put(47, before ? outgrowingSales(now, before, 'receivables') : needsPrior);
  put(48, before ? outgrowingSales(now, before, 'inventories') : needsPrior);
  put(49, ratio(now, 'payables', 'cost_of_sales', { as: 'payables / cost_of_sales' }));
  put(53, ratio(now, 'capex', 'revenue'));
  put(59, ratio(now, 'depreciation', 'capex', { as: 'depreciation / capex' }));
  put(61, reported(now, 'gross_debt'));
  put(62, reported(now, 'cash'));
  put(63, netDebt(now));
  put(64, netDebtToEbitda(now));
  put(65, interestCover(now));
  put(72, reported(now, 'capex'));
  put(73, reported(now, 'acquisitions'));
  put(74, reported(now, 'dividends'));
  put(75, reported(now, 'buybacks'));
  put(77, before ? shareCountChange(now, before) : needsPrior);
  put(79, ratio(now, 'ebit', 'invested_capital', { as: 'ebit / invested_capital (pre-tax)' }));

  // Noted rather than silently absent: a five-year rate is the one an
  // underwriter asks for and six annual periods is a lot to have loaded.
  if (fiveBack) put(12, cagr(now, fiveBack, 'revenue'));
  return answers;
}

/** The periods a company has, described for a reader. */
export function periodsRead(periods = []) {
  const annual = [...periods].filter((row) => row?.period_type === 'annual');
  if (!annual.length) return null;
  const ends = annual.map((row) => row.period_end).sort();
  const [first] = ends;
  const last = ends[ends.length - 1];
  const currencies = [...new Set(annual.map((row) => `${row.currency} x${row.scale}`))];
  return { periods: annual.length, from: first, to: last, units: currencies };
}
