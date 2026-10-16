// One process-wide budget for read-only Yahoo requests. Never rotate hosts to evade limits.
export function createYahooRequest({fetcher=(...args)=>fetch(...args),now=Date.now,sleep=ms=>new Promise(r=>setTimeout(r,ms)),spacingMs=500,ttlMs=60000,maxEntries=400,maxQueued=100}={}) {
 const cache=new Map(),pending=new Map();let tail=Promise.resolve(),nextStart=0,cooldownUntil=0,strikes=0;
 const limited=()=>new Response(JSON.stringify({error:'Yahoo cooldown; retry later'}),{status:429,headers:{'Content-Type':'application/json','Retry-After':String(Math.max(1,Math.ceil((cooldownUntil-now())/1000)))}});
 return async function yahooRequest(input,options={}) {
  const url=new URL(input);if(!/^query[12]\.finance\.yahoo\.com$/.test(url.hostname)||url.protocol!=='https:'||(options.method&&options.method!=='GET'))throw Error('Yahoo gateway accepts only Yahoo HTTPS GET requests');
  url.searchParams.sort();const key=url.href;
  const hit=cache.get(key);if(hit&&hit.until>now())return hit.response.clone();
  if(pending.has(key))return (await pending.get(key)).clone();
  if(now()<cooldownUntil)return limited();
  if(pending.size>=maxQueued)return new Response('Yahoo queue full; retry later',{status:503});
  const work=tail.then(async()=>{
   if(now()<cooldownUntil)return limited();
   if(nextStart>now())await sleep(nextStart-now());
   if(now()<cooldownUntil)return limited();
   options.signal?.throwIfAborted();nextStart=now()+spacingMs;
   const headers=new Headers(options.headers);headers.set('Accept','application/json');headers.set('User-Agent','Mozilla/5.0 (compatible; AGI-Market-Data/1.0)');
   const response=await fetcher(url,{...options,headers,signal:options.signal||AbortSignal.timeout(20000)});
   // Buffer before releasing the queue so concurrency includes body transfer.
   const body=await response.arrayBuffer();const saved=new Response(body,{status:response.status,statusText:response.statusText,headers:response.headers});
   if(response.status===429){
    strikes=Math.min(strikes+1,6);const retry=response.headers.get('retry-after');
    const seconds=retry&&/^\d+$/.test(retry)?Number(retry)*1000:Math.max(0,Date.parse(retry||'')-now())||0;
    cooldownUntil=now()+Math.max(seconds,60000*2**(strikes-1));
   } else if(response.ok){strikes=0;cache.set(key,{until:now()+ttlMs,response:saved.clone()});while(cache.size>maxEntries)cache.delete(cache.keys().next().value);}
   return saved;
  });
  pending.set(key,work);tail=work.catch(()=>{});
  try{return (await work).clone();}finally{pending.delete(key);}
 };
}
export const yahooRequest=createYahooRequest();
