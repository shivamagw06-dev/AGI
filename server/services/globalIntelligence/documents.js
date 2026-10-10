import {createHash} from 'node:crypto';
import {parse} from 'parse5';
import {database,result} from './store.js';
// Server-owned allowlist. User-submitted evidence URLs are never fetched.
export const DOCUMENTS=[
 {id:'reliance-locations',symbol:'RELIANCE',title:'Reliance manufacturing locations',url:'https://www.ril.com/about/manufacturing-locations'},
 {id:'tata-manufactured-capital',symbol:'TATASTEEL',title:'Tata Steel FY2024–25 manufactured capital',url:'https://www.tatasteel.com/investors/integrated-report-2024-25/manufactured-capital.html'},
 {id:'adani-mundra',symbol:'ADANIPORTS',title:'Adani Ports Mundra profile',url:'https://www.adaniports.com/Ports-and-Terminals/Mundra-Port'},
 {id:'ntpc-coal',symbol:'NTPC',title:'NTPC coal stations',url:'https://ntpc.co.in/power-generation/coal-stations'},
 {id:'ioc-locations',symbol:'IOC',title:'Indian Oil locations',url:'https://www.iocl.com/our-locations'},
 {id:'hindalco-locations',symbol:'HINDALCO',title:'Hindalco plant locations',url:'https://www.hindalco.com/investors/shareholder-centre/listing-details/plant-locations'},
 {id:'jsw-vijayanagar',symbol:'JSWSTEEL',title:'JSW Steel Vijayanagar Works',url:'https://www.jswsteel.in/facility/vijayanagar-works'},
];
const ignored=new Set(['script','style','noscript','nav','header','footer','form','svg','iframe','template']);
const blocks=new Set(['p','div','li','tr','h1','h2','h3','h4','section','article','br']);
function find(node,tag){if(node.tagName===tag)return node;for(const c of node.childNodes||[]){const match=find(c,tag);if(match)return match;}return null;}
export function extractDocument(html){
 const root=parse(html), title=find(root,'title');
 const walk=node=>{if(ignored.has(node.tagName)||node.attrs?.some(a=>(a.name==='hidden')||(a.name==='aria-hidden'&&a.value==='true')))return '';if(node.nodeName==='#text')return node.value;const text=(node.childNodes||[]).map(walk).join(' ');return blocks.has(node.tagName)?`\n${text}\n`:text;};
 if(/access denied|attention required|just a moment|request rejected|security check/i.test(walk(title||{childNodes:[]})))throw new Error('Source returned a blocking page');
 const selected=find(root,'main')||find(root,'article')||find(root,'body');
 const text=walk(selected||root).split('\n').map(x=>x.replace(/\s+/g,' ').trim()).filter(Boolean).join('\n');
 if(text.length<100)throw new Error('Source did not provide sufficient readable HTML');
 if(text.length>150000)throw new Error('Extracted document exceeds size limit');
 return {text,hash:createHash('sha256').update(text).digest('hex')};
}
export function documentDiff(previous,current){
 if(previous==null)return {added:0,removed:0,added_excerpt:'',removed_excerpt:''};
 const before=new Set(previous.split('\n')),after=new Set(current.split('\n'));
 const added=[...after].filter(s=>!before.has(s)),removed=[...before].filter(s=>!after.has(s));
 return {added:added.length,removed:removed.length,added_excerpt:added.join('\n').slice(0,1000),removed_excerpt:removed.join('\n').slice(0,1000)};
}
export async function fetchDocument(url,fetcher=fetch){
 if(!DOCUMENTS.some(d=>d.url===url))throw new Error('Document URL is not allowlisted');
 const response=await fetcher(url,{signal:AbortSignal.timeout(20000),redirect:'error',headers:{Accept:'text/html','User-Agent':'AGI-Research-PageMonitor/1.0 (+https://agarwalglobalinvestments.com/intelligence/sources)'}});
 if(!response.ok)throw new Error(`Source returned HTTP ${response.status}`);
 if(!/text\/html|application\/xhtml\+xml/i.test(response.headers.get('content-type')||''))throw new Error('Source did not return HTML');
 let size=0;const chunks=[];for await(const chunk of response.body){size+=chunk.length;if(size>2_000_000)throw new Error('Source response exceeds size limit');chunks.push(chunk);}
 return extractDocument(Buffer.concat(chunks).toString('utf8'));
}
let running=false;
export async function collectDocuments({force=false}={}){
 if(running)return {skipped:true,reason:'Document collection is running.'};running=true;
 try{
  if(!await result(database().rpc('gi_acquire_document_lease')))return {skipped:true,reason:'Document collection was started within the last ten minutes.'};
  // Metadata only: preserve hashes and prior successful captures across deploys.
  for(const d of DOCUMENTS)await result(database().from('gi_document_monitors').upsert(d,{onConflict:'id',ignoreDuplicates:true}));
  const stored=await result(database().from('gi_document_monitors').select('*'));
  const outcomes=[];
  // Sequential requests avoid bursts against company sites. Only configured pages are eligible.
  for(const d of DOCUMENTS){
   const previous=stored.find(s=>s.id===d.id);
   if(!force&&previous?.last_attempt_at&&Date.now()-new Date(previous.last_attempt_at).getTime()<24*3600000)continue;
   await result(database().from('gi_document_monitors').update({last_attempt_at:new Date().toISOString(),status:'checking'}).eq('id',d.id));
   try{
    const next=await fetchDocument(d.url),diff=documentDiff(previous?.normalized_text,next.text);
    const changed=await result(database().rpc('gi_save_document',{p_id:d.id,p_hash:next.hash,p_text:next.text,p_expected_hash:previous?.content_hash||null,p_added:diff.added,p_removed:diff.removed,p_added_excerpt:diff.added_excerpt,p_removed_excerpt:diff.removed_excerpt}));
    outcomes.push({id:d.id,ok:true,baseline:!previous?.content_hash,changed});
   }catch(e){await result(database().from('gi_document_monitors').update({status:'error',last_error:String(e.message).slice(0,300)}).eq('id',d.id));outcomes.push({id:d.id,ok:false,error:e.message});}
  }
  return {results:outcomes};
 }finally{running=false;}
}
