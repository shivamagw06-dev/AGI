// Stored marks remain the positive underlying basket index. Short research is
// a fixed-notional price-only P&L proxy, NOT a tradable short fund NAV.
export function convictionView(portfolio, baseline, daily, tracking) {
 if (!portfolio.conviction) return tracking;
 const short=(baseline?.direction||portfolio.direction)==='short';
 const transform=nav=>short?200-nav:nav;
 const history=tracking.history.map(h=>({...h,nav:transform(h.nav)}));
 const last=history.at(-1), prior=history.at(-2);
 const categories=(baseline?.categories||portfolio.categories).map(c=>{
  const categoryHistory=[];
  if(baseline) for(const day of daily.filter(d=>d.session_date>=baseline.startedAt.slice(0,10)).sort((a,b)=>a.session_date.localeCompare(b.session_date))){
   let nav=0,complete=true;
   for(const h of c.holdings){
    const b=baseline.holdings.find(x=>x.symbol===h.symbol),q=day.prices[h.symbol];
    if(!b?.basePrice||!(q?.price>0)||q.instrumentKey!==b.instrumentKey){complete=false;break;}
    nav+=h.weight*q.price/b.basePrice;
   }
   if(complete)categoryHistory.push({date:day.session_date,nav:transform(nav)});
  }
  const latest=categoryHistory.at(-1);
  return {...c,history:categoryHistory,nav:latest?.nav??null,returnPct:latest?latest.nav-100:null,priceDate:latest?.date??null};
 });
 return {...tracking,history,categories,nav:last?.nav??null,returnPct:last?last.nav-100:null,
  dayReturnPct:last?(short?last.nav-(prior?.nav??100):(last.nav/(prior?.nav??100)-1)*100):null,
  returnMethod:short?'theoretical_fixed_notional_short':'long_price_return',
  positions:tracking.positions.map(h=>({...h,strategyReturnPct:h.returnPct==null?null:(short?-h.returnPct:h.returnPct)}))};
}
