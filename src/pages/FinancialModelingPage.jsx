import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useSearchParams } from 'react-router-dom';
import * as Dialog from '@radix-ui/react-dialog';
import { BarChart3, Calculator, CheckCircle2, ChevronRight, Download, FileSpreadsheet, Info, LockKeyhole, RotateCcw, SlidersHorizontal, X, AlertCircle } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip } from 'recharts';
import { useAuth } from '@/contexts/AuthContext';
import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';
import { createModelCalculator, formatModelValue as fmt, modelInputErrors } from '@/lib/financialModelEngine';
import './financialModeling.css';

const COLS=['E','F','G','H','I'];
const CASES=['Base','Downside','Upside'];
const DRAFT_KEY='agi-model-auth-return-v1';
const title=s=>s.toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());
const groups=['Operating companies','Financial institutions','Real estate'];
function readDraft(catalog){try{const raw=sessionStorage.getItem(DRAFT_KEY);sessionStorage.removeItem(DRAFT_KEY);if(!raw)return null;const d=JSON.parse(raw);return d.version===catalog.sha256&&Date.now()-d.time<60*60*1000?d:null;}catch{return null;}}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}

function ModelWorkspace({catalog}){
 const {user,loading:authLoading}=useAuth();const[params,setParams]=useSearchParams();const[draft]=useState(()=>readDraft(catalog));
 const selected=params.get('sector')||draft?.sector||'it-services';const model=catalog.models.find(m=>m.id===selected)||catalog.models[0];
 const[scenario,setScenario]=useState(draft?.scenario||1);const[overrides,setOverrides]=useState(draft?.overrides||{});const[view,setView]=useState('Forecast');const[authOpen,setAuthOpen]=useState(false);const[formulaRow,setFormulaRow]=useState(null);const[busy,setBusy]=useState('');const[message,setMessage]=useState('');const[downloadError,setDownloadError]=useState('');const[resetOpen,setResetOpen]=useState(false);
 const calc=useMemo(()=>createModelCalculator(catalog,scenario,overrides),[scenario,overrides]);
 const inputErrors=useMemo(()=>modelInputErrors(model,catalog,overrides,scenario),[model,overrides,scenario]);
 const result=ref=>calc.safe(model.name,ref);
 const rows=model.rows;const checks=rows.filter(r=>r.section==='MODEL CHECKS');
 const exceptions=checks.flatMap(r=>COLS.map(c=>({label:r.label,...result(`${c}${r.row}`)}))).filter(r=>r.error||typeof r.value==='number'&&Math.abs(r.value)>.01);
 const values=(ref)=>COLS.map(c=>result(c+ref.replace(/^[A-Z]+/,'')));
 const trend=COLS.map((c,i)=>({year:`FY${String(catalog.years[i]).slice(-2)}`,income:values(model.summary.income)[i].value,profit:values(model.summary.profit)[i].value}));
 const incomeLabel=catalog.sheets[model.name]['C'+model.summary.income.slice(1)]?.v||'Income';
 const visibleRows=rows.filter(r=>{
  if(view==='KPIs')return /KPI|RETURN METRICS/.test(r.section)&&!/(equity value|value per share)/i.test(r.label);
  if(view==='Valuation')return /VALUATION/.test(r.section)&&(/VALUATION AT/.test(r.section)||/value|per share|PV of|dividends/.test(r.label));
  if(view==='Checks')return r.section==='MODEL CHECKS';
  return !/ASSUMPTIONS|VALUATION|KPIs|RETURN METRICS|MODEL CHECKS/.test(r.section)&&!r.label.includes(' — active');
 });
 const inputs=model.inputs.filter(r=>!r.case||r.case===scenario);const inputGroups=[...new Set(inputs.map(r=>r.section))];
 function update(refs,value){setOverrides(current=>({...current,[model.name]:{...current[model.name],...Object.fromEntries(refs.map(ref=>[ref,value]))}}));setMessage('');}
 function selectSector(id){setParams({sector:id},{replace:true});setFormulaRow(null);setMessage('');setDownloadError('');}
 function prepareAuth(){try{sessionStorage.setItem(DRAFT_KEY,JSON.stringify({time:Date.now(),version:catalog.sha256,sector:model.id,scenario,overrides}));}catch{/* Browsers blocking storage can still sign in. */}}
 async function download(kind){
  setDownloadError('');setMessage('');if(!user){setAuthOpen(true);return;}
  if(kind==='model'&&inputErrors.length){setDownloadError('Complete the highlighted assumptions before exporting.');return;}
  setBusy(kind);
  try{
   const[{supabase},{default:api}]=await Promise.all([import('@/lib/supabaseClient'),import('@/config')]);
   const{data,error}=await supabase.auth.getSession();if(error)throw error;if(!data.session?.access_token){setAuthOpen(true);return;}
   const response=await fetch(`${api||''}/api/financial-models/library`,{headers:{Authorization:`Bearer ${data.session.access_token}`}});
   if(response.status===401){setAuthOpen(true);throw Error('Your session expired. Sign in again to download.');}
   if(!response.ok){const body=await response.json().catch(()=>({}));throw Error(body.error||'The download is unavailable. Please try again.');}
   const bytes=await response.arrayBuffer();
   if(kind==='library'){downloadBlob(new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}),'AGI_Indian_Sector_Model_Library.xlsx');}
   else{const {exportCurrentModel}=await import('@/lib/financialModelExport');const blob=await exportCurrentModel(bytes,catalog,model,scenario,overrides);downloadBlob(blob,`AGI_${model.id}_${CASES[scenario-1]}_Model.xlsx`);}
   setMessage(kind==='library'?'Excel library downloaded. It contains the original illustrative assumptions.':'Your model downloaded with your assumptions and editable Excel formulas.');
  }catch(error){setDownloadError(error.message||'Download failed. Please try again.');}finally{setBusy('');}
 }
 useEffect(()=>{setFormulaRow(null);},[model.id,scenario]);
 const next=encodeURIComponent(`/financial-modeling?sector=${model.id}`);
 return <div className="fm-root">
  <Helmet><title>Financial Modelling Studio | Agarwal Global Investments</title><meta name="description" content="Build sector-specific financial models, compare scenarios and download editable Excel models for 16 Indian sectors."/><link rel="canonical" href="https://agarwalglobalinvestments.com/financial-modeling"/></Helmet>
  <header className="fm-heading"><div><div className="fm-eyebrow"><Calculator size={15}/> AGI RESEARCH TOOLS</div><h1>Financial Modelling Studio</h1><p>Build your assumptions. Understand the outcome.</p></div><button className="fm-button" disabled={!!busy||authLoading} onClick={()=>download('library')}><FileSpreadsheet size={17}/>{busy==='library'?'Preparing download…':'Download Excel library'}</button></header>
  <div className="fm-layout">
   <aside className="fm-sectors" aria-label="Sector models"><div className="fm-sidebar-heading">MODEL LIBRARY <span>16</span></div>{groups.map((group,g)=><div key={group} className="fm-sector-group"><h2>{group}</h2>{catalog.models.filter((_,i)=>g===0?i<12:g===1?i>=12&&i<15:i===15).map(m=><button type="button" key={m.id} className={m.id===model.id?'active':''} aria-pressed={m.id===model.id} onClick={()=>selectSector(m.id)}>{m.name}{m.id===model.id&&<ChevronRight size={15}/>}</button>)}</div>)}<div className="fm-library-note"><FileSpreadsheet size={21}/><strong>Take your work to Excel</strong><p>Download the full library or export a model with your own assumptions.</p><span>Free AGI account required</span></div></aside>
   <main className="fm-workspace">
    <div className="fm-toolbar"><div><span className="fm-breadcrumb">Models / {model.name}</span><h2>{model.name}</h2><span className="fm-caption">FY27–FY31 · INR crore unless specified</span></div><div className="fm-toolbar-actions"><div className="fm-cases" aria-label="Scenario">{CASES.map((label,i)=><button key={label} aria-pressed={scenario===i+1} onClick={()=>setScenario(i+1)}>{label}</button>)}</div><button className="fm-button fm-primary" onClick={()=>download('model')} disabled={!!busy||authLoading||inputErrors.length>0}><Download size={16}/>{busy==='model'?'Exporting…':'Export my model'}</button></div></div>
    <div className="fm-context"><Info size={16}/><span>Illustrative starting assumptions. Replace them with your company data. Changes stay in this tab until you export.</span></div>
    {message&&<div className="fm-message" role="status"><CheckCircle2 size={16}/>{message}</div>}{downloadError&&<div className="fm-error" role="alert">{downloadError}</div>}
    <div className="fm-summary" aria-live="polite">{[{label:`FY27 ${incomeLabel.toLowerCase()}`,ref:model.summary.income},{label:'FY27 profit after tax',ref:model.summary.profit},{label:`FY27 ${model.summary.kpiLabel}`,ref:model.summary.kpi,pct:true},{label:'Illustrative equity value',ref:model.summary.value,value:true}].map(item=>{const r=result(item.ref);return <div key={item.label} className={item.value?'fm-value-card':''}><span>{item.label}</span><strong title={r.error||''}>{r.error?'Unavailable':fmt(r.value,item.pct?'0.0%':'#,##0.0')}</strong><small>{r.error?'Review assumptions':item.value?'As at 31 Mar 2026':item.pct?'Selected scenario':'₹ crore'}</small></div>;})}</div>
    <div className="fm-model-grid">
     <section className="fm-assumptions"><div className="fm-panel-title"><h3><SlidersHorizontal size={16}/> Assumptions</h3><button className="fm-icon-button" onClick={()=>setResetOpen(true)} aria-label="Reset this sector to illustrative assumptions" title="Reset assumptions"><RotateCcw size={16}/></button></div><p className="fm-caption fm-assumption-help">Edit a value for all forecast years, or open the annual inputs.</p>{inputErrors.length>0&&<div className="fm-error" role="alert">{inputErrors.slice(0,3).map(e=><p key={e}>{e}</p>)}</div>}<div className="fm-input-scroll">{inputGroups.map((group,i)=><details className="fm-input-group" key={`${model.id}-${group}`} open={i===0}><summary>{title(group).replace(' And Valuation Inputs',' & Valuation')}<span>{inputs.filter(r=>r.section===group).length}</span></summary>{inputs.filter(r=>r.section===group).map(row=><Assumption catalog={catalog} key={`${model.id}-${row.row}`} row={row} model={model} overrides={overrides} update={update}/>)}</details>)}</div></section>
     <section className="fm-results"><div className="fm-chart-panel"><div className="fm-panel-title"><div><h3>Five-year outlook</h3><span className="fm-caption">{incomeLabel} and profit after tax · ₹ crore</span></div><BarChart3 size={18}/></div><div className="fm-chart" role="img" aria-label="Five-year income and profit forecast; exact figures are available in the financial table below."><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend} margin={{left:5,right:18,top:15,bottom:0}}><defs><linearGradient id="fm-income-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1b4167" stopOpacity={.15}/><stop offset="100%" stopColor="#1b4167" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e4e9ef"/><XAxis dataKey="year" tick={{fontSize:12}} axisLine={false} tickLine={false}/><YAxis width={65} tickFormatter={v=>new Intl.NumberFormat('en-IN',{notation:'compact'}).format(v)} tick={{fontSize:12}} axisLine={false} tickLine={false}/><Tooltip formatter={(v,n)=>[fmt(v),n]} contentStyle={{border:'1px solid #dde4eb',borderRadius:8,fontSize:14}}/><Area type="monotone" dataKey="income" name={incomeLabel} stroke="#1b4167" strokeWidth={2.5} fill="url(#fm-income-fill)" isAnimationActive={false}/><Area type="monotone" dataKey="profit" name="Profit after tax" stroke="#d36a23" strokeWidth={2} fill="transparent" isAnimationActive={false}/></AreaChart></ResponsiveContainer></div><div className="fm-legend"><span><i/>{incomeLabel}</span><span><i/>Profit after tax</span></div></div>
      <div className="fm-table-panel"><div className="fm-view-buttons" aria-label="Results view">{['Forecast','KPIs','Valuation','Scenarios','Checks'].map(v=><button key={v} onClick={()=>{setView(v);setFormulaRow(null);}} aria-pressed={view===v}>{v}{v==='Checks'&&exceptions.length>0?<span className="fm-check-count">{exceptions.length}</span>:null}</button>)}</div>
      {view==='Scenarios'?<ScenarioTable catalog={catalog} model={model} overrides={overrides}/>:<><div className="fm-table-scroll"><table className="fm-table"><thead><tr><th scope="col">{view==='Valuation'?'Valuation measure':'Metric'}</th>{catalog.years.map(y=><th key={y} scope="col">FY{String(y).slice(-2)}E</th>)}</tr></thead><tbody>{visibleRows.map((row,index)=><Row catalog={catalog} key={row.row} row={row} previous={visibleRows[index-1]} model={model} calc={calc} onInspect={()=>setFormulaRow(formulaRow===row.row?null:row.row)} isCheck={view==='Checks'}/>)}</tbody></table></div>{view==='Valuation'&&<p className="fm-table-footnote">{model.summary.valuation}. Single values are measured at 31 March 2026; forward measures retain their fiscal-year columns.</p>}{view==='Checks'&&<p className="fm-table-footnote">Zero means no exception. Positive funding shortfalls require additional financing or revised assumptions.</p>}</>}
      {formulaRow&&<div className="fm-formula"><div><strong>{rows.find(r=>r.row===formulaRow)?.label}</strong><button className="fm-icon-button" onClick={()=>setFormulaRow(null)} aria-label="Close calculation details"><X size={15}/></button></div><span>Excel formula · {model.name}!E{formulaRow}</span><code>{catalog.sheets[model.name][`E${formulaRow}`]?.f||'No formula in this period'}</code>{rows.find(r=>r.row===formulaRow)?.note&&<p>{rows.find(r=>r.row===formulaRow).note}</p>}</div>}
      </div>
      <details className="fm-method"><summary><Info size={16}/> Model scope & methodology</summary>{model.notes.map((n,i)=><p key={i}>{n}</p>)}<p>Forecast years end on 31 March. Ratios use 365 days. Taxes, growth and valuation multiples are assumptions. The Excel library includes model-specific definitions and disclosure references.</p><p>These are business archetypes, not forecasts for a named company. Financial institutions use book-based valuation; operating companies use FCFF and a forward-multiple cross-check.</p></details>
     </section>
    </div>
   </main>
  </div>
  <Dialog.Root open={authOpen} onOpenChange={setAuthOpen}><Dialog.Portal><Dialog.Overlay className="fm-dialog-overlay"/><Dialog.Content className="fm-dialog"><Dialog.Close className="fm-dialog-close" aria-label="Close"><X size={20}/></Dialog.Close><div className="fm-dialog-symbol"><LockKeyhole size={24}/></div><Dialog.Title>Create your free AGI account</Dialog.Title><Dialog.Description>Sign up to download the Excel library or export your financial model. Your current assumptions will be kept in this tab while you sign in.</Dialog.Description><Link className="fm-button fm-primary" onClick={prepareAuth} to={`/login?mode=signup&next=${next}`}>Sign up to download <ChevronRight size={16}/></Link><Link className="fm-signin" onClick={prepareAuth} to={`/login?mode=signin&next=${next}`}>Already have an account? Sign in</Link></Dialog.Content></Dialog.Portal></Dialog.Root>
  <Dialog.Root open={resetOpen} onOpenChange={setResetOpen}><Dialog.Portal><Dialog.Overlay className="fm-dialog-overlay"/><Dialog.Content className="fm-dialog"><Dialog.Title>Reset {model.name}?</Dialog.Title><Dialog.Description>This restores the illustrative inputs for all three scenarios in this sector. Your other sector models stay unchanged.</Dialog.Description><div className="fm-dialog-actions"><button className="fm-button" onClick={()=>setResetOpen(false)}>Cancel</button><button className="fm-button fm-primary" onClick={()=>{setOverrides(o=>{const next={...o};delete next[model.name];return next;});setResetOpen(false);}}>Reset assumptions</button></div></Dialog.Content></Dialog.Portal></Dialog.Root>
 </div>;
}

