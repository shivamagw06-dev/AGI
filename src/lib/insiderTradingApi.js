import { supabase } from '@/lib/supabaseClient';
import API_ORIGIN from '@/config';
const BASE=API_ORIGIN||'';
async function json(path,options={}){const response=await fetch(BASE+'/api/pe/insider'+path,options);const body=await response.json().catch(()=>({}));if(!response.ok)throw Error(body.error||'Insider Activity API '+response.status);return body}
async function admin(path,options={}){const{data}=await supabase.auth.getSession();return json('/admin'+path,{...options,headers:{'Content-Type':'application/json',Authorization:'Bearer '+(data.session?.access_token||'')}})}
export const insiderActivity=params=>json('/activity?'+new URLSearchParams(Object.entries(params||{}).filter(([,value])=>value)));
export const insiderAdminOverview=()=>admin('/overview');
export const insiderAdminPreview=body=>admin('/imports/preview',{method:'POST',body:JSON.stringify(body)});
export const insiderAdminApprove=body=>admin('/imports/approve',{method:'POST',body:JSON.stringify(body)});
