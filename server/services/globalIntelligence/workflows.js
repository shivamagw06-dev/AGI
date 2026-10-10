import {database,result} from './store.js';
import {matchAssets} from './model.js';
export const PUBLIC_MONITOR_FIELDS='id,symbol,title,url,status,last_attempt_at,last_success_at,last_changed_at,revision_count';
export const DEFAULT_PREFERENCES={enabled:false,observations:false,assessments:true,documents:true,enabled_at:null,last_read_at:null};
export function validatePreferences(input){
 const keys=['enabled','observations','assessments','documents'];
 if(!input||keys.some(k=>typeof input[k]!=='boolean'))throw new Error('Alert preferences must be true or false.');
 return Object.fromEntries(keys.map(k=>[k,input[k]]));
}
export async function documents({admin=false}={}){
 const [monitors,versions]=await Promise.all([
  result(database().from('gi_document_monitors').select(PUBLIC_MONITOR_FIELDS+(admin?',last_error':'')).order('symbol')),
  result(database().from('gi_document_versions').select('id,monitor_id,captured_at,baseline,added_lines,removed_lines'+(admin?',added_excerpt,removed_excerpt':'')).order('id',{ascending:false}).limit(100)),
 ]);
 return {monitors,versions,coverage:'Daily checks of seven selected official HTML pages. This is not a comprehensive exchange-disclosure feed; linked PDFs, JavaScript-only content and intra-day edits may be missed. A detected edit requires analyst review.'};
}
export async function eventHistory(id){
 const event=await result(database().from('gi_events').select('*').eq('id',id).maybeSingle());
 if(!event){const e=new Error('Event not found.');e.status=404;throw e;}
 const versions=await result(database().from('gi_event_versions').select('id,captured_at,baseline,facts').eq('event_id',id).order('id',{ascending:false}).limit(100));
 const [assets,review]=await Promise.all([result(database().from('gi_assets').select('id,symbol,company,name,latitude,longitude,location_precision').eq('active',true)),result(database().from('gi_reviews').select('status,assessment,uncertainty,next_check,evidence_url,content_hash,reviewed_at,impact_type,direction,horizon,company_symbols').eq('event_id',id).eq('status','published').maybeSingle())]);
 return {event:{...event,matches:matchAssets(event,assets),review:review?.content_hash===event.content_hash?review:null},versions,coverage:'Newest 100 saved fact revisions. The baseline is the state at archive setup; earlier revisions cannot be reconstructed. Polls with unchanged facts do not create revisions.'};
}
export function buildInbox({preferences,watch,events,monitors,versions,now=Date.now()}){
 if(!preferences.enabled||!preferences.enabled_at||!watch.length)return [];
 const since=Math.max(new Date(preferences.enabled_at).getTime(),now-30*86400000),items=[];
 const recent=time=>Number.isFinite(Date.parse(time))&&Date.parse(time)>=since&&Date.parse(time)<=now;
 for(const e of events){
  const nearby=e.matches?.filter(m=>watch.includes(m.symbol))||[];
  if(preferences.observations&&nearby.length&&recent(e.first_seen_at))items.push({id:`observation:${e.id}`,kind:'Nearby observation',title:e.title,at:e.first_seen_at,detail:'Geographic proximity; business impact is unconfirmed.',href:`/intelligence/events/${encodeURIComponent(e.id)}`});
  if(preferences.assessments&&e.review?.status==='published'&&e.review.content_hash===e.content_hash&&e.review.company_symbols?.some(s=>watch.includes(s))&&recent(e.review.reviewed_at))items.push({id:`assessment:${e.id}:${e.review.reviewed_at}`,kind:'Analyst assessment',title:e.title,at:e.review.reviewed_at,detail:'Current published assessment linked by an analyst to your watched company.',href:`/intelligence/events/${encodeURIComponent(e.id)}`});
 }
 if(preferences.documents)for(const v of versions){const m=monitors.find(x=>x.id===v.monitor_id);if(m&&watch.includes(m.symbol)&&!v.baseline&&recent(v.captured_at))items.push({id:`document:${v.id}`,kind:'Official page changed',title:m.title,at:v.captured_at,detail:'An edit was detected; financial significance has not been established.',href:`/intelligence/companies/${m.symbol}`});}
 return items.sort((a,b)=>Date.parse(b.at)-Date.parse(a.at)).slice(0,100).map(i=>({...i,unread:!preferences.last_read_at||Date.parse(i.at)>Date.parse(preferences.last_read_at)}));
}

export async function archive({page=1,search=''}={}){
 const limit=50,offset=(page-1)*limit;
 let query=database().from('gi_events').select('id,title,provider,category,observed_at,first_seen_at',{count:'exact'}).order('observed_at',{ascending:false}).order('id').range(offset,offset+limit-1);
 if(search)query=query.ilike('title',`%${search.replace(/[\\%_]/g,'')}%`);
 const {data,error,count}=await query;if(error)throw error;
 return {events:data,page,total:count,page_size:limit};
}
