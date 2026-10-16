import {nseSession} from './liveAlphaSession.js';
import {createSupabaseAdmin} from '../lib/supabaseAdmin.js';
import {allocate,advanceLedger,validPrices,valueAccount,clone} from './portfolioRebalanceMath.js';
import {validatePortfolio,publicDocument} from './portfolioCatalog.js';
import {usaHistory,completedUSDate} from './usaPortfolioHistory.js';
import {createIndiaDailyReader,completedDates} from './indiaPortfolioDaily.js';
import {loadUpstoxNseIsinMap} from './companyIsinBackfill.js';
const TABLE='agi_portfolio_ledger';
const day=(date,market)=>new Intl.DateTimeFormat('en-CA',{timeZone:market==='india'?'Asia/Kolkata':'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);
const fail=(message,status=409)=>Object.assign(Error(message),{status});
export function validateSchedule(portfolio,input,now=new Date()){
 const effectiveDate=input.effectiveDate;
 if(!/^\d{4}-\d{2}-\d{2}$/.test(effectiveDate||'')||new Date(effectiveDate+'T00:00:00Z').toISOString().slice(0,10)!==effectiveDate||effectiveDate<=day(now,portfolio.market))throw fail('Choose a future market date; backdating and same-day changes are not allowed.',400);
 if(portfolio.market==='india'&&!nseSession(new Date(effectiveDate+'T06:00:00Z')))throw fail('Choose an NSE trading session.',400);
 if([0,6].includes(new Date(effectiveDate+'T12:00:00Z').getUTCDay()))throw fail('Choose a weekday. Execution still requires actual market-session prices.',400);
 const feeBps=Number(input.feeBps);
 if(!Number.isFinite(feeBps)||feeBps<0||feeBps>100)throw fail('Enter model trading costs from 0 to 100 basis points.',400);
 const reason=String(input.reason||'').trim();if(reason.length<8||reason.length>2000)throw fail('Add a rebalance reason (8–2000 characters).',400);
 const clean=validatePortfolio({...portfolio,...input.target,market:portfolio.market,asOf:effectiveDate,incomplete:false},{preserveWeightPrecision:true});
 let target={...portfolio,...clean};
 target.holdings=target.holdings.map(h=>({...portfolio.holdings.find(x=>x.symbol===h.symbol),...h}));
 if(target.holdings.some(h=>!h.symbol))throw fail('Every holding needs a verified symbol.',400);
 if(portfolio.conviction){
  const categories=input.target?.categories;
  if(!Array.isArray(categories)||categories.length!==portfolio.categories.length)throw fail('Retain all factor categories.',400);
  const seen=new Set(),combined=new Map();
  target.categories=categories.map(c=>{
   const old=portfolio.categories.find(x=>x.name===c.name);if(!old||seen.has(c.name))throw fail('Invalid category.',400);seen.add(c.name);
   const validated=validatePortfolio({...portfolio,asOf:effectiveDate,cashWeight:0,incomplete:false,holdings:c.holdings},{preserveWeightPrecision:true});
   const total=validated.holdings.reduce((s,h)=>s+h.weight,0);
   const holdings=validated.holdings.map(h=>({...h,weight:h.weight/total*100}));
   for(const h of holdings){const existing=combined.get(h.symbol);combined.set(h.symbol,{...h,weight:(existing?.weight||0)+h.weight*old.weight/100,factors:[...(existing?.factors||[]),c.name]});}
   return {...old,holdings};
  });
  target.holdings=[...combined.values()];target.cashWeight=0;
 }
 return {effectiveDate,feeBps,reason,target};
}
async function rows(client,table){const all=[];for(let offset=0;;offset+=500){const {data,error}=await client.from(table).select('*').order(table===TABLE?'portfolio_id':table==='agi_india_daily_prices'?'session_date':table==='agi_india_portfolio_marks'?'session_date':'id').range(offset,offset+499);if(error)throw error;all.push(...data);if(data.length<500)return all;}}
function usPrices(data,holdings,date){const prices={};for(const h of holdings){const symbol=h.symbol.replace('BRK.B','BRK-B'),s=data.securities[symbol],b=s?.bars?.find(b=>b[0]===date);if(s?.status==='ok'&&s.currency==='USD'&&b?.[1]>0)prices[h.symbol]={price:b[1],source:'Yahoo adjusted close',date};}return prices;}
export function createRebalanceLedger({client=createSupabaseAdmin(),now=()=>new Date(),history=usaHistory,readDaily=createIndiaDailyReader(),master=()=>loadUpstoxNseIsinMap({instrumentTypes:['EQ','BE','ETF']})}={}){
 const get=async id=>{const {data,error}=await client.from(TABLE).select('*').eq('portfolio_id',id).maybeSingle();if(error)throw error;return data;};
 const write=async(row,document)=>{const {data,error}=await client.from(TABLE).update({document,revision:row.revision+1,updated_at:now().toISOString()}).eq('portfolio_id',row.portfolio_id).eq('revision',row.revision).select('*').maybeSingle();if(error)throw error;if(!data)throw fail('Portfolio updated concurrently. Reload and try again.');return data;};
 async function seed(p){
  if(await get(p.id))return;
  const stamp=now().toISOString();let account,marks,lastDate,startedAt,categories=[],basis;
  if(p.market==='india'){
   const {data:b,error}=await client.from('agi_india_portfolio_tracking').select('*').eq('portfolio_id',p.id).maybeSingle();if(error)throw error;if(!b)return;
   const base=b.baseline,prices=Object.fromEntries(base.holdings.map(h=>[h.symbol,{price:h.basePrice,instrumentKey:h.instrumentKey}]));
   const direction=base.direction||p.direction||'long';
   account=allocate({...p,holdings:base.holdings,cashWeight:base.cashWeight},100,prices,direction);
   p={...p,holdings:base.holdings.map(({basePrice,baseTime,...h})=>h),categories:base.categories||p.categories};
   const {data:m,error:me}=await client.from('agi_india_portfolio_marks').select('*').eq('portfolio_id',p.id).eq('valuation_method','upstox_daily').order('session_date');if(me)throw me;
   marks=m.map(x=>({date:x.session_date,nav:direction==='short'?200-x.nav:x.nav,recordedAt:x.marked_at}));
   const daily=await rows(client,'agi_india_daily_prices');
   marks=marks.map(m=>({...m,prices:daily.find(d=>d.session_date===m.date)?.prices||{}}));
   for(const c of base.categories||[]){const ac=allocate({holdings:c.holdings.map(h=>({...h,instrumentKey:base.holdings.find(x=>x.symbol===h.symbol)?.instrumentKey}))},100,prices,direction);categories.push({...c,account:ac,history:daily.filter(x=>x.session_date>=base.startedAt.slice(0,10)).map(x=>({date:x.session_date,nav:valueAccount(ac,x.prices)})).filter(x=>x.nav!=null)});}
   startedAt=base.startedAt;lastDate=marks.at(-1)?.date||day(new Date(startedAt),'india');basis='Upstox raw closing prices; dividends and corporate actions require review';
  }else{
   const data=await history.read();
   p={...p,holdings:p.holdings.map(h=>{const mapped=data.mappings?.[h.name]?.symbol;const symbol=h.symbol?.trim().replace('BRK.B','BRK-B')||mapped;if(!symbol||(mapped&&mapped!==symbol))throw Error('Unverified opening instrument mapping');return {...h,symbol};})};
   const dates=data.calendar.filter(d=>d>='2026-09-15'&&d<=data.asOf);if(dates[0]!=='2026-09-15'||p.incomplete)return;
   const prices=usPrices(data,p.holdings,dates[0]);if(!validPrices(p.holdings,prices))return;
   account=allocate(p,100,prices);marks=[];
   for(const date of dates){const prices=usPrices(data,p.holdings,date),nav=valueAccount(account,prices);if(nav==null)return;marks.push({date,nav,recordedAt:stamp,prices,retrospective:true});}
   startedAt='2026-09-15T20:00:00Z';lastDate=dates.at(-1);basis='Yahoo adjusted-price model units; pre-ledger period is a frozen retrospective simulation';
  }
  const document={portfolio:p,direction:p.direction||'long',account,history:marks,events:[{type:'opening',recordedAt:stamp,portfolio:p,account:clone(account),basis}],categories,lastDate,startedAt,ledgerStartedAt:stamp,basis,pending:null};
  const {error}=await client.from(TABLE).insert({portfolio_id:p.id,document});if(error&&error.code!=='23505')throw error;
 }
 return {
  get, async list(){return rows(client,TABLE);},
  async initialize(){for(const row of await rows(client,'agi_portfolio_catalog')){try{await seed(publicDocument(row));}catch{console.warn('[portfolio-ledger] Baseline pending for',row.id);}}},
  async schedule(id,input,actor){
   const row=await get(id);if(!row)throw fail('Tracking baseline not ready. No holdings have changed.');
   if(row.revision!==input.ledgerRevision)throw fail('Reload the current portfolio before scheduling.');
   const s=clone(row.document);if(s.pending)throw fail('A rebalance is already pending. Cancel it before replacing it.');
   const request=validateSchedule(s.portfolio,input,now());
   if(request.target.market==='india'){
    const instruments=await master();
    for(const h of request.target.holdings){const v=instruments.get(h.symbol);if(!v?.instrument_key)throw fail(`NSE symbol ${h.symbol} could not be verified.`,400);h.instrumentKey=v.instrument_key;}
    for(const c of request.target.categories||[])for(const h of c.holdings)h.instrumentKey=request.target.holdings.find(x=>x.symbol===h.symbol)?.instrumentKey;
   }else{
    for(const h of request.target.holdings){h.symbol=h.symbol.replace('BRK.B','BRK-B');const series=await history.ensureSymbol(h.symbol);if(series?.status!=='ok'||series.currency!=='USD')throw fail(`Yahoo USD history for ${h.symbol} must be collected and verified before scheduling.`,400);}
   }
   s.pending={...request,requestedAt:now().toISOString(),requestedBy:actor,id:crypto.randomUUID()};s.events.push({...s.pending,type:'scheduled'});return write(row,s);
  },
  async cancel(id,revision,actor){const row=await get(id);if(!row||row.revision!==revision)throw fail('Reload before cancelling.');const s=clone(row.document);if(!s.pending)throw fail('No pending rebalance.');s.events.push({type:'cancelled',requestId:s.pending.id,recordedAt:now().toISOString(),actor});s.pending=null;return write(row,s);},
  async collect(){
   await this.initialize();const ledgerRows=await this.list();
   for(const symbol of new Set(ledgerRows.filter(r=>r.document.portfolio.market==='usa').flatMap(r=>[...r.document.account.holdings,...(r.document.pending?.target.holdings||[])].map(h=>h.symbol))))await history.ensureSymbol(symbol);
   const us=await history.read();
   for(let row of await this.list()){
    let s=row.document;const india=s.portfolio.market==='india';
    const dates=india?completedDates(now(),s.lastDate):us.calendar.filter(d=>d>s.lastDate&&d<=completedUSDate(now()));
    // Never silently jump over an unprocessed date outside the recovery window.
    if(india&&Date.parse(day(now(),'india'))-Date.parse(s.lastDate)>6*86400000)continue;
    for(const date of dates.filter(d=>d>s.lastDate)){
     if(s.pending&&date>s.pending.effectiveDate)break;
     const holdings=[...new Map([...s.account.holdings,...(s.pending?.effectiveDate===date?s.pending.target.holdings:[])].map(h=>[h.symbol,h])).values()];
     let prices;
     if(india){
      const {data,error}=await client.from('agi_india_daily_prices').select('prices').eq('session_date',date).maybeSingle();if(error)throw error;prices={...(data?.prices||{})};const missing=holdings.filter(h=>!validPrices([h],prices));if(missing.length)Object.assign(prices,await readDaily(date,missing));
     }else{
      prices=usPrices(us,holdings,date);
      // Adjust model units to the provider's current adjustment scale without rewriting published NAV.
      const prior=usPrices(us,s.account.holdings,s.lastDate),record=s.history.at(-1)?.prices;
      if(!record||!validPrices(s.account.holdings,prior))break;
      s=clone(s);for(const h of s.account.holdings){if(!record[h.symbol]?.price)throw Error('Missing prior adjustment anchor');const ratio=record[h.symbol].price/prior[h.symbol].price;h.units*=ratio;h.entryPrice/=ratio;}
     }
     try{const next=advanceLedger(s,date,prices,now().toISOString());row=await write(row,next);s=row.document;}catch(e){if(e.status===409)break;console.warn('[portfolio-ledger] Pending evidence for',row.portfolio_id,date);break;}
    }
   }
  }
 };
}
let instance,running=false;
export const portfolioLedger=()=>instance||=createRebalanceLedger();
export function startPortfolioLedgerScheduler(){const tick=async()=>{if(running)return;running=true;try{await portfolioLedger().collect();}catch{console.warn('[portfolio-ledger] Collection pending; existing history retained.');}finally{running=false;}};const timer=setInterval(tick,300000);timer.unref();tick();return timer;}
export function ledgerView(row){
 const s=row.document,last=s.history.at(-1),prior=s.history.at(-2),prices=last?.prices||{};
 return {id:row.portfolio_id,ledgerRevision:row.revision,portfolio:s.portfolio,basis:s.basis,startedAt:s.startedAt,ledgerStartedAt:s.ledgerStartedAt,priceDate:s.lastDate,nav:last?.nav??null,returnPct:last?last.nav-100:null,dayReturnPct:last&&prior?(last.nav/prior.nav-1)*100:null,history:s.history.map(({prices,...m})=>m),events:s.events.map(({requestedBy,actor,...e})=>e),pending:s.pending?{effectiveDate:s.pending.effectiveDate,requestedAt:s.pending.requestedAt,reason:s.pending.reason,target:s.pending.target,feeBps:s.pending.feeBps}:null,categories:s.categories.map(c=>({...c,account:undefined,nav:c.history.at(-1)?.nav??null,returnPct:c.history.length?c.history.at(-1).nav-100:null,priceDate:c.history.at(-1)?.date})),positions:s.account.holdings.map(h=>{const entryAt=s.events.filter(e=>e.type==='rebalance').at(-1)?.effectiveDate||s.startedAt;const price=prices[h.symbol]?.price??null;return {...h,entryAt,price,basePrice:h.entryPrice,priceDate:s.lastDate,returnPct:price?(price/h.entryPrice-1)*100:null,strategyReturnPct:price?(s.direction==='short'?-1:1)*(price/h.entryPrice-1)*100:null,history:s.history.filter(m=>m.date>=entryAt.slice(0,10)&&m.prices?.[h.symbol]?.price>0).map(m=>({date:m.date,price:m.prices[h.symbol].price}))};}),status:s.pending&&s.pending.effectiveDate<day(new Date(),s.portfolio.market)?'daily_pending':'daily_recorded'};
}
