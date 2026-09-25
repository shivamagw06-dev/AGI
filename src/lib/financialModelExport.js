import * as XLSX from 'xlsx';
import {createModelCalculator,modelInputErrors} from './financialModelEngine.js';

export async function exportCurrentModel(bytes,catalog,model,scenario,overrides){
 const problems=modelInputErrors(model,catalog,overrides,scenario);if(problems.length)throw Error(problems[0]);
 // A new output workbook avoids dangling Overview / audit links to removed sectors.
 const original=XLSX.read(bytes,{type:'array',cellFormula:true,cellNF:true,cellStyles:true});
 if(!original.Sheets[model.name]||!original.Sheets.Controls)throw Error('The downloadable template does not match this model.');
 const book=XLSX.utils.book_new(),calc=createModelCalculator(catalog,scenario,overrides);
 for(const name of ['Controls',model.name]){
  const sheet=original.Sheets[name];
  for(const[address,source]of Object.entries(catalog.sheets[name])){
   if(!sheet[address])continue;
   if(source.f||name==='Controls'&&address==='E5'||Object.hasOwn(overrides[name]||{},address)){
    const {value,error}=calc.safe(name,address);if(error)throw Error(`Cannot export ${name}!${address}: ${error}`);
    const cell=sheet[address];cell.v=value;cell.t=typeof value==='number'?'n':typeof value==='boolean'?'b':'s';delete cell.w;
   }
  }
  XLSX.utils.book_append_sheet(book,sheet,name);
 }
 const guide=XLSX.utils.sheet_to_json(original.Sheets['KPI Guide'],{header:1,defval:''});
 const filtered=guide.filter((row,i)=>i<6||row[2]===model.name);const kpiSheet=XLSX.utils.aoa_to_sheet(filtered);kpiSheet['!cols']=[{wch:2},{wch:2},{wch:23},{wch:40},{wch:62},{wch:72},{wch:34}];XLSX.utils.book_append_sheet(book,kpiSheet,'KPI Guide');
 const readme=original.Sheets.ReadMe;readme.D6={t:'s',v:'Started from illustrative assumptions. This export includes user-entered changes from the website; the inputs have not been independently verified.'};delete readme.D6.w;XLSX.utils.book_append_sheet(book,readme,'ReadMe');
 book.Workbook={CalcPr:{calcMode:'auto',fullCalcOnLoad:true,forceFullCalc:true}};
 return new Blob([XLSX.write(book,{type:'array',bookType:'xlsx',compression:true})],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
}
