import {randomUUID,createHash} from 'node:crypto';
import {createSupabaseAdmin} from '../lib/supabaseAdmin.js';
import {createPortfolioStore} from './portfolioCatalog.js';
import {validateEnvelope,reviewPortfolios} from './researchRefreshPolicy.js';
import {latestMomentumSnapshot,parseMomentumTables,publishMomentumSnapshot} from './manualMomentumScreener.js';
import {latestLowPeSnapshot,parseLowPeTables,publishLowPeSnapshot} from './manualLowPeScreener.js';
import {latestPiotroskiSnapshot,parsePiotroskiTables,publishPiotroskiSnapshot} from './manualPiotroskiScreener.js';
import {latestCashFlowSnapshot,parseCashFlowTables,publishCashFlowSnapshot} from './manualCashFlowScreener.js';
import {latestPromoterSnapshot,parsePromoterTables,publishPromoterSnapshot} from './manualPromoterScreener.js';
const adapters={momentum:[parseMomentumTables,latestMomentumSnapshot,publishMomentumSnapshot],'low-pe':[parseLowPeTables,latestLowPeSnapshot,publishLowPeSnapshot],piotroski:[parsePiotroskiTables,latestPiotroskiSnapshot,publishPiotroskiSnapshot],'cash-flow':[parseCashFlowTables,latestCashFlowSnapshot,publishCashFlowSnapshot],'promoter-holdings':[parsePromoterTables,latestPromoterSnapshot,publishPromoterSnapshot]};
const hash=v=>createHash('sha256').update(JSON.stringify(v)).digest('hex');
export async function readApprovedFeed({env=process.env,fetcher=fetch}={}) {
 if(!env.RESEARCH_REFRESH_FEED_URL)throw Error('SOURCE_NOT_CONFIGURED: connect an approved Trendlyne export feed');
 const url=new URL(env.RESEARCH_REFRESH_FEED_URL);
 if(url.protocol!=='https:'||url.username||url.password)throw Error('Source must use HTTPS without embedded credentials');
 // URL is deployment configuration, never a request-supplied URL. Credentials never reach the UI.
 const r=await fetcher(url,{redirect:'error',signal:AbortSignal.timeout(60000),headers:{Accept:'application/json',...(env.RESEARCH_REFRESH_FEED_TOKEN?{Authorization:`Bearer ${env.RESEARCH_REFRESH_FEED_TOKEN}`}:{})}});
 if(!r.ok)throw Error(`Source unavailable (HTTP ${r.status})`);
 if(!r.headers.get('content-type')?.includes('application/json'))throw Error('Source returned a login page or non-JSON response');
 const reader=r.body.getReader();let length=0;const chunks=[];
 try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>15000000)throw Error('Source export exceeds 15 MB');chunks.push(Buffer.from(value));}}finally{await reader.cancel();}
 try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw Error('Source returned invalid JSON');}
}
export function createResearchRefreshAgent({client,engineFetch,feed=readApprovedFeed,screeners=adapters,portfolios,now=()=>new Date()}={}) {
 const db=()=>{const c=client||createSupabaseAdmin();if(!c)throw Error('Agent storage not configured');return c;};
 const rpc=async(name,args)=>{const {data,error}=await db().rpc(name,args);if(error)throw Error('Agent database migration unavailable or operation failed');return data;};
 const engine=async(path,body)=>{if(!engineFetch)throw Error('Institution service unavailable');const r=await engineFetch(path,body?{method:'POST',body,timeoutMs:60000}:{});if(r.status>=400||r.data?.ok===false)throw Error('Institution validation/publication failed');return r.data;};
 return {
  async status(){
   const c=db(),{data:state,error}=await c.from('agi_research_refresh_state').select('enabled,next_due_at,lease_until,last_report').eq('id',true).single();
   const {data:runs,error:e}=await c.from('agi_research_refresh_runs').select('*').order('started_at',{ascending:false}).limit(20);
   if(error||e)throw Error('Agent database migration not installed');
   return {state,runs,sourceConfigured:Boolean(process.env.RESEARCH_REFRESH_FEED_URL),intervalDays:15,portfolioMode:'review_only',holdingsDetailMode:'not_connected'};
  },
  async setEnabled(enabled){if(typeof enabled!=='boolean')throw Error('enabled must be boolean');const {error}=await db().from('agi_research_refresh_state').update({enabled,updated_at:now().toISOString()}).eq('id',true);if(error)throw Error('Unable to change schedule');return this.status();},
  async run({force=false}={}){
   const hour=Number(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',hour:'2-digit',hourCycle:'h23'}).format(now()));
   if(!force&&hour<17)return {status:'waiting_for_17_ist'};
   const id=randomUUID();if(!await rpc('claim_research_refresh',{p_token:id,p_force:force}))return {status:'not_due_or_running'};
   const report={id,startedAt:now().toISOString(),publications:[],portfolioReviews:[],blockers:[],status:'running'};
   try{
    const bundle=validateEnvelope(await feed(),now());report.sourceCollectedAt=bundle.collectedAt;report.sourceHash=hash(bundle);
    const prepared=[];
    // Validate every dataset and check source dates before the first public write.
    for(const s of bundle.screeners){
     const [parse,latest,publish]=screeners[s.slug],rows=parse(s.tables,s.asOf),old=await latest();
     if(rows.length!==s.expectedRows)throw Error(`${s.slug}: incomplete rows; keeping published data`);
     if(old?.as_of>s.asOf)throw Error(`${s.slug}: older than published snapshot`);
     if(old?.rows?.length&&rows.length<old.rows.length*.5)throw Error(`${s.slug}: more than half the rows disappeared; manual source review required`);
     prepared.push({s,rows,old,publish});
    }
    const institutions=[];
    for(const s of bundle.institutions){
     const body={text:s.text,country:s.country,category:s.category,asOf:s.asOf,actor:'research-refresh-agent'};
     const preview=await engine('/v1/institutions/preview',body);
     const current=await engine(`/v1/institutions?country=${s.country}&category=${s.category}`);
     if(preview.row_count!==s.expectedRows||current.asOf>s.asOf)throw Error('Institution row count or source date mismatch');
     if(current.rows?.length&&preview.row_count<current.rows.length*.5)throw Error('Institution coverage dropped by more than half');
     institutions.push({s,body,preview,current});
    }
    const catalog=portfolios?await portfolios():await createPortfolioStore(db()).list();
    report.portfolioReviews=reviewPortfolios(catalog,bundle.factorInputs,now());
    for(const {s,rows,old,publish} of prepared){
     const same=old?.as_of===s.asOf&&hash(old.rows)===hash(rows);
     const prior=new Set((old?.rows||[]).map(r=>r.isin||r.stock)),next=new Set(rows.map(r=>r.isin||r.stock));
     const result=same?old:await publish({asOf:s.asOf,rows,actorId:null});
     report.publications.push({kind:'screener',name:s.slug,status:same?'unchanged':'published',asOf:s.asOf,rowCount:rows.length,snapshotId:result.id,added:[...next].filter(k=>!prior.has(k)),removed:[...prior].filter(k=>!next.has(k))});
    }
    for(const {s,body,preview,current} of institutions){
     const same=current.asOf===s.asOf&&hash(current.rows)===hash(preview.rows);
     if(!same)await engine('/v1/institutions/publish',body);
     report.publications.push({kind:'institution_directory',name:`${s.country}:${s.category}`,status:same?'unchanged':'published',asOf:s.asOf,rowCount:preview.row_count});
    }
    report.blockers.push('Individual investor holding-detail refresh is not connected; directory updates do not refresh every underlying holding.');
    report.blockers.push('Portfolio allocations remain unchanged. Complete original factor ranking and replacement validation are required before a dated rebalance.');
    report.status='complete'; // Data-refresh cycle complete; component limitations remain explicit.
   }catch(e){report.status=report.publications.length?'partial':'blocked';report.blockers.push(String(e.message).slice(0,500));}
   report.finishedAt=now().toISOString();
   if(!await rpc('finish_research_refresh',{p_token:id,p_status:report.status,p_report:report}))throw Error('Run lost its lease; check stored report before retrying');
   return report;
  }
 };
}
let timer;
export function startResearchRefreshScheduler(agent){
 if(timer)return;
 const tick=()=>agent.run().catch(()=>console.warn('[research-refresh] Storage unavailable; existing published data retained'));
 timer=setInterval(tick,15*60000);timer.unref();tick();
}
