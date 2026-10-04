export const FACTORS = [
 ['momentum','Momentum','#e46b55'],['value','Value','#809b36'],
 ['growth','Growth','#8660bf'],['quality','Quality','#249ac2'],
 ['all-weather','All-Weather','#426ccd'],
];
export function startForPeriod(end, period) {
 if(period==='all')return '2010-01-01';
 const d=new Date(`${end}T00:00:00Z`);
 if(period==='30D')d.setUTCDate(d.getUTCDate()-30);
 else {
  const months={'3M':3,'6M':6,'1Y':12,'3Y':36,'5Y':60}[period];
  if(!months)throw Error('Unknown period');
  const day=d.getUTCDate();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()-months);
  const last=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate();
  d.setUTCDate(Math.min(day,last));
 }
 return d.toISOString().slice(0,10);
}
export function factorWindow(dataset,start,end) {
 if(!/^\d{4}-\d{2}-\d{2}$/.test(start)||!/^\d{4}-\d{2}-\d{2}$/.test(end)||start>=end) return {error:'Choose a start date before the end date.',points:[]};
 if(start<dataset.baselineDate||end>dataset.asOf)return {error:'Choose dates within the available workbook history.',points:[]};
 // Baseline is the last available observation on/before the selected start.
 const prior=dataset.rows.filter(r=>r[0]<=start).at(-1)?.[0]||dataset.baselineDate;
 const selected=dataset.rows.filter(r=>r[0]>start&&r[0]<=end);
 if(!selected.length)return {error:'No source observations in this period.',points:[]};
 const levels=dataset.keys.map(()=>100);
 const point=date=>Object.fromEntries([['date',date],...dataset.keys.map((k,i)=>[k,levels[i]])]);
 const points=[point(prior)];
 for(const r of selected){dataset.keys.forEach((_,i)=>{levels[i]*=1+r[i+1];});points.push(point(r[0]));}
 return {points,start:prior,end:selected.at(-1)[0],returns:Object.fromEntries(dataset.keys.map((k,i)=>[k,levels[i]-100]))};
}
