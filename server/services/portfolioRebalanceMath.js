// Pure, price-only model accounting. No order execution.
export const clone = x => structuredClone(x);
export function validPrices(holdings, prices) {
 return holdings.every(h => Number.isFinite(prices[h.symbol]?.price) && prices[h.symbol].price > 0 && (!h.instrumentKey || prices[h.symbol].instrumentKey === h.instrumentKey));
}
export function valueAccount(account, prices) {
 if(!validPrices(account.holdings,prices))return null;
 return account.cash + account.holdings.reduce((v,h)=>v+h.units*prices[h.symbol].price,0);
}
export function allocate(target, nav, prices, direction='long') {
 if(!(nav>0)||!validPrices(target.holdings,prices))throw Error('Complete prices and positive model equity required');
 const total=target.holdings.reduce((s,h)=>s+h.weight,Number(target.cashWeight||0));
 if(Math.abs(total-100)>.050001)throw Error('Allocation must total 100%');
 const sign=direction==='short'?-1:1;
 const holdings=target.holdings.map(h=>({...h,units:sign*nav*h.weight/total/prices[h.symbol].price,entryPrice:prices[h.symbol].price}));
 return {cash:nav-holdings.reduce((s,h)=>s+h.units*prices[h.symbol].price,0),holdings};
}
export function rebalanceAccount(account,target,prices,feeBps,direction='long') {
 const nav=valueAccount(account,prices);
 if(!(nav>0)||!validPrices(target.holdings,prices))throw Error('Rebalance requires complete prices and positive equity');
 if(!Number.isFinite(feeBps)||feeBps<0||feeBps>100)throw Error('Cost must be 0–100 basis points of traded value');
 const symbols=[...new Set([...account.holdings,...target.holdings].map(h=>h.symbol))], rate=feeBps/10000;
 const turnover=next=>symbols.reduce((s,symbol)=>s+Math.abs((next.holdings.find(h=>h.symbol===symbol)?.units||0)-(account.holdings.find(h=>h.symbol===symbol)?.units||0))*prices[symbol].price,0);
 // Solve equity + cost(equity) = pre-trade NAV, including cash and both legs.
 let lo=0,hi=nav;
 for(let i=0;i<80;i++){const mid=(lo+hi)/2,next=allocate(target,mid,prices,direction);if(mid+rate*turnover(next)>nav)hi=mid;else lo=mid;}
 const next=allocate(target,(lo+hi)/2,prices,direction), traded=turnover(next),cost=rate*traded;
 next.cash=nav-cost-next.holdings.reduce((s,h)=>s+h.units*prices[h.symbol].price,0);
 const trades=symbols.map(symbol=>({symbol,price:prices[symbol].price,units:(next.holdings.find(h=>h.symbol===symbol)?.units||0)-(account.holdings.find(h=>h.symbol===symbol)?.units||0)})).filter(t=>Math.abs(t.units)>1e-12);
 return {account:next,preNav:nav,postNav:nav-cost,cost,traded,trades};
}
export function advanceLedger(input,date,prices,recordedAt) {
 const s=clone(input);if(date<=s.lastDate)return s;
 if(s.pending&&date>s.pending.effectiveDate)throw Error('Pending rebalance date must be reconciled first');
 const nav=valueAccount(s.account,prices);if(nav==null)throw Error('Missing held-stock prices');
 if(nav<=0)throw Error('Model equity exhausted; administrator review required');
 let cost=0;
 if(s.pending?.effectiveDate===date){
  let r=rebalanceAccount(s.account,s.pending.target,prices,s.pending.feeBps,s.direction);
  const categoryChanges=[];
  if(s.categories?.length){
   for(const c of s.categories){
    const target=s.pending.target.categories?.find(t=>t.name===c.name);
    if(!target)throw Error('All existing categories must be retained');
    const cr=rebalanceAccount(c.account,{holdings:target.holdings,cashWeight:0},prices,s.pending.feeBps,s.direction);
    c.account=cr.account;c.holdings=target.holdings;c.history.push({date,nav:cr.postNav});categoryChanges.push({name:c.name,...cr});
   }
  }
  if(categoryChanges.length){
   // Rebalance within each fixed category sleeve; no hidden transfers between sleeves.
   const holdings=new Map();let cash=0,totalCost=0,totalTurnover=0;
   for(const c of s.categories){const weight=c.weight/100;cash+=c.account.cash*weight;const cr=categoryChanges.find(x=>x.name===c.name);totalCost+=cr.cost*weight;totalTurnover+=cr.traded*weight;for(const h of c.account.holdings){const old=holdings.get(h.symbol);holdings.set(h.symbol,{...h,units:(old?.units||0)+h.units*weight});}}
   r={...r,account:{cash,holdings:[...holdings.values()]},cost:totalCost,traded:totalTurnover,postNav:nav-totalCost};
   r.trades=[...new Set([...s.account.holdings,...r.account.holdings].map(h=>h.symbol))].map(symbol=>({symbol,price:prices[symbol].price,units:(r.account.holdings.find(h=>h.symbol===symbol)?.units||0)-(s.account.holdings.find(h=>h.symbol===symbol)?.units||0)}));
  }
  s.events.push({...s.pending,type:'rebalance',recordedAt,prices:clone(prices),...r,categoryChanges});
  s.account=r.account;s.portfolio=s.pending.target;s.pending=null;cost=r.cost;
 }
 for(const c of s.categories||[]){if(c.history.at(-1)?.date!==date){const n=valueAccount(c.account,prices);if(n==null)throw Error('Missing category prices');c.history.push({date,nav:n});}}
 s.history.push({date,nav:nav-cost,recordedAt,cost,prices:clone(prices)});s.lastDate=date;
 return s;
}
