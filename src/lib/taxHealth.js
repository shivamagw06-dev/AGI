// FY 2025–26 insurance-premium part of section 80D only. No check-ups or senior medical expenses.
export function assessInsurancePremium(input) {
  const value=(key)=>{const raw=String(input[key]??'').trim();if(!raw)return null;if(!/^\d+(?:\.\d{1,2})?$/.test(raw)||Number(raw)>1e12)throw new Error(`Enter a valid ${key} amount.`);return Number(raw);};
  const self=value('selfPremium'),parent=value('parentPremium');
  if(self==null||parent==null)throw new Error('Enter both self/family and parent premiums (0 if none).');
  const selfAge=Number(input.selfAge),parentAge=parent>0?Number(input.parentAge):null;
  if(!Number.isInteger(selfAge)||selfAge<18||selfAge>120)throw new Error('Enter the taxpayer age at the end of the year.');
  if(parent>0&&(!Number.isInteger(parentAge)||parentAge<18||parentAge>120))throw new Error('Enter the insured parent’s age at year end.');
  if((self>0||parent>0)&&(!input.nonCashPaid||!input.eligibleRelationship||!input.paidInYear||!input.notDoubleClaimed))
    throw new Error('Confirm eligible insured persons, non-cash premium payment in the chosen year, and no duplicate claim.');
  return {deduction:Math.min(self,selfAge>=60?50000:25000)+Math.min(parent,parentAge>=60?50000:25000),
    selfAllowed:Math.min(self,selfAge>=60?50000:25000),parentAllowed:Math.min(parent,parentAge>=60?50000:25000),
    excluded:'Preventive check-ups and uncovered senior medical expenses are not included.'};
}
