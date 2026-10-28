import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabaseClient';
import { API_ORIGIN } from '@/config';
const Context=createContext(null);
export async function plusRequest(path,{method='GET',body}={}){
 const {data}=await supabase.auth.getSession();
 const response=await fetch(`${API_ORIGIN||''}/api/plus${path}`,{method,cache:'no-store',headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{}),...(data?.session?.access_token?{Authorization:`Bearer ${data.session.access_token}`}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(20000)});
 const payload=await response.json().catch(()=>({error:'Subscription service unavailable'}));if(!response.ok||payload.error)throw Error(payload.error||'Subscription service unavailable');return payload;
}
export function PlusProvider({children}){
 const {user,authReady,loading:authLoading}=useAuth();const sequence=useRef(0);const [state,setState]=useState({loading:true,error:null,config:null,active:false,isAdmin:false,payments:[],membership:null});
 const refresh=useCallback(async()=>{if(!authReady||authLoading)return;const identity=user?.id||null,request=++sequence.current;
  setState(s=>({...s,loading:true,error:null}));
  try{const payload=await plusRequest(identity?'/status':'/config');const config=identity?payload.config:payload;if(typeof config?.enabled!=='boolean'||typeof config?.checkoutEnabled!=='boolean'||config.amountPaise!==19900||(identity&&(typeof payload.active!=='boolean'||typeof payload.isAdmin!=='boolean')))throw Error('Membership status could not be verified.');if(request===sequence.current)setState(identity?{...payload,subjectId:identity,loading:false,error:null}:{config:payload,subjectId:null,active:false,isAdmin:false,payments:[],membership:null,loading:false,error:null});}
  catch(e){if(request===sequence.current)setState({loading:false,error:e.message,config:null,active:false,isAdmin:false,payments:[],membership:null});}
 },[user?.id,authReady,authLoading]);
 useEffect(()=>{setState({loading:true,error:null,config:null,active:false,isAdmin:false,payments:[],membership:null});refresh();return()=>{sequence.current++;};},[refresh]);
 useEffect(()=>{const onFocus=()=>{if(!document.hidden)refresh();};window.addEventListener('focus',onFocus);const interval=setInterval(onFocus,300000);return()=>{window.removeEventListener('focus',onFocus);clearInterval(interval);};},[refresh]);
 useEffect(()=>{if(!state.active||!state.membership?.expires_at)return;const remaining=Date.parse(state.membership.expires_at)-Date.parse(state.serverTime);const timer=setTimeout(()=>{setState(s=>({...s,active:false}));refresh();},Math.max(0,Math.min(remaining,2147483647)));return()=>clearTimeout(timer);},[state.active,state.membership?.expires_at,state.serverTime,refresh]);
 return <Context.Provider value={{...state,refresh}}>{children}</Context.Provider>;
}
export const usePlus=()=>useContext(Context);
