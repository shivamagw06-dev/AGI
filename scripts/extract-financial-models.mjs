// Refresh the browser model catalog from the reviewed Excel library.
// Usage: node scripts/extract-financial-models.mjs /absolute/path/to/library.xlsx
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import XLSX from 'xlsx';
const source=process.argv[2];
if(!source)throw new Error('Provide the reviewed Excel workbook path.');
const bytes=fs.readFileSync(source);
const book=XLSX.read(bytes,{type:'buffer',cellNF:true});
const catalog={version:1,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),years:[2027,2028,2029,2030,2031],sheets:{},models:[]};
for(const name of book.SheetNames){const cells={};for(const [address,cell] of Object.entries(book.Sheets[name])){if(address.startsWith('!'))continue;if(cell.v===undefined&&!cell.f)continue;cells[address]={v:cell.v??null,...(cell.f?{f:cell.f}:{}),z:cell.z||'General'};}catalog.sheets[name]=cells;}
const overview=catalog.sheets.Overview;
for(let r=8;r<=23;r++){
 const name=overview[`C${r}`].v,cells=catalog.sheets[name],rows=[],inputs=[];let section='',scenarioLabel='';
 const numbers=Object.keys(cells).filter(k=>/^C\d+$/.test(k)).map(k=>Number(k.slice(1))).filter(r=>r>=9).sort((a,b)=>a-b);
 for(const row of numbers){const label=cells[`C${row}`].v;const refs=['D','E','F','G','H','I'].filter(c=>cells[`${c}${row}`]!==undefined);if(!refs.length){section=label;continue;}
  const item={row,label,section,format:cells[`E${row}`]?.z||cells[`D${row}`]?.z||'General',note:cells[`K${row}`]?.v||''};
  if(label.endsWith(' — active'))scenarioLabel=label.replace(' — active','');
  const inputRefs=refs.filter(c=>typeof cells[`${c}${row}`].v==='number'&&!cells[`${c}${row}`].f);
  if(inputRefs.length){item.refs=inputRefs.map(c=>`${c}${row}`);item.seed=inputRefs[0]==='D';if(['Base','Downside','Upside'].includes(label)){item.case=['Base','Downside','Upside'].indexOf(label)+1;item.label=scenarioLabel;}inputs.push(item);}
  else if(refs.some(c=>cells[`${c}${row}`]?.f))rows.push(item);
 }
 const ref=(c)=>overview[`${c}${r}`].f.match(/!([A-Z]+\d+)/)[1];
 catalog.models.push({name,id:name.toLowerCase().replaceAll(' ','-'),inputs,rows,notes:[10,11,12,13].map(i=>cells[`K${i}`]?.v).filter(Boolean),summary:{income:ref('D'),profit:ref('F'),kpi:ref('H'),value:ref('J'),kpiLabel:overview[`I${r}`].v,valuation:overview[`K${r}`].v}});
}
// Only ship inputs and calculations used by the modelling surface.
for(const name of Object.keys(catalog.sheets))if(name!=='Controls'&&!catalog.models.some(m=>m.name===name))delete catalog.sheets[name];
fs.mkdirSync('server/assets/financial-models',{recursive:true});fs.writeFileSync('server/assets/financial-models/financialModels.json',JSON.stringify(catalog));
fs.mkdirSync('server/assets/financial-models',{recursive:true});fs.copyFileSync(source,'server/assets/financial-models/Indian_Sector_Financial_Model_Library.xlsx');
console.log(`Extracted ${catalog.models.length} sector models. Workbook checksum ${catalog.sha256}`);
