import { FEEDS, normaliseFeed } from './model.js';
import { database, result } from './store.js';
import {collectDocuments} from './documents.js';
let running=false;
export async function fetchJson(url,fetcher=fetch) {
  const response=await fetcher(url,{signal:AbortSignal.timeout(20000),headers:{Accept:'application/json'},redirect:'error'});
  if(!response.ok) throw new Error(`Source returned HTTP ${response.status}`);
  let size=0; const chunks=[];
  for await(const chunk of response.body){size+=chunk.length;if(size>4_000_000)throw new Error('Source response exceeded size limit');chunks.push(chunk);}
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
export async function collectEvents() {
  if(running) return {skipped:true,reason:'A collection is already running.'};
  running=true;
  try {
    const acquired=await result(database().rpc('gi_acquire_collection_lease'));
    if(!acquired)return {skipped:true,reason:'Collection is running or was checked recently.'};
    const outcomes=await Promise.allSettled(FEEDS.map(async feed=>{
      const now=new Date().toISOString();
      await result(database().from('gi_sources').update({last_attempt_at:now,status:'checking'}).eq('id',feed.id));
      try {
        const rows=normaliseFeed(feed.id,await fetchJson(feed.url));
        if(rows.length)await result(database().from('gi_events').upsert(rows.map(r=>({...r,last_seen_at:now})),{onConflict:'id'}));
        await result(database().from('gi_sources').update({last_success_at:now,last_count:rows.length,last_error:null,status:'ok'}).eq('id',feed.id));
        return {source:feed.id,count:rows.length};
      }catch(e){
        await result(database().from('gi_sources').update({last_error:String(e.message).slice(0,300),status:'error'}).eq('id',feed.id));
        throw new Error(`${feed.name}: ${e.message}`);
      }
    }));
    return {results:outcomes.map(r=>r.status==='fulfilled'?{ok:true,...r.value}:{ok:false,error:r.reason.message})};
  } finally {running=false;}
}
export function startGlobalIntelligenceCollector(){
  if(process.env.GLOBAL_INTELLIGENCE_COLLECTOR==='false'||process.env.NODE_ENV==='test')return;
  const run=()=>collectEvents().catch(e=>console.warn('[global-intelligence]',e.message));
  setTimeout(run,60000).unref();
  setInterval(run,30*60*1000).unref();
  const documents=()=>collectDocuments().catch(e=>console.warn('[gi-documents]',e.message));
  setTimeout(documents,90000).unref();
  setInterval(documents,60*60*1000).unref();
}
