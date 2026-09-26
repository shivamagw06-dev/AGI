import { number } from './wealthPlanning.js';
// This release intentionally does not treat an AY 2026-27 source as TY 2026-27 law.
export const TAX_RULE = Object.freeze({ id: 'IN-FY2025-26-ordinary-v1', financialYear: '2025-26', assessmentYear: '2026-27',
  effectiveFrom: '2025-04-01', effectiveTo: '2026-03-31', checkedAt: '2026-09-24', professionalReview: 'pending',
  source: 'https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1',
  rebateReliefSource: 'https://sansad.in/getFile/loksabhaquestions/annex/187/AU1546_FJ8593.pdf?source=pqals',
  transitionSource: 'https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/objective-and-scope-new-act' });
function slabTax(income, regime, age) {
  const slabs = regime === 'new' ? [[400000, 0], [800000, .05], [1200000, .1], [1600000, .15], [2000000, .2], [2400000, .25], [Infinity, .3]]
    : [[age >= 80 ? 500000 : age >= 60 ? 300000 : 250000, 0], [500000, .05], [1000000, .2], [Infinity, .3]];
  let tax = 0, last = 0;
  for (const [ceiling, rate] of slabs) { tax += Math.max(0, Math.min(income, ceiling) - last) * rate; last = ceiling; }
  return tax;
}
function rate(income, regime) {
  return income > 50000000 && regime === 'old' ? .37 : income > 20000000 ? .25 : income > 10000000 ? .15 : income > 5000000 ? .1 : 0;
}
export function estimateOrdinaryTax(input) {
  const unsupported = [];
  if (input.year !== TAX_RULE.financialYear) unsupported.push('This tax year has no verified rule package in this release.');
  if (input.entity !== 'individual' || input.residency !== 'resident') unsupported.push('Only resident individuals are supported.');
  if (input.special !== 'none') unsupported.push('Capital gains, dividends, foreign income, losses or other special treatment require a separate calculation.');
  if (!['old', 'new'].includes(input.regime)) unsupported.push('Select a supported tax regime.');
  if (unsupported.length) return { status: 'review_required', reasons: unsupported, total: null, rule: TAX_RULE };
  const age = number(input.age, 'Age at year end', 18, 120);
  const taxable = Math.round(number(input.taxable, 'CA-computed taxable ordinary income') / 10) * 10;
  const credits = number(input.credits, 'Confirmed TDS and advance tax');
  const base = slabTax(taxable, input.regime, age);
  const rebateLimit = input.regime === 'new' ? 1200000 : 500000;
  const rebate = taxable <= rebateLimit ? Math.min(base, input.regime === 'new' ? 60000 : 12500) : 0;
  const rebateRelief = input.regime === 'new' && taxable > rebateLimit ? Math.max(0, base - (taxable - rebateLimit)) : 0;
  const afterRebate = base - rebate - rebateRelief;
  const surchargeRate = rate(taxable, input.regime), surcharge = afterRebate * surchargeRate;
  const thresholds = input.regime === 'new' ? [5000000, 10000000, 20000000] : [5000000, 10000000, 20000000, 50000000];
  const threshold = thresholds.filter(x => taxable > x).at(-1);
  const atThreshold = threshold == null ? 0 : slabTax(threshold, input.regime, age) * (1 + rate(threshold, input.regime));
  const marginalRelief = threshold == null ? 0 : Math.max(0, afterRebate + surcharge - atThreshold - (taxable - threshold));
  const beforeCess = afterRebate + surcharge - marginalRelief, cess = beforeCess * .04;
  const total = Math.round((beforeCess + cess) / 10) * 10;
  return { status: 'estimate_pending_review', taxable, base, rebate, rebateRelief, surcharge, marginalRelief, cess, total,
    credits, balance: total - credits, effectiveRate: taxable ? total / taxable * 100 : 0, rule: TAX_RULE,
    reasons: ['Ordinary taxable income only; deductions and income-head computations must already be verified. No filing or regime-switch eligibility determination. Professional review pending.'] };
}
