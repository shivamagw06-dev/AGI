// Head-of-house-property schedule only: does not determine income classification, set-off or GST.
export function housePropertySchedule(input) {
  const number=(key)=>{const v=String(input[key]??'').trim();if(!/^\d+(?:\.\d{1,2})?$/.test(v)||Number(v)>1e12)throw new Error(`Enter a valid non-negative ${key} amount.`);return Number(v);};
  const rent=number('rent'),municipal=number('municipal'),interest=number('interest');
  if(municipal>rent)throw new Error('Municipal tax paid exceeds the rent entered; review the property facts.');
  if(!input.confirmedHouseProperty)throw new Error('Confirm this is ordinary let-out house property, not hotel services or inseparable composite letting.');
  const netAnnualValue=rent-municipal,standardDeduction=netAnnualValue*.3;
  return {rent,municipal,netAnnualValue,standardDeduction,interest,propertyIncome:netAnnualValue-standardDeduction-interest,
    note:'Provisional annual-value schedule only. Vacancy, fair rent, loan eligibility, co-ownership and loss set-off require further review.'};
}
