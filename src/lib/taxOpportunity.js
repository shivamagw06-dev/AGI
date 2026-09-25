import { estimateOrdinaryTax } from './wealthTax.js';

export const TAX_SOURCES = Object.freeze({
  year: 'https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/objective-and-scope-new-act',
  regime: 'https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1',
  salary: 'https://www.incometaxindia.gov.in/en/income-from-salary',
  interest: 'https://www.incometaxindia.gov.in/w/deductions',
  property: 'https://www.incometaxindia.gov.in/hi/w/income-from-house-property',
  gains: 'https://www.incometaxindia.gov.in/w/capital-gain',
  ais: 'https://www.incometax.gov.in/iec/foportal/ais-faq',
  business: 'https://www.incometaxindia.gov.in/w/section-37-36',
  gst: 'https://cbic-gst.gov.in/pdf/Circular-55thGSTC-Services.pdf',
  clubbing: 'https://www.incometaxindia.gov.in/w/section-64-34',
});
export const BLANK_TAX_CASE = Object.freeze({ year:'2026-27', age:'', salary:'', depositInterest:'', savingsInterest:'',
  eligible80c:'', eligible80d:'', eligibleNps:'', hasRental:false, hasGains:false, hasBusiness:false, hasForeign:false,
  otherIncome:false, recordsConfirmed:false, claimsConfirmed:false });
