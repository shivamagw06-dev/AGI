export const agiTools = [
 {name:'Financial Model Studio',category:'Productivity',path:'/financial-modeling',tag:'16 sector models · Free account',description:'Build forecasts, compare scenarios and export editable Excel models for Indian sectors.'},
 {name:'Valuation Calculator',category:'Analytics',path:'/tools/valuation',tag:'DCF · Multiples · Sensitivities',description:'Calculate enterprise and equity value from your own cash-flow assumptions.'},
 {name:'Peer Comparison',category:'Analytics',path:'/tools/peer-comparison',tag:'Growth · Returns · Valuation',description:'Compare up to six companies side by side using consistent financial inputs.'},
 {name:'Investor Holdings Explorer',category:'Analytics',path:'/institutions',tag:'India & USA · Disclosed portfolios',description:'Explore reported investor portfolios, search holdings and inspect ownership changes.'},
];
export const numeric = x => x === '' || x === null || x === undefined || !Number.isFinite(Number(x)) ? null : Number(x);
const divide=(a,b)=>a===null||b===null||b<=0?null:a/b;
export function valuation(v){
 const keys=['fcf','growth','wacc','terminal','debt','cash','shares','ebitda','multiple'];
 const n=Object.fromEntries(keys.map(k=>[k,numeric(v[k])]));
 const errors=keys.filter(k=>n[k]===null).map(k=>`Enter a valid ${k} value.`);
 if(n.growth!==null&&n.growth < -100)errors.push('Cash-flow growth cannot be below −100%.');
 if(n.wacc!==null&&n.wacc<=0)errors.push('WACC must be positive.');
 if(n.terminal!==null&&n.terminal<=-100)errors.push('Terminal growth must exceed −100%.');
 if(n.wacc!==null&&n.terminal!==null&&n.wacc<=n.terminal)errors.push('WACC must exceed terminal growth.');
 for(const k of ['debt','cash','multiple'])if(n[k]!==null&&n[k]<0)errors.push(`${k} cannot be negative.`);
 if(n.shares!==null&&n.shares<=0)errors.push('Diluted shares must be positive.');
 if(errors.length)return {errors};
 const flows=Array.from({length:5},(_,i)=>n.fcf*(1+n.growth/100)**(i+1));
 const pv=flows.map((f,i)=>f/(1+n.wacc/100)**(i+1));
 const tv=flows[4]*(1+n.terminal/100)/((n.wacc-n.terminal)/100);
 const terminalPV=tv/(1+n.wacc/100)**5;
 const ev=pv.reduce((a,b)=>a+b,0)+terminalPV,equity=ev-n.debt+n.cash;
 if(![...flows,...pv,tv,ev,equity].every(Number.isFinite))return {errors:['Assumptions produce values outside the supported range.']};
 const multipleEV=n.ebitda>0?n.ebitda*n.multiple:null;
 if(!Number.isFinite(equity/n.shares)||(multipleEV!==null&&!Number.isFinite(multipleEV-n.debt+n.cash)))return {errors:['Assumptions produce values outside the supported range.']};
 return {errors:[],flows,pv,terminalPV,ev,equity,price:equity/n.shares,multipleEV,multipleEquity:multipleEV===null?null:multipleEV-n.debt+n.cash,warning:flows[4]<=0?'Negative or zero terminal cash flow: a perpetuity valuation may not be meaningful.':equity<0?'Equity value is negative under these assumptions.':null};
}
export function peerMetrics(p){
 const n=Object.fromEntries(['revenue','priorRevenue','ebitda','profit','priorProfit','debt','cash','equity','shares','price'].map(k=>[k,numeric(p[k])]));
 const cap=n.shares>0&&n.price>=0?n.shares*n.price:null;
 const ev=cap!==null&&n.debt!==null&&n.cash!==null?cap+n.debt-n.cash:null;
 const netDebt=n.debt!==null&&n.cash!==null?n.debt-n.cash:null;
 const metrics={marketCap:cap,ev,revenueGrowth:n.revenue!==null&&n.priorRevenue>0?n.revenue/n.priorRevenue-1:null,profitGrowth:n.profit!==null&&n.priorProfit>0?n.profit/n.priorProfit-1:null,ebitdaMargin:divide(n.ebitda,n.revenue),netMargin:divide(n.profit,n.revenue),roe:divide(n.profit,n.equity),pe:divide(cap,n.profit),evEbitda:divide(ev,n.ebitda),pb:divide(cap,n.equity),netDebtEbitda:divide(netDebt,n.ebitda)};
 return Object.fromEntries(Object.entries(metrics).map(([k,v])=>[k,Number.isFinite(v)?v:null]));
}
export function csvText(rows){return rows.map(row=>row.map(v=>{let s=String(v??'');if(/^[=+@\-\t\r]/.test(s)&&!/^[-+]?\d+(\.\d+)?$/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}).join(',')).join('\r\n');}
