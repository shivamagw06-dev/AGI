import { estimateOrdinaryTax } from './wealthTax.js';
import { TAX_SOURCES } from './taxOpportunity.js';

const item=(id,title,detail,questions,evidence,source,priority,impact=null,kind='review')=>({id,title,detail,questions,evidence,source,priority,impact,kind});
const rupees=value=>Number(value||0);
const active=(context,key)=>Boolean(context?.[key]);

/** Order opportunities by verified effect and missing evidence, never by a nominal deduction limit. */
export function taxDecisionBrief({form,scan,reconciliation={},propertySchedule=null,context={},asOf='2026-09-25'}) {
  if(!form||!scan||form.year!==scan.year)throw new Error('Tax case and scan must describe the same income year.');
  const old=form.year==='2025-26', taxYear=old?'FY 2025–26 / AY 2026–27':'Tax Year 2026–27';
  const items=[];
  const add=(...args)=>items.push(item(...args));
  const mismatch=reconciliation.comparisons?.filter(c=>c.status==='difference')||[];
  if((reconciliation.unmatched||0)>0||mismatch.length||reconciliation.warnings?.length)
    add('reconcile','Resolve records before calculating',`Review ${reconciliation.unmatched||0} unreviewed rows, ${mismatch.length} income differences and ${reconciliation.warnings?.length||0} duplicate or year warnings. Check whether TDS is credited to the correct tax year; a credit is not a deduction.`,
      ['Which source is authoritative for each mismatch?','Was any income or tax credit assigned to the wrong owner or year?'],
      'Source statement, AIS/26AS or Form 168, original tax certificate',TAX_SOURCES.ais,0,null,'blocker');
  if(scan.comparison){
    const c=scan.comparison;
    add('regime','Compare your complete old and new regime cases',
      `On the entered simple income, the ${c.lower==='equal'?'two regimes tie':c.lower+' regime is lower'}. The estimated difference is a scenario result; confirm every deduction and any omitted income before choosing.`,
      ['Were HRA, employer NPS, other income and losses included?','Is the regime election available for this taxpayer?'],
      'Form 16, salary structure, bank interest statements and election history',TAX_SOURCES.regime,1,c.difference,'estimate');
    const age=Number(form.age),deposit=rupees(form.depositInterest),savings=rupees(form.savingsInterest);
    const eligible=age>=60?Math.min(deposit+savings,50000):Math.min(savings,10000);
    if(eligible>0){
      const oldWithout=estimateOrdinaryTax({year:'2025-26',age,entity:'individual',residency:'resident',special:'none',credits:0,
        regime:'old',taxable:c.oldTaxable+eligible});
      const impact=Math.max(0,Math.min(oldWithout.total,c.new)-Math.min(c.old,c.new));
      add('interest',age>=60?'Check senior deposit-interest deduction':'Check savings-interest deduction',
        `An eligible old-regime deduction of up to ₹${eligible.toLocaleString('en-IN')} is already included in this scenario. Its estimated effect after choosing the lower supported regime is ₹${impact.toLocaleString('en-IN')}. FD interest is not eligible for the non-senior savings-account deduction.`,
        ['Are you a resident individual of the stated age?','Do bank certificates split savings interest from FD/deposit interest?'],
        'Bank interest certificates, age and residency',TAX_SOURCES.interest,2,impact,'estimate');
    }
    if(rupees(form.eligible80c)+rupees(form.eligibleNps)>0)
      add('already-paid','Verify eligible 80C and NPS payments already made',
        `The combined estimated effect of recorded 80C and extra personal NPS payments on the lowest supported regime is ₹${c.documentedClaimEffect.toLocaleString('en-IN')}. A deduction under a regime that is not selected may have no net effect.`,
        ['Were the amounts paid within FY 2025–26?','Did employee EPF already use some of the 80C ceiling?','Is the NPS payment counted only once?'],
        'EPF, PPF, ELSS or tuition receipts and PRAN statement',TAX_SOURCES.regime,3,c.documentedClaimEffect,'estimate');
  }else if(!old){
    add('current-law','Prepare the current-year regime comparison',
      'Tax Year 2026–27 is governed by the Income Tax Act, 2025. Record all income and eligible payments now, then check the new Act rule package and department calculator before acting on a numeric comparison.',
      ['Do you have business income or a restricted prior regime election?','Are you comparing net cash saved after the cost and lock-in of a product?'],
      'Payroll projection, investment confirmations and new Act section mapping',TAX_SOURCES.year,2,null,'pending-rule');
  }
  if(!old && (rupees(form.salary)||rupees(form.depositInterest)||rupees(form.savingsInterest)))
    add('section-123','Review already used investment allowance before adding a product',
      'The 2025 Act refers to Schedule XV read with section 123 for the category previously known as 80C. Check current-year eligibility and whether EPF or other existing payments already consume the relevant ceiling; do not purchase solely for a nominal deduction.',
      ['How much employee EPF, PPF, insurance, tuition or eligible principal will already be paid this year?','Would the old regime beat the new after *all* deductions and investment costs?'],
      'EPF statements, eligible receipts and expected payroll', TAX_SOURCES.year,5,null,'qualification');
  if(active(context,'receivesHra')&&rupees(form.salary)>0)
    add('hra','Reconstruct the HRA exemption',
      'A rent payment or HRA label alone does not establish an exemption. Compare actual HRA, rent less the prescribed salary share, and the applicable metro/non-metro salary fraction only after salary components and housing facts are verified.',
      ['What are basic pay, qualifying DA, HRA received and rent actually paid?','Did you own or occupy the same home, and what is the city?'],
      'Form 16, salary slips, tenancy and rent receipts',old?TAX_SOURCES.salary:TAX_SOURCES.year,4,null,'qualification');
  if(active(context,'employerNps'))
    add('employer-nps','Check employer NPS separately',
      'An employer contribution follows its own conditions and limits and can change the regime comparison. Do not combine it with a personal NPS contribution or a simple 80C total.',
      ['How much did the employer contribute and what is the eligible salary basis?','Has payroll already included and deducted it correctly?'],
      'Employer contribution certificate, salary and PRAN record',old?TAX_SOURCES.salary:TAX_SOURCES.year,4,null,'qualification');
  if(rupees(form.eligible80d)>0||active(context,'parentCover')){
    const healthAmount=old&&scan.comparison&&form.healthValidated?rupees(form.eligible80d):0;
    let healthImpact=null;
    if(healthAmount>0){
      const c=scan.comparison;
      const oldWithout=estimateOrdinaryTax({year:'2025-26',age:Number(form.age),entity:'individual',residency:'resident',special:'none',credits:0,
        regime:'old',taxable:c.oldTaxable+healthAmount});
      healthImpact=Math.max(0,Math.min(oldWithout.total,c.new)-Math.min(c.old,c.new));
    }
    add('health','Check insured persons before claiming health cover',
      healthImpact==null?'Premium eligibility depends on the insured person’s age, relationship, payment mode and the selected regime. Confirm details before calculating a FY 2025–26 claim.':`Qualified FY 2025–26 premium deduction of ₹${healthAmount.toLocaleString('en-IN')} is included. Its estimated effect after selecting the lower regime is ₹${healthImpact.toLocaleString('en-IN')}.`,
      ['Who is covered and what is each person’s age?','Was the premium paid in this year by an eligible method and not claimed twice?'],
      'Policy schedule, premium receipts, insured ages and bank payment',old?TAX_SOURCES.regime:TAX_SOURCES.year,4,healthImpact,healthImpact==null?'qualification':'estimate');
  }
  if(active(context,'donated'))
    add('donation','Verify eligible donation and deduction rate',
      'A receipt alone does not establish the deductible percentage or whether a qualifying limit applies. Verify the donee, payment and required certificate before claiming.',
      ['Is the recipient approved for the selected year?','Was a required certificate issued, and is the amount within any qualifying limit?'],
      'Donation receipt, certificate and payment trail',old?TAX_SOURCES.regime:TAX_SOURCES.year,5,null,'qualification');
  if(form.hasRental||rupees(propertySchedule?.rent)>0)
    add('property','Reconcile rental income property by property',
      propertySchedule? `Provisional property income is ₹${propertySchedule.propertyIncome.toLocaleString('en-IN')} before any loss-setoff restrictions. Check ownership share, municipal payments, qualifying interest and classification.`:
        'Compute annual value, owner-paid municipal tax and eligible interest separately for every property. Hotel operations and inseparable service contracts may need another income head.',
      ['Is this pure let-out house property or a hotel/composite service?','Who legally owns each share, and which municipality taxes were actually paid?'],
      'Titles, leases, receipts, municipal tax and loan certificate',TAX_SOURCES.property,4,null,'qualification');
  if(form.hasGains||active(context,'inheritedSale')||(reconciliation.investmentOrders||0)>0)
    add('gains','Rebuild fund and property sale cost before seeking relief',
      'An order amount is not a taxable capital gain. Match completed allotments/redemptions, units, previous-owner cost where inherited, and sale timing. Check exemption conditions only after a realised gain is established.',
      ['Is there a completed sale with cost, date and beneficial owner?','Were property reinvestment or bond-exemption time windows actually met?'],
      'CAS, broker contract notes, deeds, previous-owner cost and allotment records',TAX_SOURCES.gains,4,null,'qualification');
  if(form.hasBusiness||active(context,'hotel'))
    add('business','Separate hotel/business books from passive rent',
      'Compare actual evidenced business costs and depreciation with an eligible presumptive method only after classifying receipts. Under a presumptive computation, do not deduct the same expenses again.',
      ['Are accommodation and rentals booked separately?','Are expenses business-only, invoice-backed and not already claimed?'],
      'Books, asset register, invoices, payroll and turnover',TAX_SOURCES.business,4,null,'qualification');
  if(form.hasRental||form.hasBusiness||active(context,'hotel'))
    add('gst','Review GST invoices and credits separately',
      'GST on supplies and income tax on profits are separate calculations. Match invoice tax, supply category and eligible input credits; do not treat GST collected as personal income-tax paid.',
      ['What was supplied, by whom, to whom and on what date?','Do purchase invoices match available input-tax credits?'],
      'GST registration, agreements, GSTR-1, GSTR-3B and GSTR-2B',TAX_SOURCES.gst,5,null,'qualification');
  if(form.hasForeign)
    add('foreign','Verify foreign income and residential status',
      'Overseas accounts, assets, treaties and foreign tax credits can change filing schedules and liability. Moving address alone does not make Indian-source income exempt.',
      ['What is the verified day-count residence and source of each receipt?','Is foreign tax credit supported by proof?'],
      'Travel days, broker/bank records and treaty/credit documents',TAX_SOURCES.year,4,null,'qualification');
  if(rupees(form.depositInterest)>0 && !old)
    add('advance-tax','Check advance tax on interest',
      'Interest may cause tax beyond employer withholding. Confirm actual tax credits and the tax-year payment schedule before paying; the income-tax threshold is not a deduction.',
      ['How much tax has already been withheld and credited in the right tax year?','Is the person eligible for a senior exemption from advance-tax payment?'],
      'Interest projections, tax-credit statement and payment challans','https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/tax-payments',6,null,'compliance');
  const sorted=items.sort((a,b)=>a.priority-b.priority||(b.impact??-1)-(a.impact??-1));
  return {taxYear,asOf,items:sorted,numericCount:sorted.filter(x=>x.impact!=null).length,
    methodology:'Amounts represent whole-case differences within the supported FY25–26 ordinary-income fact pattern. No unsupported current-year, hotel, investment-gain or GST savings are quantified.'};
}
