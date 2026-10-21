import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
// Run with the bundled artifact-tool runtime; baseline must be the v1 library.
const [baselineBook,baselineCatalog,outDir]=process.argv.slice(2);
if(!baselineBook||!baselineCatalog||!outDir)throw Error('Usage: baseline.xlsx baseline.json output-directory');
await fs.mkdir(outDir,{recursive:true});
const catalog=JSON.parse(await fs.readFile(baselineCatalog,'utf8'));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(baselineBook));
if(catalog.version!==1)throw Error('Use the v1 baseline, not an already upgraded workbook.');
const C=['E','F','G','H','I'],cases=['Base','Downside','Upside'];
const num='#,##0.0;(#,##0.0);"–"';
const val=(s,a,v)=>s.getRange(a).values=[[v]];
const formula=(s,a,f)=>s.getRange(a).formulas=[['='+f]];
const band=(s,r,label)=>{val(s,`C${r}`,label);s.getRange(`C${r}:I${r}`).format={fill:'#19354D',font:{bold:true,color:'#FFFFFF'},rowHeight:25};};
const row=(s,r,label,forms,format=num)=>{val(s,`C${r}`,label);s.getRange(`E${r}:I${r}`).formulas=[forms.map(f=>'='+f)];s.getRange(`E${r}:I${r}`).setNumberFormat(format);};
const input=(s,r,label,v,format=num)=>{val(s,`C${r}`,label);val(s,`D${r}`,v);s.getRange(`D${r}`).setNumberFormat(format);s.getRange(`D${r}`).format={fill:'#FFF2CC',font:{color:'#0000FF'}};};
const controls=wb.worksheets.getItem('Controls');
val(controls,'C17','First forecast financial year (ending March)');val(controls,'E17',2027);
controls.getRange('E17').setNumberFormat('0');controls.getRange('E17').dataValidation={rule:{type:'whole',operator:'between',formula1:2020,formula2:2040}};
val(controls,'C18','Opening balance / valuation date');formula(controls,'E18','DATE(E17-1,3,31)');controls.getRange('E18').setNumberFormat('dd-mmm-yyyy');
C.forEach((c,i)=>formula(controls,`${c}19`,`DATE($E$17+${i},3,31)`));
val(controls,'C22','Annual drivers have independent Base / Downside / Upside inputs.');val(controls,'C27','Opening balances and annual valuation date follow the selected first forecast year.');
const metadata={};
for(const m of catalog.models){
 const s=wb.worksheets.getItem(m.name),cells=catalog.sheets[m.name];
 const find=(label)=>m.rows.find(r=>r.label===label)?.row;
 const inp=(label)=>m.inputs.find(r=>r.label===label)?.refs[0];
 const op=!!inp('WACC'),debt=op||m.name==='Real Estate';
 metadata[m.name]={sensitivities:[],history:[],summaryRange:'M2:U28'};
 s.showGridLines=false;s.getRange('C110:I510').format.font={name:'Arial',size:10,color:'#000000'};
 s.getRange('C110:C510').format.wrapText=true;s.getRange('C110:I510').format.rowHeight=30;
 C.forEach((c,i)=>{formula(s,`${c}7`,`'Controls'!$E$17+${i}`);s.getRange(`${c}7`).setNumberFormat('"FY"0"E"');});
 // Remove obsolete literal years in descriptive labels, without changing formulas.
 for(const [a,v] of Object.entries(cells))if(!/^[E-I]7$/.test(a)&&typeof v.v==='string'&&!v.f&&/31 March 2026|31 Mar 2026|FY:27|FY:31/.test(v.v))val(s,a,v.v.replace(/31 March 2026|31 Mar 2026/g,'the opening valuation date').replace(/FY:27/g,'first forecast year').replace(/FY:31/g,'final forecast year'));
 band(s,110,'SUPPORTING SCHEDULE ASSUMPTIONS');
 if(debt){if(op)input(s,114,'Current-year capex depreciation fraction',0,'0.0%');input(s,115,'Debt movement interest weighting',0,'0.0%');val(s,'K115','0 = opening debt interest; 0.5 = mid-year movements; 1 = full-year movements.');}
 input(s,116,'Opening tax losses available for use',0);input(s,117,'Tax loss utilization share of positive PBT',1,'0.0%');val(s,'K117','Simplified cash tax schedule. Check company-specific eligibility, expiry, MAT and deferred tax separately.');
 const pbt=find('Profit before tax'),tax=find('Cash income tax')||find('Tax');
 const taxInput=m.inputs.find(r=>/Effective.*tax rate/i.test(r.label)).refs[0].replace(/^[A-Z]+/,'');
 band(s,139,'CASH TAX SCHEDULE');
 row(s,140,'Opening usable tax losses',C.map((c,i)=>i?`${C[i-1]}145`:'$D$116'));
 row(s,141,'Profit before tax for loss utilization',C.map(c=>`${c}${pbt}`));
 row(s,142,'Tax losses utilized',C.map(c=>`MIN(${c}140,MAX(0,${c}141)*$D$117)`));
 row(s,143,'Taxable profit after loss utilization',C.map(c=>`MAX(0,${c}141-${c}142)`));
 row(s,144,'Cash income tax after loss utilization',C.map(c=>`${c}143*${c}${taxInput}`));
 row(s,145,'Closing usable tax losses',C.map(c=>`${c}140-${c}142+MAX(0,-${c}141)`));
 C.forEach(c=>formula(s,`${c}${tax}`,`${c}144`));
 if(debt){
  const opening=inp('Opening debt'),borrow=m.inputs.find(r=>/^(New borrowing|New debt)$/.test(r.label)).row,repay=m.inputs.find(r=>/principal repayment/i.test(r.label)).row,rate=m.inputs.find(r=>/Interest on opening debt/.test(r.label)).row;
  band(s,119,'DEBT AND INTEREST SCHEDULE');
  row(s,120,'Opening debt balance',C.map((c,i)=>i?`${C[i-1]}123`:opening));
  row(s,121,'Debt drawn',C.map(c=>`${c}${borrow}`));row(s,122,'Debt principal repaid',C.map(c=>`${c}${repay}`));
  row(s,123,'Closing debt balance',C.map(c=>`${c}120+${c}121-${c}122`));
  row(s,124,'Interest-bearing debt base',C.map(c=>`${c}120+(${c}121-${c}122)*$D$115`));
  row(s,125,'Scheduled interest expense',C.map(c=>`${c}124*${c}${rate}`));
  C.forEach(c=>{formula(s,`${c}${find('Closing debt')}`,`${c}123`);formula(s,`${c}${find('Interest expense')}`,`${c}125`);});
  if(!op){band(s,147,'MODEL CHECKS');row(s,148,'Debt below zero',C.map(c=>`MAX(0,-${c}123)`));}
 }
 if(op){
  const ppe=inp('Opening net PP&E'),capex=find('Capital expenditure'),daRate=m.inputs.find(r=>r.label==='D&A / opening net PP&E').row;
  band(s,129,'CAPEX AND DEPRECIATION SCHEDULE');
  row(s,130,'Opening net property plant and equipment',C.map((c,i)=>i?`${C[i-1]}135`:ppe));
  row(s,131,'Capital expenditure added',C.map(c=>`${c}${capex}`));
  row(s,132,'Depreciation on opening assets',C.map(c=>`${c}130*${c}${daRate}`));
  row(s,133,'Depreciation on current-year additions',C.map(c=>`${c}131*${c}${daRate}*$D$114`));
  row(s,134,'Total depreciation charge',C.map(c=>`${c}132+${c}133`));
  row(s,135,'Closing net property plant and equipment',C.map(c=>`${c}130+${c}131-${c}134`));
  C.forEach(c=>{formula(s,`${c}${find('Depreciation and amortization')}`,`${c}134`);formula(s,`${c}${find('Closing net PP&E')}`,`${c}135`);});
 }
 // Detailed operating bridges are optional, with explicit ownership of revenue/capex.
 if(['IT Services','Renewable Power'].includes(m.name)){
  input(s,112,'Detailed operating bridge (0 off / 1 on)',0,'0');s.getRange('D112').dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:1},errorAlert:{style:'stop',title:'Choose 0 or 1',message:'0 uses scale growth; 1 uses the detailed operating bridge.'}};
  band(s,150,'DETAILED OPERATING BRIDGE INPUTS');
  const annual=(r,label,v,format)=>{val(s,`C${r}`,label);s.getRange(`E${r}:I${r}`).values=[[v,v,v,v,v]];s.getRange(`E${r}:I${r}`).setNumberFormat(format||num);s.getRange(`E${r}:I${r}`).format={fill:'#FFF2CC',font:{color:'#0000FF'}};};
  band(s,159,'DETAILED OPERATING BRIDGE');
  if(m.name==='IT Services'){
   annual(151,'Gross delivery FTE hires',1500);annual(152,'Delivery FTE attrition',.10,'0.0%');annual(153,'Offshore share of billable FTE',.8,'0.0%');annual(154,'Onsite billing / offshore billing multiple',2,'0.0"x"');
   row(s,160,'Opening delivery FTE',C.map((c,i)=>i?`${C[i-1]}163`:'$D$10'));
   row(s,161,'Delivery FTE hires',C.map(c=>`${c}151`));row(s,162,'Delivery FTE exits',C.map(c=>`${c}160*${c}152`));
   row(s,163,'Closing delivery FTE',C.map(c=>`${c}160+${c}161-${c}162`));row(s,164,'Average delivery FTE in service',C.map(c=>`(${c}160+${c}163)/2`));
   row(s,165,'Offshore billable FTE',C.map(c=>`${c}164*${c}20*${c}153`));row(s,166,'Onsite billable FTE',C.map(c=>`${c}164*${c}20*(1-${c}153)`));
   row(s,167,'Offshore annual billing (INR lakh)',C.map(c=>`${c}45`));row(s,168,'Onsite annual billing (INR lakh)',C.map(c=>`${c}167*${c}154`));row(s,169,'Delivery bridge revenue',C.map(c=>`(${c}165*${c}167+${c}166*${c}168)*'Controls'!$E$15/'Controls'!$E$9`));
   C.forEach(c=>{formula(s,`${c}44`,`IF($D$112=1,${c}164,${cells[c+'44'].f})`);formula(s,`${c}47`,`IF($D$112=1,${c}169,${cells[c+'47'].f})`);});
   val(s,'K151','Detailed bridge: seed FTE is opening headcount; hires and exits assumed evenly through the year.');
  }else{
   annual(151,'New commissioned capacity (MW)',180);annual(152,'Commissioned capacity operating-year fraction',.5,'0.0%');annual(153,'Construction cash cost per new MW (INR crore)',4);annual(154,'Maintenance capex / revenue',.02,'0.0%');
   row(s,160,'Opening operational capacity (MW)',C.map((c,i)=>i?`${C[i-1]}162`:'$D$10'));row(s,161,'Commissioned capacity (MW)',C.map(c=>`${c}151`));row(s,162,'Closing operational capacity (MW)',C.map(c=>`${c}160+${c}161`));row(s,163,'Time-weighted operational capacity (MW)',C.map(c=>`${c}160+${c}161*${c}152`));row(s,164,'Construction cash expenditure',C.map(c=>`${c}151*${c}153`));row(s,165,'Maintenance capital expenditure',C.map(c=>`${c}47*${c}154`));row(s,166,'Total capacity-linked capital expenditure',C.map(c=>`${c}164+${c}165`));
   row(s,167,'Cash available for debt service after all capex',C.map(c=>`${c}52-${c}57-${c}64-${c}65`));row(s,168,'Interest plus scheduled principal',C.map(c=>`${c}125+${c}122`));row(s,169,'DSCR after all capex (n/a if no debt service)',C.map(c=>`IF(${c}168=0,"n/a",${c}167/${c}168)`),'0.00"x"');
   C.forEach(c=>{formula(s,`${c}44`,`IF($D$112=1,${c}163,${cells[c+'44'].f})`);formula(s,`${c}65`,`IF($D$112=1,${c}166,${cells[c+'65'].f})`);});
   val(s,'K151','Detailed bridge assumes construction payments in the commissioning year. DSCR includes all capex; lender covenant definitions can differ.');
  }
 }
 if(m.name==='Real Estate'){
  band(s,159,'PROJECT COLLECTIONS AND COST ROLLFORWARD');
  row(s,160,'Opening sold but unrecognized project value',C.map((c,i)=>i?`${C[i-1]}164`:'$D$12'));row(s,161,'New project sales booked',C.map(c=>`${c}42`));row(s,162,'Opening sold value recognized',C.map(c=>`${c}160*${c}28`));row(s,163,'New sales collections',C.map(c=>`${c}161*${c}29`));row(s,164,'Closing sold but unrecognized project value',C.map(c=>`${c}160+${c}161-${c}162`));row(s,165,'Opening backlog collections',C.map(c=>`${c}160*${c}30`));row(s,166,'Total project collections',C.map(c=>`${c}163+${c}165`));row(s,167,'Project cash construction and land cost',C.map(c=>`${c}161*${c}32`));
  C.forEach(c=>{formula(s,`${c}43`,`${c}162`);formula(s,`${c}44`,`${c}164`);formula(s,`${c}45`,`${c}166`);formula(s,`${c}47`,`${c}167`);});
  val(s,'K160','Aggregate project portfolio rollforward, not a project-by-project construction model. Recognition requires company-specific accounting review.');
 }
 // Independent case inputs for each formerly shared annual driver.
 let r=400;band(s,398,'SCENARIO ASSUMPTIONS');
 const shared=m.inputs.filter(x=>!x.seed&&!x.case).map(x=>({...x,values:C.map(c=>cells[c+x.row].v)}));
 if(['IT Services','Renewable Power'].includes(m.name))for(let n=151;n<=154;n++)shared.push({row:n,label:s.getRange(`C${n}`).values[0][0],format:s.getRange(`E${n}`).format.numberFormat,values:s.getRange(`E${n}:I${n}`).values[0]});
 for(const x of shared){
  val(s,`C${r}`,x.label+' — active');
  C.forEach(c=>formula(s,`${c}${r}`,`IF(COUNT(CHOOSE('Controls'!$E$5,${c}${r+1},${c}${r+2},${c}${r+3}))=1,CHOOSE('Controls'!$E$5,${c}${r+1},${c}${r+2},${c}${r+3}),NA())`));
  for(let k=1;k<=3;k++){val(s,`C${r+k}`,cases[k-1]);s.getRange(`E${r+k}:I${r+k}`).values=[x.values];}
  s.getRange(`E${r}:I${r+3}`).setNumberFormat(typeof x.format==='string'?x.format:cells[`E${x.row}`]?.z||num);
  s.getRange(`E${r+1}:I${r+3}`).format={fill:'#FFF2CC',font:{color:'#0000FF'}};
  C.forEach(c=>formula(s,`${c}${x.row}`,`${c}${r}`));r+=5;
 }
 // Excel checks for the same economically bounded inputs as the website.
 band(s,179,'MODEL CHECKS');let checkRow=180;
 for(const x of m.inputs.filter(x=>!x.case||x.case===1)){
  const label=x.label.toLowerCase();let low=0,high=null;
  if(/growth/.test(label))low=-1;
  else if(/change.*pp/.test(label)){low=-1;high=1;}
  else if(/working capital|contract asset/.test(label))continue;
  if(/utilization|occupancy|retention|payout|tax rate|recovery \/|write-offs \/|completed \/ recognized|collection \/|d&a \//.test(label))high=1;
  const active=x.case?x.row-1:x.row;
  row(s,checkRow++,x.label+' input outside bounds',C.map(c=>{const a=x.seed?x.refs[0]:c+active;return `IF(COUNT(${a})=0,1,IF(${a}<${low},1,${high===null?'0':`IF(${a}>${high},1,0)`}))`;}),'0');
 }
 if(op){const w=inp('WACC'),g=inp('Terminal growth'),ri=inp('Terminal incremental ROIC');row(s,checkRow++,'Terminal valuation assumptions invalid',C.map(()=>`IF(${w}<=${g},1,IF(${ri}<=0,1,IF(${g}>${ri},1,0)))`),'0');}
 const addedChecks=checkRow-1;
 s.getRange(`E180:I${addedChecks}`).conditionalFormats.add('cellIs',{operator:'notEqual',formula:0,format:{fill:'#FCE4D6',font:{color:'#A52828'}}});
 // Client-facing summary and genuine historical input area (never fabricated).
 s.getRange('M2:V90').format.font={name:'Arial',size:10,color:'#000000'};s.getRange('M2:M90').format.columnWidth=35;s.getRange('N2:U90').format.columnWidth=15;s.getRange('V2:V90').format.columnWidth=45;
 s.getRange('M2:U2').merge();val(s,'M2',m.name+' | Client summary');s.getRange('M2:U2').format={fill:'#19354D',font:{bold:true,color:'#FFFFFF',size:16},rowHeight:32};
 val(s,'M4','Company / model name');val(s,'N4','Illustrative company');val(s,'M5','Valuation date');formula(s,'N5',"'Controls'!E18");s.getRange('N5').setNumberFormat('dd-mmm-yyyy');
 val(s,'M6','Selected case');formula(s,'N6',"'Controls'!E6");
 val(s,'M8','Equity value (INR crore)');formula(s,'N8',m.summary.value);s.getRange('N8').setNumberFormat(num);
 val(s,'M9','Review model checks before use');val(s,'M10','Illustrative inputs; replace with company evidence.');s.getRange('M9:U10').merge(true);
 const checkRefs=m.rows.filter(x=>x.section==='MODEL CHECKS').flatMap(x=>C.map(c=>c+x.row));
 formula(s,'M9',`IF(MAX(${checkRefs.join(',')},E180:I${addedChecks})>0.01,"ATTENTION: model checks contain exceptions",IF(MIN(${checkRefs.join(',')},E180:I${addedChecks})<-0.01,"ATTENTION: model checks contain exceptions","Model checks clear; review company assumptions"))`);
 s.getRange('M30:U30').merge();val(s,'M30','Historical actuals and forecast | INR crore');s.getRange('M30:U30').format={fill:'#19354D',font:{bold:true,color:'#FFFFFF'}};
 val(s,'M32','Metric');for(let i=0;i<8;i++){const col=String.fromCharCode(78+i);formula(s,col+'32',`'Controls'!$E$17+${i-3}`);s.getRange(col+'32').setNumberFormat(i<3?'"FY"0"A"':'"FY"0"E"');}val(s,'V32','Source / reporting date');
 const selected=[['Income',m.summary.income],['Profit after tax',m.summary.profit],...['EBITDA','Closing debt','Closing cash / (funding gap)','Closing book equity','Closing equity','Operating cash flow after interest'].filter(l=>find(l)).map(l=>[l,`E${find(l)}`])];
 selected.forEach(([label,ref],i)=>{const n=33+i;val(s,`M${n}`,label);for(let j=0;j<5;j++)formula(s,`${String.fromCharCode(81+j)}${n}`,C[j]+ref.replace(/^[A-Z]+/,''));s.getRange(`N${n}:P${n}`).format={fill:'#FFF2CC',font:{color:'#0000FF'}};s.getRange(`N${n}:U${n}`).setNumberFormat(num);metadata[m.name].history.push({label,row:n,refs:['N','O','P'].map(c=>c+n),forecastRefs:C.map(c=>c+ref.replace(/^[A-Z]+/,'')),sourceRef:'V'+n});});
 val(s,'M43','Actuals are reference inputs. Calibrate the opening balances and forecast assumptions separately.');s.getRange('M43:U44').merge();s.getRange('M43:U44').format.wrapText=true;
 // Compact chart source table with formula-backed periods and two comparable series.
 s.getRange('X2:Z2').values=[['Forecast year','Income','Profit after tax']];for(let i=0;i<5;i++){formula(s,`X${i+3}`,`'Controls'!$E$17+${i}`);formula(s,`Y${i+3}`,C[i]+m.summary.income.slice(1));formula(s,`Z${i+3}`,C[i]+m.summary.profit.slice(1));}
 const chart=s.charts.add('line',s.getRange('X2:Z7'));chart.title='Income and profit after tax (INR crore)';chart.setPosition('M12','U28');chart.titleTextStyle.fontSize=13;chart.titleTextStyle.typeface='Arial';chart.xAxis={axisType:'textAxis',textStyle:{fontSize:10,typeface:'Arial'}};chart.yAxis={numberFormatCode:'#,##0',numberFormatSourceLinked:false,textStyle:{fontSize:10,typeface:'Arial'}};chart.series.items.forEach((a,i)=>a.line={fill:i?'#BC6C25':'#19354D',width:2,style:'solid'});
 if(op){
  const w=inp('WACC'),g=inp('Terminal growth'),roic=inp('Terminal incremental ROIC'),fcff=find('Free cash flow to firm'),nopat=find('Unlevered operating profit after tax'),ebitda=find('EBITDA'),rev=find('Revenue'),multiple=inp('Forward EV / EBITDA'),openingDebt=inp('Opening debt'),cash=inp('Opening cash');
  const grid=(start,label,heads,side,fn)=>{val(s,`M${start}`,label);s.getRange(`M${start}:R${start}`).merge();s.getRange(`M${start}:R${start}`).format={fill:'#19354D',font:{bold:true,color:'#FFFFFF'},rowHeight:25};['N','O','P','Q','R'].forEach((c,i)=>formula(s,`${c}${start+1}`,heads[i]));for(let i=0;i<5;i++){formula(s,`M${start+2+i}`,side[i]);['N','O','P','Q','R'].forEach(c=>formula(s,`${c}${start+2+i}`,fn(c,start+2+i,start+1)));}s.getRange(`N${start+2}:R${start+6}`).setNumberFormat(num);metadata[m.name].sensitivities.push({label,header:heads.map((_,i)=>String.fromCharCode(78+i)+(start+1)),side:side.map((_,i)=>'M'+(start+2+i)),values:side.map((_,i)=>['N','O','P','Q','R'].map(c=>c+(start+2+i)))});};
  grid(48,'DCF equity value | rows WACC / columns terminal growth',[-.01,-.005,0,.005,.01].map(d=>`$${g[0]}$${g.slice(1)}+${d}`),[-.02,-.01,0,.01,.02].map(d=>`$${w[0]}$${w.slice(1)}+${d}`),(c,r,h)=>`IF($M${r}<=${c}$${h},"n/a",IF(${c}$${h}>$${roic[0]}$${roic.slice(1)},"n/a",${C.map((cc,i)=>`${cc}${fcff}/(1+$M${r})^${i+1}`).join('+')}+I${nopat}*(1+${c}$${h})*(1-${c}$${h}/${roic})/($M${r}-${c}$${h})/(1+$M${r})^5-${openingDebt}+${cash}))`);
  s.getRange('N49:R49').setNumberFormat('0.0%');s.getRange('M50:M54').setNumberFormat('0.0%');
  grid(58,'Forward equity value | rows EBITDA / columns EV/EBITDA',[-2,-1,0,1,2].map(d=>`MAX(0,${multiple}+${d})`),[.8,.9,1,1.1,1.2].map(d=>`E${ebitda}*${d}`),(c,r,h)=>`$M${r}*${c}$${h}-${openingDebt}+${cash}`);s.getRange('N59:R59').setNumberFormat('0.0"x"');s.getRange('M60:M64').setNumberFormat(num);
  grid(68,'First-year EBITDA | rows revenue / columns EBITDA margin',[-.04,-.02,0,.02,.04].map(d=>`E${ebitda}/E${rev}+${d}`),[.8,.9,1,1.1,1.2].map(d=>`E${rev}*${d}`),(c,r,h)=>`$M${r}*${c}$${h}`);s.getRange('N69:R69').setNumberFormat('0.0%');s.getRange('M70:M74').setNumberFormat(num);
 }
 console.log('Upgraded '+m.name);
}
wb.recalculate();
console.log((await wb.inspect({kind:'region',sheetId:'IT Services',range:'M48:R54',maxChars:2000})).ndjson);
for(const name of catalog.models.map(m=>m.name)){const p=await wb.render({sheetName:name,range:'M2:U44',scale:1,format:'png'});await fs.writeFile(`${outDir}/${name.replaceAll(' ','-')}.png`,new Uint8Array(await p.arrayBuffer()));}
await fs.writeFile(`${outDir}/metadata.json`,JSON.stringify(metadata));
await (await SpreadsheetFile.exportXlsx(wb)).save(`${outDir}/AGI_Model_Library.xlsx`);
console.log('Workbook exported');
