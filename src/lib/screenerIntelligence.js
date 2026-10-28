// Deterministic research summaries. No predictive score or trading instruction.
const key = value => String(value ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');
export function numeric(value) {
  if (value == null || typeof value === 'boolean') return null;
  const raw = String(value).trim().replace(/[,%₹$\s]/g, '').replace(/−/g, '-');
  if (!/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw)) return null;
  const n = Number(raw); return Number.isFinite(n) ? n : null;
}
export function sourceDate(value) {
  const text = String(value ?? '').trim();
  let match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/), y, m, d;
  if (match) [, y, m, d] = match;
  else {
    match = text.match(/^(\d{1,2})[\s-]+([A-Za-z]{3}),?[\s-]+(\d{4})$/);
    if (!match) return null;
    d = match[1]; m = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'].indexOf(match[2].toLowerCase()) + 1; y = match[3];
  }
  const date = new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
  return date.getUTCFullYear() === Number(y) && date.getUTCMonth() + 1 === Number(m) && date.getUTCDate() === Number(d) ? date.toISOString().slice(0, 10) : null;
}
export function normalizeResearchSnapshot(slug, snapshot) {
  if (!snapshot) return null;
  const rows = (snapshot.rows || []).map(raw => {
    const object = Array.isArray(raw) ? Object.fromEntries(snapshot.columns.map((c, i) => [key(c), raw[i]])) : Object.fromEntries(Object.entries(raw).map(([k, v]) => [key(k), v]));
    const get = (...aliases) => { for (const alias of aliases) { const v = object[key(alias)]; if (v != null && String(v).trim() !== '') return v; } return null; };
    const num = (...aliases) => numeric(get(...aliases));
    return { get, num, name: String(get('Stock Name','stock','company') || 'Unnamed stock'), code: String(get('NSE Code','Stock Code','symbol','ticker') || '').toUpperCase().trim(), isin: String(get('ISIN') || '').toUpperCase().trim(), sector: get('sector','sector_name'), cap: num('Market Capitalization','marketCapCr','Market Cap') };
  });
  return { ...snapshot, slug, rows };
}
const median = values => { const a = values.filter(Number.isFinite).sort((a,b) => a-b); return a.length ? (a[Math.floor((a.length-1)/2)] + a[Math.ceil((a.length-1)/2)]) / 2 : null; };
const fmt = n => Number.isFinite(n) ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(n) : 'Unavailable';
const pct = n => Number.isFinite(n) ? `${fmt(n)}%` : 'Unavailable';
const days = (a,b) => Math.floor((Date.parse(a) - Date.parse(b))/86400000);
const note = 'Numbers describe the full published table, before search or table filters. They are observations, not a probability of profit.';
const PURPOSE = {
  'low-pe':['Valuation relative to history','A lower P/E can reflect weaker expected earnings. Compare profitability and cash generation before drawing a valuation conclusion.'],
  'promoter-holdings':['Reported promoter ownership increases','Ownership changes are disclosed holdings, not evidence of buying today. Corporate actions can also change ownership percentages.'],
  piotroski:['Supplied financial-strength scores','Underlying score components and statement dates are not supplied. A high score is not a forecast or an AGI rating.'],
  'cash-flow':['Cash-generation consistency','Six relative annual observations are supplied; exact fiscal year-end dates and the causes of cash-flow changes are not supplied.'],
  momentum:['Supplied technical momentum','The source score shares price inputs with other technical screens. It is not a calibrated likelihood of gains.'],
  'agi-momentum-candidates':['Six- and twelve-month price leadership','These price candidates omit earnings revisions. Historic price appreciation is not performance since publication.'],
  'agi-value-candidates':['Valuation candidates with eligibility filters','A discount to sector P/E does not establish fair value. Earnings quality, sector context and leverage still need review.'],
  'agi-growth-candidates':['Historical and forecast growth candidates','Forecast EPS and revenue are estimates. Forecast dispersion and revisions are not supplied.'],
  'agi-quality-candidates':['ROE relative to history and industry','High ROE can be influenced by leverage or a small equity base. Cash conversion and accounting quality are not established by this table.'],
  'agi-all-weather-candidates':['A union of factor candidate lists','This is not a weighted All-Weather portfolio. Appearing in several related filters is not independent confirmation.'],
  'golden-cross':['A bullish moving-average condition','SMA50 above SMA200 does not mean a crossover occurred today. It also does not mean the stock will rise.'],
  'death-cross':['A bearish moving-average condition','SMA50 below SMA200 does not mean a crossover occurred today. This is not an instruction to sell or short.'],
  'volume-breakouts':['Price gains with elevated volume','A volume surge is not proof of institutional buying or a breakout above resistance. One observation cannot establish persistence.'],
  'relative-strength':['Three-month performance versus sector','A stock can outperform its sector while falling in absolute price. These are source-period returns, not forward returns.'],
  'fii-holding-increases':['Reported foreign-institution ownership changes','Quarterly disclosures are not live flows. Compare the same reporting period and inspect corporate actions and filing dates.'],
  'dii-holding-increases':['Reported mutual-fund ownership changes','This table covers mutual funds, not all DIIs. Quarterly ownership increases are not evidence of buying today.'],
  'candlestick-patterns':['Daily Hammer-pattern candidates','The source flags a pattern; subsequent confirmation, failure and entry/exit results are not supplied. A Hammer alone does not establish a reversal.'],
  'dividend-quality':['Dividend yield supported by cash-flow filters','Historical cash flow and yield do not guarantee future dividends. Review payout policy, leverage and current earnings.'],
  'earnings-growth':['A combined earnings-growth candidate filter','The filter also contains profitability and price conditions. Historical earnings and forecasts should not be treated as interchangeable.'],
  'analyst-estimate-candidates':['Source analyst-consensus candidates','Strong Buy is an external consensus label, not an AGI recommendation. Estimate revision history, target dispersion and guaranteed upside are not available.'],
  'financial-red-flags':['A curated auditor-resignation watchlist','Membership is not proof of a new or unresolved resignation. Event dates, reasons and resolution require the dated exchange filing.'],
};
export function ownershipPeriods(rows, asOf) {
  const date = new Date(`${asOf}T00:00:00Z`);
  const expected = new Date(Date.UTC(date.getUTCFullYear(), Math.floor(date.getUTCMonth()/3)*3, 0)).toISOString().slice(0,10);
  const result = { expected, current:0, older:0, other:0, missing:0 };
  for (const r of rows) { const v = sourceDate(r.get('Shareholding Date','shareholdingDate')); if (!v) result.missing++; else if(v===expected)result.current++; else if(v<expected)result.older++; else result.other++; }
  return result;
}
function overlap(a,b) {
  const lookup = (rows, prop) => { const m=new Map(); for(const r of rows) {const v=String(r[prop]||'').trim().toLowerCase();if(v)m.set(v,(m.get(v)||0)+1);} return m; };
  const bi=lookup(b.rows,'isin'),bc=lookup(b.rows,'code'),ac=lookup(a.rows,'code'),bn=lookup(b.rows,'name'),an=lookup(a.rows,'name');
  const codeRows=new Map(b.rows.filter(r=>r.code).map(r=>[r.code.toLowerCase(),r]));
  let identified=0, provisional=0;
  for(const r of a.rows) {
    const codeRow=r.code?codeRows.get(r.code.toLowerCase()):null;
    const codeMatch=r.code&&bc.get(r.code.toLowerCase())===1&&ac.get(r.code.toLowerCase())===1&&!(r.isin&&codeRow?.isin&&r.isin!==codeRow.isin);
    if ((r.isin && bi.get(r.isin.toLowerCase())===1) || codeMatch) identified++;
    else if(an.get(r.name.toLowerCase())===1 && bn.get(r.name.toLowerCase())===1) {
      const other=b.rows.find(x=>x.name.toLowerCase()===r.name.toLowerCase());
      // Conflicting supplied identifiers must never be rescued by a name match.
      if(!(r.isin&&other.isin&&r.isin!==other.isin)&&!(r.code&&other.code&&r.code!==other.code))provisional++;
    }
  }
  return { identified, provisional };
}
export function buildScreenerIntelligence({ slug, snapshot, previous=null, universe=[], historical=false, now=new Date().toISOString() }) {
  const target=normalizeResearchSnapshot(slug,snapshot);
  if(!target)return { available:false, reason:'No published table is available.' };
  const rows=target.rows, cards=[], evidence=[];
  const purpose=PURPOSE[slug]||['Imported research candidates','Read the supplied screen definition and verify the underlying financial evidence. The importer does not execute financial rules.'];
  const add=(label,values,unit='',detail='')=>{const valid=values.filter(Number.isFinite);cards.push({label,value:valid.length?(unit==='%'?pct(median(valid)):fmt(median(valid))+unit):'Unavailable',detail:`${valid.length} of ${rows.length} rows have valid inputs. ${detail}`.trim()});};
  const values=(...a)=>rows.map(r=>r.num(...a));
  const ratio=(a,b,fn)=>rows.map(r=>{const x=r.num(...a),y=r.num(...b);return x!=null&&y>0?fn(x,y):null;});
  if(slug==='low-pe') {add('Median discount to 10Y P/E',ratio(['peTtm'],['pe10y'],(x,y)=>(1-x/y)*100),'%','Historical valuation comparison, not fair-value upside.');add('Median trailing P/E',values('peTtm'),'×');}
  else if(slug==='piotroski') {cards.push({label:'Supplied score of 9',value:`${rows.filter(r=>r.num('score')===9).length} / ${rows.length}`,detail:'Source score out of 9; component checks are not available.'});add('Median market cap',rows.map(r=>r.cap),' cr','₹ crore.');}
  else if(slug==='cash-flow') {const all=rows.filter(r=>Array.isArray(r.get('fcf'))&&r.get('fcf').length===6&&r.get('fcf').every(v=>numeric(v)>0));cards.push({label:'Positive in all six periods',value:`${all.length} / ${rows.length}`,detail:'Zeros do not count as positive. Relative annual labels; exact year-end dates were not supplied.'});add('Median latest FCF',rows.map(r=>numeric(r.get('fcf')?.[0])),' cr','₹ crore; absolute size is not a quality ranking.');}
  else if(slug==='momentum') {add('Median supplied score',values('score'),' / 100','A source reading, not a probability.');add('Median weekly excess return',values('relativeWeekChange'),' pp','Stock weekly change minus Nifty 50 weekly change.');}
  else if(slug==='agi-momentum-candidates') {add('Median six-month change',values('Half Yr Change %'),'%');add('Median twelve-month change',values('1Yr change %'),'%');}
  else if(slug==='agi-value-candidates') {add('Median forward earnings yield',values('Forecaster Estimates 1Y forward PE').map(v=>v>0?100/v:null),'%','100 divided by positive forward P/E.');add('Median P/E discount to sector',ratio(['PE TTM Price to Earnings'],['Sector PE TTM'],(x,y)=>x>0?(1-x/y)*100:null),'%','Trailing P/E comparison; not target-price upside.');}
  else if(slug==='agi-growth-candidates') {add('Median FY2 EPS growth',ratio(['Forecaster Estimates 2Y forward EPS Annual'],['Forecaster Estimates 1Y forward EPS Annual'],(x,y)=>(x/y-1)*100),'%','FY2 versus FY1 estimates.');add('Median FY2 revenue growth',ratio(['Forecaster Estimates 2Y forward Revenue Annual'],['Forecaster Estimates 1Y forward Revenue Annual'],(x,y)=>(x/y-1)*100),'%','FY2 versus FY1 estimates.');}
  else if(slug==='agi-quality-candidates') {add('Median ROE above industry',rows.map(r=>{const a=r.num('ROE Annual %'),b=r.num('Industry Return on Equity','Industry Return on Equity ROE');return a!=null&&b!=null?a-b:null;}),' pp');add('Median annual ROE',values('ROE Annual %'),'%');}
  else if(['promoter-holdings','fii-holding-increases','dii-holding-increases'].includes(slug)) {add('Median reported ownership increase',values('promoterChange','FII holding change QoQ %','MF holding change QoQ %'),' pp','Change in ownership percentage points, not a trading flow.');const p=ownershipPeriods(rows,target.as_of);cards.push({label:'Latest completed quarter',value:`${p.current} / ${rows.length}`,detail:`Period ending ${p.expected}; ${p.older} older, ${p.other} later/non-quarter-end, ${p.missing} missing or invalid dates.`});}
  else if(['golden-cross','death-cross'].includes(slug)) {add('Median SMA50 vs SMA200 gap',ratio(['Day SMA50'],['Day SMA200'],(x,y)=>(x/y-1)*100),'%');add('Median weekly price change',values('Week change %'),'%','A source-period change, not return since publication.');}
  else if(slug==='volume-breakouts') {add('Median volume multiple',ratio(['Day Volume'],['Week Volume Avg'],(x,y)=>x/y),'×','Daily volume divided by weekly average volume.');add('Median daily price change',values('Day change %'),'%');}
  else if(slug==='relative-strength') {add('Median three-month sector excess',rows.map(r=>{const a=r.num('Qtr Change %'),b=r.num('Sector Qtr Change %');return a!=null&&b!=null?a-b:null;}),' pp');cards.push({label:'Outperforming but falling',value:String(rows.filter(r=>r.num('Qtr Change %')!=null&&r.num('Qtr Change %')<0).length),detail:'Rows with negative absolute three-month price change. Relative strength alone does not mean a positive return.'});}
  else if(slug==='dividend-quality') {add('Median dividend yield',values('Dividend yield 1yr %'),'%');add('Median FCF / net profit',ratio(['Free Cash Flow Annual Cr'],['Net Profit Annual'],(x,y)=>x/y),'×','Historical cash conversion; not a guarantee of dividend payment.');}
  else if(slug==='earnings-growth') {add('Median quarterly EPS growth',ratio(['Basic EPS Qtr'],['Basic EPS 4Qtr Ago'],(x,y)=>(x/y-1)*100),'%','Same quarter a year earlier; positive baselines only.');add('Median annual revenue growth',values('Revenue Growth Annual YoY %'),'%');}
  else if(slug==='analyst-estimate-candidates') {cards.push({label:'Source consensus',value:'Strong Buy filter',detail:'Provider-defined consensus condition; not an AGI recommendation. Individual forecast changes are not supplied.'});add('Median trailing P/E',values('PE TTM Price to Earnings'),'×');}
  else if(slug==='candlestick-patterns') {cards.push({label:'Source pattern',value:'Daily Hammer',detail:'The imported screen covers this pattern only. Subsequent confirmation and failure are not measured yet.'});add('Median daily price change',values('Day change %'),'%');}
  else if(slug==='financial-red-flags') {cards.push({label:'Watchlist cases',value:String(rows.length),detail:'Curated source membership, not newly verified resignation events.'},{label:'Dated event verification',value:'Not supplied',detail:'The imported table does not include resignation announcement dates or resolution evidence.'});}
  else if(slug==='agi-all-weather-candidates') {
    const factors=['agi-momentum-candidates','agi-value-candidates','agi-growth-candidates','agi-quality-candidates'].map(s=>universe.find(x=>x.slug===s&&x.as_of===target.as_of));
    if(!historical&&factors.every(Boolean)) {
      const counts=new Map(),targetNames=new Set(rows.map(r=>r.name.toLowerCase()));
      for(const factor of factors){const n=normalizeResearchSnapshot(factor.slug,factor),seen=new Map();for(const r of n.rows){const name=r.name.toLowerCase();seen.set(name,(seen.get(name)||0)+1);}for(const [name,count] of seen)if(count===1&&targetNames.has(name))counts.set(name,(counts.get(name)||0)+1);}
      cards.push({label:'In all four factor screens',value:String([...counts.values()].filter(v=>v===4).length),detail:'Provisional exact-name matches within this pool, using same-date tables. Security identifiers still need reconciliation.'},{label:'In at least three factors',value:String([...counts.values()].filter(v=>v>=3).length),detail:'Includes the four-factor matches. These related filters do not provide independent confirmations or portfolio weights.'});
    } else cards.push({label:'Four-factor comparison',value:'Unavailable',detail:'Requires all four same-date factor tables in the latest view. Saved-history comparisons do not use later tables.'},{label:'Candidate pool',value:String(rows.length),detail:'A union of candidates, not a weighted All-Weather portfolio.'});
  }
  else {cards.push({label:'Research candidates',value:String(rows.length),detail:'A source-filtered pool, not a ranked or weighted investment portfolio.'});add('Median forward P/E',values('Forecaster Estimates 1Y forward PE'),'×');}
  const sectorCounts=new Map();for(const r of rows){if(r.sector)sectorCounts.set(r.sector,(sectorCounts.get(r.sector)||0)+1);}
  const sectors=[...sectorCounts].sort((a,b)=>b[1]-a[1]).slice(0,3).map(([name,count])=>({name,count}));
  const age=Math.max(0,days(String(now).slice(0,10),target.as_of));
  const knownCaps=rows.filter(r=>r.cap!=null),small=knownCaps.filter(r=>r.cap<5000).length;
  const dated=rows.map(r=>sourceDate(r.get('Latest financial result','financialResultDate'))).filter(Boolean);
  if(age>7)evidence.push(`This table is ${age} calendar days old. Rechecking the summary does not refresh its prices or fundamentals.`);
  if(small)evidence.push(`${small} of ${knownCaps.length} rows with market-cap data are below ₹5,000 crore. The factor-screen minimum is not automatically applied to other screens.`);
  if(!dated.length)evidence.push('Underlying financial-statement dates are not available in this table. Import date is not the financial period.');
  if(sectors.length)evidence.push(`Largest supplied sector: ${sectors[0].name}, ${sectors[0].count} stocks. Counts are not portfolio weights.`);
  else evidence.push('Sector concentration is unavailable because sector labels were not supplied.');
  if(['promoter-holdings','fii-holding-increases','dii-holding-increases'].includes(slug)){const p=ownershipPeriods(rows,target.as_of);if(p.older||p.other||p.missing)evidence.unshift('Mixed or missing ownership periods: do not describe every row as current-quarter accumulation.');}
  let change={available:false,reason:'First saved publication: changes cannot be inferred.'};
  const prev=normalizeResearchSnapshot(slug,previous);
  const identity=rs=>rs.map(r=>r.isin?`isin:${r.isin}`:r.code?`code:${r.code}`:`name:${r.name.toLowerCase()}`);
  if(prev){const current=new Set(identity(rows)),old=new Set(identity(prev.rows));const modes=items=>[...new Set(items.map(v=>v.split(':')[0]))].sort().join(',');if(modes([...current])!==modes([...old]))change={available:false,reason:'Security identifier coverage changed; entries and exits are withheld until identities are reconciled.'};else{const provisional=rows.some(r=>!r.isin&&!r.code)||prev.rows.some(r=>!r.isin&&!r.code);change={available:true,added:[...current].filter(v=>!old.has(v)).length,removed:[...old].filter(v=>!current.has(v)).length,previousAsOf:prev.as_of,provisional};}}
  const ownership=new Set(['promoter-holdings','fii-holding-increases','dii-holding-increases']);
  const comparable=s=>{if(!ownership.has(s.slug))return s;const period=ownershipPeriods([],s.as_of).expected;return {...s,rows:s.rows.filter(r=>sourceDate(r.get('Shareholding Date','shareholdingDate'))===period)};};
  const overlaps=historical?[]:universe.filter(x=>x.slug!==slug&&x.as_of===target.as_of&&!(slug.startsWith('agi-')&&slug!=='agi-all-weather-candidates'&&x.slug==='agi-all-weather-candidates')).map(s=>{const other=normalizeResearchSnapshot(s.slug,s);return{slug:s.slug,name:s.display_name||s.definition?.display_name||s.slug,asOf:s.as_of,period:ownership.has(slug)||ownership.has(s.slug)?ownershipPeriods([],target.as_of).expected:null,...overlap(comparable(target),comparable(other))};}).filter(x=>x.identified||x.provisional).sort((a,b)=>b.identified-a.identified||b.provisional-a.provisional).slice(0,3);
  return { available:true,version:1,slug,snapshotId:target.id,asOf:target.as_of,recordedAt:target.created_at,generatedAt:now,rowCount:rows.length,purpose:purpose[0],caution:purpose[1],cards,changes:change,overlaps,overlapNote:historical?'Cross-screen context is withheld in saved-history views to avoid using later publications.':'Compared only with other available tables bearing the same data date. Ownership matches use only the latest completed reporting quarter; older, non-quarter-end and missing periods are excluded. Code/ISIN matches are distinct from provisional exact-name matches. The parent All-Weather union is excluded from individual factor comparisons. Related screens share inputs; matches are not independent confirmations.',ageDays:age,evidence,sectors,note,sourceUrl:target.source_url||null,performance:'Forward performance since publication is not measured by this summary. Source-period returns must not be presented as subsequent investment results.' };
}
