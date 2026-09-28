import {useState} from 'react';
import {saveModelVersion,writeModelStore} from '@/lib/financialModelStorage';

export default function FinancialModelSaves({userId,store,setStore,payload,onLoad,status}){
 const [name,setName]=useState(''),[selected,setSelected]=useState(''),[error,setError]=useState('');
 const current=store.models.find(m=>m.id===selected);
 function save(){try{const next=saveModelVersion(store,{...payload,name},selected);writeModelStore(localStorage,userId,next);setStore(next);setSelected(next.models.at(-1).id);setError('');}catch(e){setError(e.message);}}
 function backup(){const url=URL.createObjectURL(new Blob([JSON.stringify(store,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='AGI_saved_model_inputs.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 return <details className="fm-saved-models"><summary>My saved models <span>{status}</span></summary>
  <p>Private to this account on this browser. Keep an Excel copy for backup or another device. The latest draft autosaves; named models keep the last 20 saved versions.</p>
  {store.legacyDraft&&<p>An older-library draft is retained in your inputs backup. Its cell references need review before reuse.</p>}<button className="fm-button" onClick={backup}>Back up saved inputs</button>
  <div className="fm-save-controls"><label>Saved model<select value={selected} onChange={e=>{setSelected(e.target.value);setName(store.models.find(m=>m.id===e.target.value)?.name||'');}}><option value="">New model</option>{store.models.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
  <label>Company / model name<input value={name} maxLength={100} placeholder="Company name — investment case" onChange={e=>setName(e.target.value)}/></label><button className="fm-button" onClick={save}>Save version</button></div>
  {current&&<div className="fm-save-controls"><label>Restore a version<select defaultValue="" key={selected+'-'+current.versions.length} onChange={e=>{if(e.target.value==='')return;onLoad(current.versions[Number(e.target.value)]);}}><option value="">Choose version…</option>{current.versions.map((v,i)=><option key={i} value={i}>{i+1} · {new Date(v.time).toLocaleString()} · {v.sector}</option>)}</select></label><button className="fm-button" onClick={()=>{if(!window.confirm(`Remove saved model “${current.name}” from this browser?`))return;try{const next={...store,models:store.models.filter(m=>m.id!==selected)};writeModelStore(localStorage,userId,next);setStore(next);setSelected('');setName('');}catch(e){setError('Unable to update local storage.');}}}>Remove saved model</button></div>}
  {error&&<p role="alert" className="fm-error">{error}</p>}
 </details>;
}
