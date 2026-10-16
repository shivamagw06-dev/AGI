import { useState } from 'react';
import './investorSelector.css';
export default function InvestorSelector({investors, selected, onChange}) {
 const [search,setSearch]=useState('');
 const names=[...new Set(investors.map(x=>x.name))].sort((a,b)=>a.localeCompare(b));
 const matches=names.filter(x=>x.toLowerCase().includes(search.trim().toLowerCase()));
 const toggle=name=>onChange(selected.includes(name)?selected.filter(x=>x!==name):[...selected,name]);
 return <div className="investor-filter"><details><summary>Choose investors <span>{selected.length?`${selected.length} selected`:'All investors'}</span></summary><div className="investor-picker"><label>Find an investor<input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search investor names…"/></label><div className="investor-picker-actions"><button type="button" disabled={!matches.length} onClick={()=>onChange([...new Set([...selected,...matches])])}>Select matching</button><button type="button" onClick={()=>onChange([])}>Show all investors</button></div><fieldset><legend className="rk-sr-only">Investors to display</legend>{matches.map(name=><label key={name}><input type="checkbox" checked={selected.includes(name)} onChange={()=>toggle(name)}/><span>{name}</span></label>)}{!matches.length&&<p>No matching names.</p>}</fieldset></div></details><p>Choose one or more investors. Your selection is remembered in this browser.</p>{selected.length>0&&<div className="investor-selection" aria-label="Selected investors">{selected.map(name=><button key={name} type="button" onClick={()=>toggle(name)} aria-label={`Remove ${name}`}>{name}<span aria-hidden="true"> ×</span></button>)}<button type="button" className="investor-clear" onClick={()=>onChange([])}>Clear selection</button></div>}</div>;
}
