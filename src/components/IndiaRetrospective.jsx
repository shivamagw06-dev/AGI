import {useEffect,useState} from 'react';
import {API_ORIGIN} from '@/config';
import {supabase} from '@/lib/supabaseClient';
import FactorRetrospective from './FactorRetrospective';
import './FactorSelection.css';
export function useIndiaRetrospective(id,admin=false){
 const [state,setState]=useState({data:null,error:''});
 useEffect(()=>{let active=true;const controller=new AbortController();setState({data:null,error:''});
  const load=async()=>{try{const headers={};if(admin){const {data}=await supabase.auth.getSession();if(data.session)headers.Authorization=`Bearer ${data.session.access_token}`;}
   const r=await fetch(`${API_ORIGIN||''}/api/portfolios/${id?'%ID%/retrospective'.replace('%ID%',encodeURIComponent(id)):'india-retrospectives'}`,{headers,cache:'no-store',signal:controller.signal});
   const data=await r.json();if(!r.ok)throw Error(data.error||'Historical prices unavailable');if(active)setState({data,error:''});
  }catch(e){if(active&&e.name!=='AbortError')setState(s=>({...s,error:e.message}));}};
  load();const timer=setInterval(load,240000);return()=>{active=false;controller.abort();clearInterval(timer);};
 },[id,admin]);return state;
}
export default function IndiaRetrospective({id,admin=false}){
 const {data,error}=useIndiaRetrospective(id,admin);
 return <div className="factor-selection">{error&&<p role="alert" className="pf-warning">September history: {error}</p>}{data?<FactorRetrospective key={id} data={data}/>:<p role="status">Loading historical returns from 15 September…</p>}</div>;
}