function Assumption({catalog,row,model,overrides,update}){
 const[annual,setAnnual]=useState(false);const percent=row.format.includes('%');const value=ref=>Object.hasOwn(overrides[model.name]||{},ref)?overrides[model.name][ref]:catalog.sheets[model.name][ref].v;
 const edit=(refs,raw)=>update(refs,raw.trim()===''?null:Number(raw)/(percent?100:1));const display=ref=>{const n=value(ref);return n===null?'':Number((n*(percent?100:1)).toFixed(6));};
 const same=row.refs.every(ref=>value(ref)===value(row.refs[0]));
 const input=(ref,refs,label)=><div className="fm-number-field"><input id={`fm-input-${row.row}-${ref}`} aria-label={`${row.label}${label?' '+label:''}`} type="number" step="any" value={display(ref)} onChange={e=>edit(refs,e.target.value)} aria-invalid={value(ref)===null}/>{percent&&<span>%</span>}</div>;
 return <div className="fm-input"><div className="fm-input-label"><label htmlFor={`fm-input-${row.row}-${row.refs[0]}`}>{row.label.replace(' — seed','')}</label>{row.note&&<span title={row.note}><Info size={13}/></span>}</div>{!row.seed&&<button className="fm-year-toggle" aria-expanded={annual} onClick={()=>setAnnual(!annual)}>{annual?'Use one value':same?'Edit by year':'Values vary by year'} <ChevronRight size={11}/></button>}{annual&&!row.seed?<div className="fm-annual-inputs">{row.refs.map((ref,i)=><label key={ref}><span>FY{String(catalog.years[i]).slice(-2)}</span>{input(ref,[ref],`FY${catalog.years[i]}`)}</label>)}</div>:<>{input(row.refs[0],row.refs,row.seed?'Opening balance':'all five forecast years')}<span className="fm-input-hint">{row.seed?'Opening / valuation assumption':same?'Applies to all five years':'Editing this value will apply it to all five years'}</span></>}</div>;
}
function Row({catalog,row,previous,model,calc,onInspect,isCheck}){return <>{row.section!==previous?.section&&<tr className="fm-section-row"><th colSpan={6}>{title(row.section)}</th></tr>}<tr><th scope="row"><button className="fm-metric-button" onClick={onInspect} title="Show calculation">{row.label}<Info size={12}/></button></th>{COLS.map(c=>{const ref=`${c}${row.row}`;if(!catalog.sheets[model.name][ref])return <td key={c}>—</td>;const{value,error}=calc.safe(model.name,ref);return <td key={c} className={error||isCheck&&Math.abs(value)>.01?'fm-bad-cell':''} title={error||row.note}>{error?<span>Unavailable</span>:fmt(value,isCheck?'0.00':row.format)}</td>;})}</tr></>;}
function ScenarioTable({catalog,model,overrides}){const cases=useMemo(()=>[1,2,3].map(c=>createModelCalculator(catalog,c,overrides)),[overrides]);const metrics=[['FY27 income',model.summary.income,'#,##0.0'],['FY31 income',model.summary.income.replace(/^E/,'I'),'#,##0.0'],['FY27 profit after tax',model.summary.profit,'#,##0.0'],['FY31 profit after tax',model.summary.profit.replace(/^E/,'I'),'#,##0.0'],[`FY27 ${model.summary.kpiLabel}`,model.summary.kpi,'0.0%'],['Equity value at 31 Mar 2026',model.summary.value,'#,##0.0']];return <><div className="fm-table-scroll"><table className="fm-table"><thead><tr><th>Measure</th>{CASES.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{metrics.map(([label,ref,format])=><tr key={label}><th>{label}</th>{cases.map((calc,i)=>{const r=calc.safe(model.name,ref);return <td key={i} title={r.error||''}>{r.error?'Unavailable':fmt(r.value,format)}</td>;})}</tr>)}</tbody></table></div><p className="fm-table-footnote">Each scenario is calculated independently from its own driver assumptions. Ungrouped inputs apply to all three.</p></>;}

export default function FinancialModelingPage(){
 const {user,loading}=useAuth();const [params]=useSearchParams();
 const [state,setState]=useState({});const [attempt,setAttempt]=useState(0);
 const eligible=!!user?.id&&!user.is_anonymous&&!!user.email_confirmed_at;
 useEffect(()=>{let active=true;setState({});if(!eligible)return;
 (async()=>{try{const {data}=await supabase.auth.getSession();const response=await fetch(`${API_ORIGIN}/api/financial-models/catalog`,{headers:{Authorization:`Bearer ${data.session?.access_token||''}`},cache:'no-store'});if(!response.ok){const body=await response.json().catch(()=>({}));throw Error(body.error||'Unable to load models. Please try again.');}const catalog=await response.json();if(active)setState({catalog,userId:user.id});}catch(error){if(active)setState({error:error.message});}})();return()=>{active=false;};
 },[eligible,user?.id,attempt]);
 const next=encodeURIComponent('/financial-modeling'+(params.toString()?'?'+params.toString():''));
 if(eligible&&state.catalog&&state.userId===user.id)return <ModelWorkspace catalog={state.catalog}/>;
 return <div className="fm-page"><section style={{maxWidth:600,margin:'80px auto',padding:32,textAlign:'center'}}><LockKeyhole size={32} style={{margin:'0 auto 20px'}}/><h1>Financial Models</h1><p style={{margin:'16px 0 24px'}}>{loading?'Checking your account…':!eligible?'Create a free AGI account to build financial models across 16 Indian sectors and download editable Excel workbooks.':state.error||'Loading your model library…'}</p>{!loading&&!eligible&&<><Link className="fm-button fm-primary" to={`/login?mode=signup&next=${next}`}>Sign up for free</Link><p style={{marginTop:20}}><Link to={`/login?mode=signin&next=${next}`}>Already registered? Sign in</Link></p>{user&&!user.email_confirmed_at&&<p>Please verify your email to access the models.</p>}</>}{eligible&&state.error&&<button className="fm-button" onClick={()=>setAttempt(x=>x+1)}>Try again</button>}</section></div>;
}