const CARD = (id, title, detail, evidence, source, status = 'review') => ({id,title,detail,evidence,source,status});
function optionalAmount(value, name) {
  if (value == null || value === '') return null;
  if (!/^\d+(?:\.\d{1,2})?$/.test(String(value).trim()) || Number(value) > 1e12) throw new Error(`${name}: enter a non-negative rupee amount (up to two decimals).`);
  return Number(value);
}
export function scanTaxOpportunities(input) {
  if (!input || !['2025-26','2026-27'].includes(input.year)) throw new Error('Choose a supported income year.');
  if (input.age !== '' && (!/^\d+$/.test(String(input.age)) || Number(input.age) < 18 || Number(input.age) > 120)) throw new Error('Enter age at the end of the income year (18–120).');
  const age = input.age === '' ? null : Number(input.age);
  const amounts = Object.fromEntries(['salary','depositInterest','savingsInterest','eligible80c','eligible80d','eligibleNps'].map(key=>[key,optionalAmount(input[key],key)]));
  const year = input.year, old = year === '2025-26';
  const cards = [];
  const add = (...args) => cards.push(CARD(...args));
  add('ais','Reconcile income and TDS','Match salary and bank interest with AIS, Form 26AS, Form 16 and bank certificates. The same receipt shown twice is one receipt; TDS is a credit, not a tax exemption.','AIS/26AS and salary/interest certificates',TAX_SOURCES.ais,'action');
  if (amounts.salary != null && amounts.salary > 0) add('regime','Compare old and new regimes',old ? 'Old regime can allow eligible deductions; the new regime has different slabs and salary standard deduction. Compare whole-year liability before selecting.' : 'Current Tax Year 2026–27 uses the 2025 Act. Do not apply AY 2026–27 calculations to current-year income.','Form 16, pay slips, employer contribution and deductions',TAX_SOURCES.regime,'action');
  if (amounts.depositInterest != null || amounts.savingsInterest != null) {
    add('interest',age >= 60 ? 'Check resident senior deposit deduction' : 'Check savings-interest deduction',age >= 60 ? 'For FY 2025–26 old regime, section 80TTB may cover up to ₹50,000 of eligible deposit interest for a resident senior citizen. FD interest above the eligible amount remains income.' : 'For FY 2025–26 old regime, section 80TTA may cover up to ₹10,000 of savings-account interest. FD interest does not qualify for 80TTA.','Bank interest certificates, age and residency',TAX_SOURCES.interest,'action');
  }
  if (old) add('80c','Audit existing 80C payments',`The combined FY 2025–26 old-regime ceiling is ₹1,50,000. Enter only eligible payments actually made in that year; recorded eligible amount: ₹${Math.min(amounts.eligible80c,150000).toLocaleString('en-IN')}. Buying something now cannot create a 2025–26 payment.`,'EPF/PPF/ELSS/tuition/home-loan principal certificates as applicable',TAX_SOURCES.regime,'action');
  if (old) add('80d','Review qualifying health cover','Old-regime self/family premium limits depend on who is insured and their age; verify payment method, premium and policy before claiming. Parent cover has a separate limit.','Policy, receipt, insured persons and payment method',TAX_SOURCES.regime,'review');
  if (old) add('nps','Review additional personal NPS contribution','Section 80CCD(1B) can allow up to ₹50,000 in FY 2025–26 old regime for an eligible personal NPS contribution not also claimed under 80CCD(1).','PRAN and contribution statement',TAX_SOURCES.regime,'action');
  if (!old) add('current-year-deductions','Check current-year rule eligibility','Tax Year 2026–27 is governed by the 2025 Act. Record existing contributions, employer NPS, health premiums and the old-regime election history, then verify current-year sections and limits before estimating savings.','Payment evidence, employer statement and current-year rule pack',TAX_SOURCES.year,'review');
  if (input.hasRental) add('rental','Calculate rent property by property','Check legal ownership, reasonable annual value, municipal tax actually paid, the 30% standard deduction on net annual value and qualifying loan interest. Composite hotel services or inseparable asset letting may require a different income head.','Title/share, leases, rent ledger, municipal receipts and loan certificate',TAX_SOURCES.property,'review');
  if (input.hasGains) add('gains','Examine realised capital gains and eligible relief','Reconstruct lots and costs, including inherited-asset previous-owner records. Sections 54/54F/54EC have asset, time, investment and lock-in conditions; buying any property does not automatically exempt gains.','Broker statements, sale and acquisition deeds, previous-owner cost and investment proof',TAX_SOURCES.gains,'review');
  if (input.hasBusiness) add('business','Compare actual business records and permitted methods','Review documented business-only costs, depreciation, GST and presumptive eligibility. Presumptive business income does not permit an additional deduction for the same business expenses.','Books, invoices, asset register, GST returns and turnover by payment mode',TAX_SOURCES.business,'review');
  if (input.hasRental || input.hasBusiness) add('gst','Review GST by supply and registration','Income-tax treatment and GST are separate questions. Classify hotel accommodation and each commercial or residential lease, supplier/recipient status, invoices and input credits before applying a rate.','GST registration, contracts, invoices, return and ITC ledger',TAX_SOURCES.gst,'review');
  if (input.hasForeign) add('foreign','Check residency and foreign reporting','Foreign income, overseas assets and treaty relief require a separately verified case. Do not assume a change of address makes Indian-source income tax-free.','Travel-day evidence, broker/bank statements and residency documents',TAX_SOURCES.year,'review');
  if (input.otherIncome) add('other','Classify other income before comparing regimes','Dividends, special-rate income, losses, gifts and employer benefits can change liability.','Source documents and prior return',TAX_SOURCES.regime,'review');
  add('ownership','Verify taxpayer ownership','Assign each receipt to the legal/beneficial owner. Transfers to a spouse or minor and some family arrangements can trigger clubbing rules. Do not split income merely to access lower slabs.','Ownership deeds, inheritance and funding trail',TAX_SOURCES.clubbing,'review');
  const sorted = cards.sort((a,b) => (a.status === 'action' ? 0 : 1)-(b.status === 'action' ? 0 : 1));
  const missing = [];
  if (age == null) missing.push('Age at year end');
  if (amounts.salary == null && amounts.depositInterest == null && amounts.savingsInterest == null) missing.push('A supported income amount');
  if (amounts.salary == null) missing.push('Salary/pension amount, enter 0 if none');
  if (amounts.depositInterest == null) missing.push('FD/deposit interest, enter 0 if none');
  if (amounts.savingsInterest == null) missing.push('Savings-account interest, enter 0 if none');
  if (old) for (const [key,label] of [['eligible80c','80C/80CCC/80CCD(1)'],['eligibleNps','Personal NPS'],['eligible80d','Health premium']]) if (amounts[key] == null) missing.push(`${label} amount, enter 0 if none`);
  if (old && !input.claimsConfirmed) missing.push('Eligibility and same-year payment of deductions');
  if (old && (amounts.eligible80d || 0) > 0) missing.push('80D premium eligibility details (excluded from this numerical comparison)');
  if (!input.recordsConfirmed) missing.push('Income records reconciled with AIS/26AS');
  const complex = input.hasRental || input.hasGains || input.hasBusiness || input.hasForeign || input.otherIncome;
  const taxableEligible = old && missing.length === 0 && !complex;
  let comparison = null;
  if (taxableEligible) {
    const gross = amounts.salary + amounts.depositInterest + amounts.savingsInterest;
    const oldDed = Math.min(amounts.eligible80c || 0,150000) + Math.min(amounts.eligibleNps || 0,50000) + (age >= 60 ? Math.min(amounts.depositInterest + amounts.savingsInterest,50000) : Math.min(amounts.savingsInterest,10000));
    const salaryOld = Math.min(amounts.salary,50000), salaryNew = Math.min(amounts.salary,75000);
    // This is a narrow ordinary-income comparison. Unknown benefits, loss treatment and special rates are excluded.
    const oldTaxable = Math.max(0,gross - salaryOld - oldDed), newTaxable = Math.max(0,gross - salaryNew);
    const base = {year,age,entity:'individual',residency:'resident',special:'none',credits:0};
    const oldResult = estimateOrdinaryTax({...base,regime:'old',taxable:oldTaxable});
    const newResult = estimateOrdinaryTax({...base,regime:'new',taxable:newTaxable});
    // The comparison below audits eligible payments already made in FY25–26; it never models a new payment after that year.
    const withoutClaims = Math.max(0, oldTaxable + Math.min(amounts.eligible80c||0,150000) + Math.min(amounts.eligibleNps||0,50000));
    const noClaimsOld = estimateOrdinaryTax({...base,regime:'old',taxable:withoutClaims});
    const documentedClaimEffect = Math.max(0, Math.min(noClaimsOld.total,newResult.total)-Math.min(oldResult.total,newResult.total));
    comparison = {old:oldResult.total,new:newResult.total,oldTaxable,newTaxable,oldDeductions:oldDed,
      lower:oldResult.total === newResult.total ? 'equal' : oldResult.total < newResult.total ? 'old' : 'new',
      difference:Math.abs(oldResult.total-newResult.total),documentedClaimEffect};
  }
  return {year, cards:sorted,missing,comparison,blockedReason:!old ? 'Tax Year 2026–27 rule package is awaiting separate verification.' : complex ? 'Complex or special income needs separate computation before a whole-case comparison.' : missing.length ? 'Complete and confirm the listed inputs to compare supported ordinary income.' : null};
}
