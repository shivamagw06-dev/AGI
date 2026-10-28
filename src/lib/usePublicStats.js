import {useEffect,useState} from 'react';
import {API_ORIGIN} from '@/config';
export default function usePublicStats(days=1){
 const [data,setData]=useState(null),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 useEffect(()=>{let active=true;const controller=new AbortController();setData(null);setError('');
 async function load(){try{const r=await fetch(`${API_ORIGIN||''}/api/intelligence/website-analytics/public-summary?days=${days}`,{signal:AbortSignal.any([controller.signal,AbortSignal.timeout(25000)])});const body=await r.json();if(!r.ok||!body.ok)throw Error();if(active){setData(body);setError('');}}catch{if(active&&!controller.signal.aborted)setError('Stats could not refresh. Please try again.');}}
 load();const interval=setInterval(()=>{if(!document.hidden)load();},60000);return()=>{active=false;controller.abort();clearInterval(interval);};
 },[days,retry]);return {data,error,refresh:()=>setRetry(x=>x+1)};
}
