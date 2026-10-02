// Current-allocation retrospective simulation, never an actual fund track record.
export const HORIZONS = [1, 3, 6, 12];
export function monthBoundary(date, months) {
  const [y,m,d] = date.split('-').map(Number);
  const last = new Date(Date.UTC(y,m-1-months+1,0)).getUTCDate();
  return new Date(Date.UTC(y,m-1-months,Math.min(d,last))).toISOString().slice(0,10);
}
export function periodDates(data, months) {
  if (!data?.asOf || !data.calendar?.length) return null;
  const boundary = monthBoundary(data.asOf, months);
  const start = data.calendar.filter(d=>d<=boundary).at(-1);
  return start ? {start,end:data.asOf,dates:data.calendar.filter(d=>d>=start&&d<=data.asOf)} : null;
}
export function resolveHolding(data, holding) {
  // Name mappings are reviewed, never guessed from the first search hit.
  const match = data.mappings?.[holding.name];
  const symbol = holding.symbol?.trim().toUpperCase().replace('BRK.B','BRK-B');
  if (symbol && match?.symbol && symbol !== match.symbol) return {reason:'Ticker differs from reviewed mapping'};
  if (!match?.symbol) return {reason:match?.reason || 'Instrument mapping not verified'};
  const series = data.securities?.[match.symbol];
  if (!series || series.status !== 'ok') return {symbol:match.symbol,reason:series?.reason || 'History unavailable'};
  if (series.currency !== 'USD') return {symbol:match.symbol,reason:'USD series required'};
  return {symbol:match.symbol,series};
}
export function holdingReturn(data, holding, months) {
  const resolved=resolveHolding(data,holding), period=periodDates(data,months);
  if(resolved.reason) return resolved;
  if(!period) return {...resolved,reason:'Insufficient benchmark calendar'};
  const prices=new Map(resolved.series.bars.map(b=>[b[0],b[1]]));
  if(period.dates.some(d=>!Number.isFinite(prices.get(d))||prices.get(d)<=0)) return {...resolved,reason:'Missing prices or insufficient listing history',...period};
  const initial=prices.get(period.start), end=prices.get(period.end);
  return {symbol:resolved.symbol,...period,returnPct:(end/initial-1)*100,startPrice:initial,endPrice:end,values:period.dates.map(date=>({date,value:prices.get(date)/initial}))};
}
export function portfolioReturn(data, portfolio, months) {
  const positive=portfolio.holdings.filter(h=>h.weight>0);
  const total=portfolio.holdings.reduce((s,h)=>s+h.weight,0);
  const rows=portfolio.holdings.map(h=>({...h,...holdingReturn(data,h,months)}));
  const covered=rows.filter(r=>r.weight>0&&!r.reason).reduce((s,r)=>s+r.weight,0);
  const base={rows,total,covered,months,...periodDates(data,months)};
  if(portfolio.incomplete || !Number.isFinite(total) || Math.abs(total-100)>.050001) return {...base,reason:'Incomplete allocation: full-portfolio return withheld'};
  if(!positive.length || portfolio.holdings.some(h=>!Number.isFinite(h.weight)||h.weight<0)) return {...base,reason:'Invalid allocation'};
  if(rows.some(r=>r.weight>0&&r.reason)) return {...base,reason:'Missing instrument history: full-portfolio return withheld'};
  // Only tiny disclosed rounding differences are normalised; no unknown weight becomes cash.
  const valid=rows.filter(r=>r.weight>0);
  const curve=valid[0].values.map((p,i)=>({date:p.date,value:valid.reduce((s,r)=>s+(r.weight/total)*r.values[i].value,0)}));
  let peak=1, maxDrawdown=0;
  curve.forEach(p=>{peak=Math.max(peak,p.value);maxDrawdown=Math.max(maxDrawdown,1-p.value/peak);});
  return {...base,curve,returnPct:(curve.at(-1).value-1)*100,maxDrawdownPct:maxDrawdown*100,roundingNormalised:Math.abs(total-100)>1e-8};
}
