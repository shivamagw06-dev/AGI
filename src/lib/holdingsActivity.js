export const activityLabels={increased:'Increased holdings',reduced:'Reduced holdings',new:'New disclosure',absent:'Absent in newer table',unchanged:'Same reported quantity',rounding:'Within source rounding',unavailable:'Comparison unavailable','identity-review':'Identity review required'};
export function filterActivityStocks(stocks,managers,{query='',direction='all',entity='all'}={}){
 const term=query.trim().toLowerCase();
 return stocks.filter(s=>(direction==='all'||s.counts[direction]>0)&&(entity==='all'||(direction==='all'?s.managerIds:s.statusIds?.[direction]||[]).some(id=>managers[id]?.type===entity))&&(!term||[s.stock,s.symbol,s.id,...s.managerIds.map(id=>managers[id]?.name)].filter(Boolean).join(' ').toLowerCase().includes(term)));
}
export function activityValue(value,unit){return Number.isFinite(value)?`${value.toLocaleString('en-US',{maximumFractionDigits:4})}${unit==='ownership'?'%':''}`:'Not available';}
export function activityChange(row){
 if(row.status==='new')return 'Not reported → disclosed';
 if(row.status==='absent')return 'Previously disclosed → absent';
 if(['unavailable','identity-review'].includes(row.status))return 'Direction withheld';
 if(row.unit==='ownership')return `${row.delta>0?'+':''}${row.delta.toFixed(2)} pp${row.uncertainty?` (±${row.uncertainty.toFixed(2)} pp rounding)`:''}`;
 if(row.status==='unchanged')return '0 shares';
 return Number.isFinite(row.changePct)?`${row.changePct>0?'+':''}${row.changePct.toFixed(2)}%`:'Percentage unavailable';
}
