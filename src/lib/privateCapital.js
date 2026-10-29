export const isNumber=v=>typeof v==='number'&&Number.isFinite(v);
export const moneyUsd=v=>!isNumber(v)?'Not disclosed':v>=1000?`$${(v/1000).toLocaleString('en-US',{maximumFractionDigits:2})}bn`:`$${v.toLocaleString('en-US',{maximumFractionDigits:1})}m`;
export const percent=v=>!isNumber(v)?'—':`${v>0?'+':''}${(v*100).toFixed(1)}%`;
export const multiple=v=>!isNumber(v)?'—':`${v.toFixed(1)}×`;
export const researchDate=v=>v?new Date(v+'T00:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}):'Not recorded';
export function researchStats(companies){
 const sectors=Object.entries(companies.reduce((a,c)=>(a[c.sector]=(a[c.sector]||0)+1,a),{})).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
 return {total:companies.length,sectors,revenue:companies.filter(c=>isNumber(c.revenueInrCr)).length,valuations:companies.filter(c=>isNumber(c.valuationUsdM)).length,pipeline:companies.filter(c=>/IPO/.test(c.status)).length,fundingDates:companies.filter(c=>c.fundingDate).length};
}
export function filterCompanies(companies,{search='',sector='All sectors',status='All stages',coverage='all',saved=[]}={}){
 const q=search.trim().toLowerCase();
 return companies.filter(c=>(!q||[c.name,c.legalEntity,c.subsector,c.hq,c.sector].filter(Boolean).join(' ').toLowerCase().includes(q))&&(sector==='All sectors'||c.sector===sector)&&(status==='All stages'||(status==='IPO watch'?/IPO/.test(c.status):c.status===status))&&(coverage!=='financials'||isNumber(c.revenueInrCr))&&(coverage!=='saved'||saved.includes(c.id)));
}
export function csvCell(v){const s=String(v??'');return '"'+(/^[\s]*[=+@-]/.test(s)?"'"+s:s).replaceAll('"','""')+'"';}
