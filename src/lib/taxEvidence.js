// Client-side evidence staging. Source files stay in memory until the tab is closed.
export const EVIDENCE_CATEGORIES = Object.freeze({
  salary:'Salary / pension', deposit_interest:'FD / deposit interest', savings_interest:'Savings interest',
  rent:'Rent', dividend:'Dividends', capital_gains:'Capital gains', business:'Business / hotel',
  other:'Other income', tax_credit:'TDS / tax payment', investment:'Investment transaction',
});
const LIMIT = 1000;
const incomeYear = date => {const y=Number(date.slice(0,4)),m=Number(date.slice(5,7));return `${m>=4?y:y-1}-${String((m>=4?y:y-1)+1).slice(-2)}`;};
const amount = (value, label) => {
  const plain = String(value ?? '').trim().replace(/^₹/, '').replace(/,/g,'');
  if (!plain) return 0;
  if (!/^\d+(?:\.\d{1,2})?$/.test(plain) || Number(plain)>1e12) throw new Error(`Invalid ${label}: use a non-negative rupee amount.`);
  return Number(plain);
};
export function parseEvidenceCsv(text) {
  if (typeof text !== 'string' || text.length > 2_000_000) throw new Error('CSV must be smaller than 2 MB.');
  const cells=[]; let row=[], cell='', quoted=false;
  for (let i=0;i<text.length;i++) {
    const char=text[i];
    if (quoted) {if(char==='"' && text[i+1]==='"'){cell+='"';i++;} else if(char==='"') quoted=false; else cell+=char;}
    else if(char==='"'){if(cell) throw new Error('Malformed CSV quotation.');quoted=true;}
    else if(char===','){row.push(cell);cell='';}
    else if(char==='\n' || char==='\r'){if(char==='\r' && text[i+1]==='\n')i++;row.push(cell);if(row.some(v=>v.trim()))cells.push(row);row=[];cell='';if(cells.length>LIMIT+1)throw new Error('Limit imports to 1,000 records.');}
    else cell+=char;
  }
  if(quoted)throw new Error('Unclosed CSV quotation.');
  row.push(cell);if(row.some(v=>v.trim()))cells.push(row);
  if(cells.length<2)throw new Error('CSV needs a header and at least one record.');
  const headers=cells[0].map((v,i)=>v.replace(/^\uFEFF/,'').trim() || `Column ${i+1}`);
  if(headers.length>100 || cells.slice(1).some(r=>r.length!==headers.length))throw new Error('CSV columns are inconsistent.');
  return {headers, rows:cells.slice(1)};
}
export function mapEvidenceCsv(parsed, config) {
  const {headers,rows}=parsed;
  const index=key=>{const selected=config[key];return selected==null||selected==='' ? -1 : headers.findIndex((_,i)=>String(i)===String(selected));};
  const columns={amount:index('amount'),credit:index('credit'),category:index('category'),reference:index('reference'),date:index('date')};
  if(columns.amount<0 && columns.credit<0)throw new Error('Map an income amount or a tax-credit column.');
  if(!EVIDENCE_CATEGORIES[config.defaultCategory])throw new Error('Select an evidence category.');
  const result=rows.map((r,i)=>{
    const get=k=>columns[k]<0?'':r[columns[k]].trim();
    const category=columns.category<0?config.defaultCategory:get('category').toLowerCase();
    if(!EVIDENCE_CATEGORIES[category])throw new Error(`Row ${i+2}: unknown category. Select a single category or use the category codes shown.`);
    const value=amount(get('amount'),`amount on row ${i+2}`), credit=amount(get('credit'),`credit on row ${i+2}`);
    if(category==='tax_credit'&&value&&credit)throw new Error(`Row ${i+2}: map each tax payment to one amount column, not both.`);
    if(!value && !credit)return null;
    const date=get('date');if(date && (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date)) || new Date(date).toISOString().slice(0,10)!==date))throw new Error(`Row ${i+2}: use YYYY-MM-DD for the date.`);
    return {id:`${config.batchId}:${i}`,ownerId:config.ownerId,year:config.year,source:config.source.slice(0,120),category,
      amount:value,credit,reference:get('reference').slice(0,120),date,reviewed:false};
  }).filter(Boolean);
  if(!result.length)throw new Error('No nonzero records found.');
  return result;
}
export function parseUpstoxFundOrders(text,{ownerId,year,batchId}) {
  if(typeof text!=='string'||text.length>2_000_000)throw new Error('Order export must be under 2 MB.');
  let parsed;try{parsed=JSON.parse(text);}catch{throw new Error('Orders must be valid JSON.');}
  const orders=Array.isArray(parsed)?parsed:parsed?.data;
  if(!Array.isArray(orders)||orders.length>LIMIT)throw new Error('Expected an Upstox mutual fund order array (up to 1,000 records).');
  const ids=new Set();
  return orders.map((o,i)=>{
    if(!o||typeof o!=='object'||!['BUY','SELL'].includes(o.transaction_type)||typeof o.order_id!=='string')throw new Error(`Order ${i+1} is incomplete.`);
    if(ids.has(o.order_id))throw new Error(`Duplicate order id in import: order ${i+1}.`);
    ids.add(o.order_id);
    const status=String(o.status||'').toUpperCase();
    const proceeds=amount(o.amount,`order ${i+1} amount`);
    const date=String(o.order_timestamp||'').slice(0,10);
    if(date && (!/^\d{4}-\d{2}-\d{2}$/.test(date)||Number.isNaN(Date.parse(date))||incomeYear(date)!==year))throw new Error(`Order ${i+1} is undated or outside the selected income year. Import orders one year at a time.`);
    if(!date)throw new Error(`Order ${i+1} needs a date to assign its income year.`);
    return {id:`${batchId}:${i}`,ownerId,year,source:'Upstox mutual fund order export',category:'investment',amount:proceeds,
      credit:0,reference:o.order_id.slice(0,120),date,reviewed:false,description:String(o.fund||o.instrument_key||'Fund').slice(0,160),
      transactionType:o.transaction_type,status,quantity:amount(o.quantity,`order ${i+1} units`),
      note:status==='COMPLETED'?'Completed order; match units, folio, cost and redemption records before computing gains.':'Unsettled or unsuccessful order; exclude from tax calculations.'};
  });
}
export function reconcileTaxEvidence(rows,ownerId,year,declared={}) {
  const scoped=rows.filter(r=>r.ownerId===ownerId&&r.year===year);
  const totals={}; const warnings=[]; const keys=new Map();
  for(const r of scoped){
    if(r.category!=='investment'){
      if(r.category!=='tax_credit')totals[r.category]=(totals[r.category]||0)+Number(r.amount||0);
      totals.tax_credit=(totals.tax_credit||0)+Number(r.credit||0)+(r.category==='tax_credit'?Number(r.amount||0):0);
    }
    if(r.date && incomeYear(r.date)!==year)warnings.push(`Record ${r.reference||r.id} is dated outside ${year}; check its income year.`);
    const key=r.reference?[r.category,r.reference.toLowerCase(),r.amount,r.credit].join('|'):
      r.date?[r.category,r.date,r.amount,r.credit].join('|'):null;
    if(key){const previous=keys.get(key);if(previous)warnings.push(`Possible duplicate ${r.reference||r.date} across ${previous.source} and ${r.source}.`);else keys.set(key,r);}
  }
  const comparisons=[['salary','salary'],['deposit_interest','depositInterest'],['savings_interest','savingsInterest']].map(([category,field])=>({
    category,declared:declared[field]===''||declared[field]==null?null:amount(declared[field],field),evidence:totals[category]??null,
  })).map(r=>({...r,status:r.declared==null||r.evidence==null?'needs evidence':Math.abs(r.declared-r.evidence)>1?'difference':'matched'}));
  const unmatched=scoped.filter(r=>!r.reviewed).length;
  return {totals,comparisons,warnings:[...new Set(warnings)],unmatched,investmentOrders:scoped.filter(r=>r.category==='investment').length,
    missingCategories:scoped.filter(r=>!['salary','deposit_interest','savings_interest','investment','tax_credit'].includes(r.category)&&r.amount>0).map(r=>r.category).filter((v,i,a)=>a.indexOf(v)===i)};
}
export function restoreTaxReview(text,ownerId) {
  if(typeof text!=='string'||text.length>2_000_000)throw new Error('Tax review must be under 2 MB.');
  let raw;try{raw=JSON.parse(text);}catch{throw new Error('Invalid tax review JSON.');}
  if(raw?.version!==1||!['2025-26','2026-27'].includes(raw.year)||!raw.case||raw.case.year!==raw.year||
    !Array.isArray(raw.evidence)||raw.evidence.length>LIMIT)throw new Error('Unsupported tax review format.');
  const allowed=['age','salary','depositInterest','savingsInterest','eligible80c','eligible80d','eligibleNps'];
  const form={year:raw.year,recordsConfirmed:false,claimsConfirmed:false};
  for(const key of allowed){
    const v=raw.case[key];if(v!==''&&v!=null && (typeof v!=='string'&&typeof v!=='number'||!/^\d+(?:\.\d{1,2})?$/.test(String(v))||Number(v)>1e12))throw new Error(`Invalid ${key} in tax review.`);
    form[key]=v==null?'':String(v);
  }
  for(const key of ['hasRental','hasGains','hasBusiness','hasForeign','otherIncome']){
    if(typeof raw.case[key]!=='boolean')throw new Error(`Invalid ${key} in tax review.`);form[key]=raw.case[key];
  }
  if(form.age && (Number(form.age)<18||Number(form.age)>120||!/^\d+$/.test(form.age)))throw new Error('Invalid age in tax review.');
  const evidence=raw.evidence.map((r,i)=>{
    if(!r||!EVIDENCE_CATEGORIES[r.category]||typeof r.source!=='string'||r.source.length>120||
      typeof r.reference!=='string'||r.reference.length>120||typeof r.date!=='string'||r.date.length>10||
      r.date && (!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||Number.isNaN(Date.parse(r.date)))||
      !Number.isFinite(r.amount)||r.amount<0||r.amount>1e12||!Number.isFinite(r.credit)||r.credit<0||r.credit>1e12||
      r.category==='investment' && (!['BUY','SELL'].includes(r.transactionType)||!['COMPLETED','NEW','PENDING','OPEN','INPROCESS','PLACED','REJECTED','CREATED','PAYMENT_PENDING','FAILED','CANCELLED','VERIFIED','ARCHIVED'].includes(r.status)))throw new Error(`Invalid evidence row ${i+1}.`);
    return {id:`restored:${i}`,ownerId,year:raw.year,source:r.source,category:r.category,amount:r.amount,credit:r.credit,
      reference:r.reference,date:r.date,reviewed:false,...r.category==='investment'?{transactionType:r.transactionType,status:r.status,
      description:String(r.description||'').slice(0,160),quantity:Math.max(0,Number(r.quantity)||0),note:String(r.note||'').slice(0,250)}:{}};
  });
  const property={rent:'',municipal:'',interest:'',confirmedHouseProperty:false};
  if(raw.propertyInputs!=null){
    if(typeof raw.propertyInputs!=='object'||Array.isArray(raw.propertyInputs))throw new Error('Invalid property inputs.');
    for(const key of ['rent','municipal','interest']){
      const v=String(raw.propertyInputs[key]??'');
      if(v && (!/^\d+(?:\.\d{1,2})?$/.test(v)||Number(v)>1e12))throw new Error(`Invalid property ${key}.`);
      property[key]=v;
    }
  }
  const signals={};
  const allowedSignals=['receivesHra','employerNps','parentCover','donated','inheritedSale','hotel'];
  if(raw.signals!=null){
    if(typeof raw.signals!=='object'||Array.isArray(raw.signals))throw new Error('Invalid follow-up answers.');
    for(const key of allowedSignals){
      if(raw.signals[key]!=null && typeof raw.signals[key]!=='boolean')throw new Error(`Invalid answer ${key}.`);
      signals[key]=Boolean(raw.signals[key]);
    }
  }
  const health={selfPremium:'',parentPremium:'',parentAge:'',nonCashPaid:false,eligibleRelationship:false,paidInYear:false,notDoubleClaimed:false};
  if(raw.healthInputs!=null){
    if(typeof raw.healthInputs!=='object'||Array.isArray(raw.healthInputs))throw new Error('Invalid health premium details.');
    for(const key of ['selfPremium','parentPremium','parentAge']){
      const v=String(raw.healthInputs[key]??'');
      if(v && (!/^\d+(?:\.\d{1,2})?$/.test(v)||Number(v)>1e12||key==='parentAge'&&(!/^\d+$/.test(v)||Number(v)>120)))throw new Error(`Invalid ${key} in tax review.`);
      health[key]=v;
    }
    for(const key of ['nonCashPaid','eligibleRelationship','paidInYear','notDoubleClaimed'])
      if(raw.healthInputs[key]!=null&&typeof raw.healthInputs[key]!=='boolean')throw new Error(`Invalid ${key} in tax review.`);
  }
  return {form,evidence,property,signals,health};
}
