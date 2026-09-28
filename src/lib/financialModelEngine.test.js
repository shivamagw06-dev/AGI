import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import XLSX from 'xlsx';
import {createModelCalculator,modelInputErrors,modelHealth} from './financialModelEngine.js';
import {unzipSync,strFromU8} from 'fflate';
import {exportCurrentModel} from './financialModelExport.js';
const catalog=JSON.parse(fs.readFileSync(new URL('../../server/assets/financial-models/financialModels.json',import.meta.url)));
test('browser calculations match every reviewed workbook formula',()=>{
 const calc=createModelCalculator(catalog);let checked=0;
 for(const model of catalog.models)for(const[ref,cell]of Object.entries(catalog.sheets[model.name]))if(cell.f){const value=calc.cell(model.name,ref);if(typeof cell.v==='number')assert.ok(Math.abs(value-cell.v)<=Math.max(1,Math.abs(cell.v))*1e-10,`${model.name}!${ref}`);else assert.equal(value,cell.v);checked++;}
 assert.ok(checked>3000);
});
test('growth floors, genuine loss ratios and repayment shortfalls are distinguished',async()=>{
 const m=catalog.models[0],growth=m.inputs.find(r=>r.case===1&&/Operating scale growth/.test(r.label));
 assert.match(modelInputErrors(m,catalog,{[m.name]:{[growth.refs[0]]:-1.5}},1).join(),/−100%/);
 assert.equal(modelInputErrors(m,catalog,{[m.name]:{[growth.refs[0]]:-1}},1).length,0);
 const insurance=catalog.models.find(m=>m.name==='General Insurance'),claims=insurance.inputs.find(r=>r.case===1&&r.label.startsWith('Incurred claims'));
 assert.equal(modelInputErrors(insurance,catalog,{[insurance.name]:{[claims.refs[0]]:1.1}},1).length,0);
 const repayment=m.inputs.find(r=>r.case===1&&/principal repayment/i.test(r.label));const bad={[m.name]:{[repayment.refs[0]]:200}};
 assert.match(modelHealth(m,catalog,bad,1).join(),/Debt below zero/);
 await assert.rejects(()=>exportCurrentModel(new Uint8Array(),catalog,m,1,bad),/Debt below zero/);
});
test('supporting schedules own interest, capex depreciation and cash tax',()=>{
 const m=catalog.models[0],base=createModelCalculator(catalog),o={[m.name]:{D114:.5,D115:.5,D116:1000}},calc=createModelCalculator(catalog,1,o);
 assert.ok(calc.cell(m.name,'E53')>base.cell(m.name,'E53'));
 assert.equal(calc.cell(m.name,'E55'),calc.cell(m.name,'E124')*calc.cell(m.name,'E29'));
 assert.ok(calc.cell(m.name,'E57')<base.cell(m.name,'E57'));
 assert.ok(Math.abs(calc.cell(m.name,'E99'))<1e-7);
 for(const name of ['IT Services','Renewable Power']){const c=createModelCalculator(catalog,1,{[name]:{D112:1}});for(const col of ['E','F','G','H','I'])assert.ok(Math.abs(c.cell(name,col+'99'))<1e-7);}
});
test('sensitivity centers reconcile to the underlying model and dates roll consistently',()=>{
 for(const m of catalog.models.filter(m=>m.sensitivities?.length)){const calc=createModelCalculator(catalog);assert.ok(Math.abs(calc.cell(m.name,'P52')-calc.cell(m.name,m.summary.value))<1e-7,m.name);}
 const calc=createModelCalculator(catalog,1,{Controls:{E17:2029}});assert.equal(calc.cell('Controls','E18'),(Date.UTC(2028,2,31)-Date.UTC(1899,11,30))/86400000);assert.equal(calc.cell('IT Services','E7'),2029);
});
test('export preserves charts, dates, history, literal source text and formula caches',async()=>{
 const m=catalog.models[0],bytes=fs.readFileSync(new URL('../../server/assets/financial-models/Indian_Sector_Financial_Model_Library.xlsx',import.meta.url));
 const overrides={Controls:{E17:2028},[m.name]:{N4:'Client A',N33:4500,V33:'=not a formula & source <2025>'}};
 const out=await exportCurrentModel(bytes,catalog,m,1,overrides),raw=new Uint8Array(await out.arrayBuffer()),book=XLSX.read(raw,{type:'array'}),zip=unzipSync(raw);
 assert.equal(book.Sheets[m.name].N33.v,4500);assert.equal(book.Sheets[m.name].V33.v,'=not a formula & source <2025>');assert.equal(book.Sheets[m.name].V33.f,undefined);assert.equal(book.Sheets[m.name].E7.v,2028);
 const chart=Object.keys(zip).filter(k=>/\/charts\//.test(k)).map(k=>strFromU8(zip[k])).find(s=>s.includes("'IT Services'"));assert.ok(chart.includes('ptCount val="5"'));assert.ok(chart.includes('c:lineChart'));
 assert.ok(Object.keys(zip).filter(k=>/worksheets\/sheet/.test(k)).some(k=>strFromU8(zip[k]).includes('dataValidation')));
});
test('all scenarios reconcile independently for every sector',()=>{
 for(const scenario of [1,2,3]){const calc=createModelCalculator(catalog,scenario);for(const model of catalog.models){const check=model.rows.find(r=>r.label.startsWith('Assets less'));assert.ok(check,model.name);for(const c of ['E','F','G','H','I'])assert.ok(Math.abs(calc.cell(model.name,`${c}${check.row}`))<1e-7,`${model.name} scenario ${scenario}`);}}
});
test('scenario, annual edits, missing values and zero remain distinct',()=>{
 const m=catalog.models[0];const driver=m.inputs.find(r=>r.case===1);const down=m.inputs.find(r=>r.case===2);const baseline=createModelCalculator(catalog).cell(m.name,m.summary.income);
 assert.ok(createModelCalculator(catalog,2).cell(m.name,m.summary.income)<baseline);assert.ok(createModelCalculator(catalog,3).cell(m.name,m.summary.income)>baseline);
 const change={[m.name]:{[driver.refs[4]]:.3}};const calc=createModelCalculator(catalog,1,change);assert.equal(calc.cell(m.name,m.summary.income),baseline);assert.ok(calc.cell(m.name,m.summary.income.replace('E','I'))>createModelCalculator(catalog).cell(m.name,m.summary.income.replace('E','I')));
 const missing={[m.name]:{[down.refs[0]]:null}};assert.equal(createModelCalculator(catalog,1,missing).cell(m.name,m.summary.income),baseline);assert.ok(createModelCalculator(catalog,2,missing).safe(m.name,m.summary.income).error);
 assert.ok(Number.isFinite(createModelCalculator(catalog,1,{[m.name]:{[driver.refs[0]]:0}}).cell(m.name,m.summary.income)));
 assert.ok(modelInputErrors(m,catalog,{[m.name]:{[driver.refs[0]]:null}},1).length);assert.equal(modelInputErrors(m,catalog,missing,1).length,0);
});
test('invalid discount rate and zero denominators expose errors',()=>{
 const m=catalog.models[0],wacc=m.inputs.find(r=>r.label==='WACC'),g=m.inputs.find(r=>r.label==='Terminal growth');
 assert.ok(createModelCalculator(catalog,1,{[m.name]:{[wacc.refs[0]]:.02,[g.refs[0]]:.04}}).safe(m.name,m.summary.value).error);
});
test('customized Excel preserves formula inputs and has no links to removed sector sheets',async()=>{
 const bytes=fs.readFileSync(new URL('../../server/assets/financial-models/Indian_Sector_Financial_Model_Library.xlsx',import.meta.url));
 for(const name of ['IT Services','Banking','General Insurance','Real Estate']){const m=catalog.models.find(m=>m.name===name);const driver=m.inputs.find(r=>r.case===1);const overrides={[name]:{[driver.refs[0]]:.16}};const calc=createModelCalculator(catalog,1,overrides);const blob=await exportCurrentModel(bytes,catalog,m,1,overrides);const out=XLSX.read(await blob.arrayBuffer(),{type:'array'});assert.deepEqual(out.SheetNames,['Controls',name,'KPI Guide','ReadMe']);assert.equal(out.Sheets[name][driver.refs[0]].v,.16);assert.ok(out.Sheets[name][m.summary.income].f);assert.ok(Math.abs(out.Sheets[name][m.summary.income].v-calc.cell(name,m.summary.income))<1e-8);for(const sheet of Object.values(out.Sheets))for(const cell of Object.values(sheet)){if(!cell?.f)continue;for(const match of cell.f.matchAll(/'([^']+)'!/g))assert.ok(out.SheetNames.includes(match[1]),match[1]);}}
});
