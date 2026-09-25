import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import XLSX from 'xlsx';
import {createModelCalculator,modelInputErrors} from './financialModelEngine.js';
import {exportCurrentModel} from './financialModelExport.js';
const catalog=JSON.parse(fs.readFileSync(new URL('../../server/assets/financial-models/financialModels.json',import.meta.url)));
test('browser calculations match every reviewed workbook formula',()=>{
 const calc=createModelCalculator(catalog);let checked=0;
 for(const model of catalog.models)for(const[ref,cell]of Object.entries(catalog.sheets[model.name]))if(cell.f){const value=calc.cell(model.name,ref);if(typeof cell.v==='number')assert.ok(Math.abs(value-cell.v)<=Math.max(1,Math.abs(cell.v))*1e-10,`${model.name}!${ref}`);else assert.equal(value,cell.v);checked++;}
 assert.ok(checked>3000);
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
